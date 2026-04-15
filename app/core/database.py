"""
SQLite data layer for AI Sales Bot.

Replaces JSON-based storage for proper querying and concurrency.

Tables:
  messages — all processed messages (pending / sent / skipped / escalated)
  leads    — auto-populated from POTENTIAL_BUYER messages
  errors   — system error log from API clients and N8N

Thread safety: SQLite WAL mode + one connection per operation.

Usage:
    from app.core.database import init_db, save_message, get_pending
    init_db()   # call once at startup
"""

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path("data/bot.db")

_DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS messages (
    id          TEXT PRIMARY KEY,
    timestamp   TEXT NOT NULL,
    channel     TEXT NOT NULL DEFAULT 'unknown',
    user_id     TEXT DEFAULT '',
    user_name   TEXT DEFAULT '',
    text        TEXT DEFAULT '',
    intent      TEXT DEFAULT '',
    confidence  REAL DEFAULT 0.0,
    sentiment   TEXT DEFAULT 'neutral',
    key_signals TEXT DEFAULT '[]',
    reply       TEXT DEFAULT '',
    status      TEXT DEFAULT 'pending',
    escalated   INTEGER DEFAULT 0,
    comment_id  TEXT DEFAULT '',
    post_id     TEXT DEFAULT '',
    error       TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS leads (
    id               TEXT PRIMARY KEY,
    message_id       TEXT,
    created_at       TEXT NOT NULL,
    user_name        TEXT DEFAULT '',
    user_id          TEXT DEFAULT '',
    channel          TEXT DEFAULT '',
    product_interest TEXT DEFAULT '',
    contacted        INTEGER DEFAULT 0,
    notes            TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS errors (
    id        TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    type      TEXT DEFAULT '',
    detail    TEXT DEFAULT '',
    source    TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_msg_status    ON messages(status);
CREATE INDEX IF NOT EXISTS idx_msg_channel   ON messages(channel);
CREATE INDEX IF NOT EXISTS idx_msg_intent    ON messages(intent);
CREATE INDEX IF NOT EXISTS idx_msg_ts        ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_leads_channel ON leads(channel);
CREATE INDEX IF NOT EXISTS idx_errors_ts     ON errors(timestamp);
"""


@contextmanager
def _conn():
    """Open a DB connection, commit on success, rollback on error."""
    DB_PATH.parent.mkdir(exist_ok=True)
    con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Create tables and indexes. Safe to call multiple times."""
    with _conn() as con:
        con.executescript(_DDL)


# ---------------------------------------------------------------------------
# Write operations
# ---------------------------------------------------------------------------

def save_message(msg: dict) -> str:
    """
    Insert or replace a message record. Returns the message ID.

    Accepts both the router's internal dict format and the legacy pending
    JSON format (with 'from_name' and 'comment' keys).
    """
    msg_id = msg.get("id") or str(uuid.uuid4())
    with _conn() as con:
        con.execute(
            """
            INSERT OR REPLACE INTO messages
                (id, timestamp, channel, user_id, user_name, text,
                 intent, confidence, sentiment, key_signals,
                 reply, status, escalated, comment_id, post_id, error)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                msg_id,
                msg.get("timestamp", datetime.now().isoformat()),
                msg.get("channel", "unknown"),
                msg.get("user_id", ""),
                msg.get("user_name", "") or msg.get("from_name", ""),
                msg.get("text", "") or msg.get("comment", ""),
                msg.get("intent", ""),
                float(msg.get("confidence", 0.0)),
                msg.get("sentiment", "neutral"),
                json.dumps(msg.get("key_signals", []), ensure_ascii=False),
                msg.get("reply", ""),
                msg.get("status", "pending"),
                1 if msg.get("is_escalated") or msg.get("escalated") else 0,
                msg.get("comment_id", ""),
                msg.get("post_id", ""),
                msg.get("error", ""),
            ),
        )

    # Auto-create lead record for POTENTIAL_BUYER
    if msg.get("intent") == "POTENTIAL_BUYER":
        _ensure_lead(msg_id, msg)

    return msg_id


def _ensure_lead(message_id: str, msg: dict) -> None:
    """Create a lead record if one doesn't exist for this message."""
    with _conn() as con:
        exists = con.execute(
            "SELECT 1 FROM leads WHERE message_id=?", (message_id,)
        ).fetchone()
        if not exists:
            con.execute(
                """
                INSERT INTO leads
                    (id, message_id, created_at, user_name, user_id,
                     channel, product_interest, contacted, notes)
                VALUES (?,?,?,?,?,?,?,0,'')
                """,
                (
                    str(uuid.uuid4()),
                    message_id,
                    msg.get("timestamp", datetime.now().isoformat()),
                    msg.get("user_name", "") or msg.get("from_name", ""),
                    msg.get("user_id", ""),
                    msg.get("channel", ""),
                    msg.get("text", "") or msg.get("comment", ""),
                ),
            )


def update_message_status(
    msg_id: str,
    status: str,
    final_reply: str = "",
    escalated: bool = False,
) -> None:
    """Update message status after an operator action."""
    with _conn() as con:
        if final_reply:
            con.execute(
                "UPDATE messages SET status=?, reply=?, escalated=? WHERE id=?",
                (status, final_reply, 1 if escalated else 0, msg_id),
            )
        else:
            con.execute(
                "UPDATE messages SET status=?, escalated=? WHERE id=?",
                (status, 1 if escalated else 0, msg_id),
            )


def update_lead_contacted(message_id: str, contacted: bool, notes: str = "") -> None:
    """Mark a lead as contacted (or not) and add notes."""
    with _conn() as con:
        con.execute(
            "UPDATE leads SET contacted=?, notes=? WHERE message_id=?",
            (1 if contacted else 0, notes, message_id),
        )


def log_error(error_type: str, detail: str, source: str = "") -> None:
    """Insert an error record into the errors table."""
    with _conn() as con:
        con.execute(
            "INSERT INTO errors (id, timestamp, type, detail, source) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), datetime.now().isoformat(), error_type, detail, source),
        )


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def get_pending(
    channel: Optional[str] = None,
    intent: Optional[str] = None,
) -> list[dict]:
    """Return pending messages, newest first."""
    clauses = ["status='pending'"]
    params: list[Any] = []
    if channel:
        clauses.append("channel=?")
        params.append(channel)
    if intent:
        clauses.append("intent=?")
        params.append(intent)

    where = " AND ".join(clauses)
    with _conn() as con:
        rows = con.execute(
            f"SELECT * FROM messages WHERE {where} ORDER BY timestamp DESC", params
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_history(
    channel: Optional[str] = None,
    intent: Optional[str] = None,
    keyword: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 500,
) -> list[dict]:
    """Return processed messages (sent/skipped/escalated), newest first."""
    clauses = ["status != 'pending'"]
    params: list[Any] = []

    if channel:
        clauses.append("channel=?")
        params.append(channel)
    if intent:
        clauses.append("intent=?")
        params.append(intent)
    if keyword:
        clauses.append("(text LIKE ? OR reply LIKE ? OR user_name LIKE ?)")
        k = f"%{keyword}%"
        params += [k, k, k]
    if date_from:
        clauses.append("timestamp >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("timestamp <= ?")
        params.append(date_to + "T23:59:59")

    where = " AND ".join(clauses)
    with _conn() as con:
        rows = con.execute(
            f"SELECT * FROM messages WHERE {where} ORDER BY timestamp DESC LIMIT ?",
            params + [limit],
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def get_leads(contacted: Optional[bool] = None) -> list[dict]:
    """Return leads joined with their message data, newest first."""
    clauses: list[str] = []
    params: list[Any] = []
    if contacted is not None:
        clauses.append("l.contacted=?")
        params.append(1 if contacted else 0)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    with _conn() as con:
        rows = con.execute(
            f"""
            SELECT l.id as lead_id, l.message_id, l.created_at, l.contacted, l.notes,
                   m.channel, m.user_name, m.user_id, m.text, m.confidence, m.status,
                   m.reply, m.sentiment
            FROM leads l
            LEFT JOIN messages m ON l.message_id = m.id
            {where}
            ORDER BY l.created_at DESC
            """,
            params,
        ).fetchall()
    return [dict(r) for r in rows]


def get_today_stats() -> dict:
    """Return message counts for today."""
    today = date.today().isoformat()
    with _conn() as con:
        total = con.execute(
            "SELECT COUNT(*) FROM messages WHERE timestamp >= ?", (today,)
        ).fetchone()[0]
        replied = con.execute(
            "SELECT COUNT(*) FROM messages WHERE timestamp >= ? AND status='sent'",
            (today,),
        ).fetchone()[0]
        pending = con.execute(
            "SELECT COUNT(*) FROM messages WHERE status='pending'"
        ).fetchone()[0]
    return {"total": total, "replied": replied, "pending": pending}


def get_errors(limit: int = 20) -> list[dict]:
    """Return recent error records, newest first."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM errors ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------

def migrate_from_json(pending_path: Path, history_path: Path) -> int:
    """
    One-time import of existing JSON files into SQLite.
    Safe to call multiple times — INSERT OR REPLACE is idempotent.
    Returns number of records imported.
    """
    count = 0
    for path, default_status in [(pending_path, "pending"), (history_path, "sent")]:
        if not path.exists():
            continue
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in items:
            item.setdefault("status", item.get("action", default_status))
            if item.get("action") == "skipped":
                item["status"] = "skipped"
            save_message(item)
            count += 1
    return count


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    try:
        d["key_signals"] = json.loads(d.get("key_signals", "[]") or "[]")
    except Exception:
        d["key_signals"] = []
    # Backward-compat aliases used in Streamlit templates
    d["from_name"] = d.get("user_name", "")
    d["comment"] = d.get("text", "")
    d["is_escalated"] = bool(d.get("escalated", 0))
    return d
