"""Append-only audit trail of the AI agent's activity: output/audit_trail.json.

Every agent tool call and every agent run's stop reason is appended as one
record to a JSON array. Guarantees:

- Append only. Existing records are never removed, reordered, or rewritten;
  nothing in the app clears or resets the file.
- Always valid JSON. Each append writes a complete new copy to a temp file and
  atomically swaps it in (os.replace), under a process lock and a file lock,
  so a crash mid-write can't leave a half-written file.
- Never breaks shopping. Any logging failure is caught and logged to the
  server console; the customer's chat carries on.
- No sensitive data. Arguments and results are summarized, not dumped, and
  pass through redact() (emails, API keys/tokens, password fields). Customers
  are recorded only as "guest" or "customer", never by id, name, or email.
- If the file is ever unreadable (e.g. edited by hand), it is NOT overwritten:
  new records go to audit_trail.recovery.jsonl instead.
"""

import contextvars
import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # OS file lock on macOS/Linux; Windows has no fcntl, so the thread lock alone serializes writes.
    import fcntl
except ImportError:  # pragma: no cover - Windows
    fcntl = None

logger = logging.getLogger("campus_customs.audit")

AUDIT_PATH = Path(__file__).resolve().parent.parent / "output" / "audit_trail.json"

_lock = threading.Lock()

# Which agent run (one shopper message) the current tool call belongs to.
current_run: contextvars.ContextVar[dict | None] = contextvars.ContextVar("audit_run", default=None)

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_SECRET = re.compile(r"\b(?:pk|sk|rk|key|tok)[-_][A-Za-z0-9_-]{8,}\b|\b[A-Za-z0-9_-]{32,}\b")
_PASSWORDISH = re.compile(r"(password|passwd|pwd|token|secret|api[_-]?key|authorization)\s*[:=]\s*\S+", re.I)


def redact(text: str, limit: int = 300) -> str:
    """Remove emails, keys/tokens, and password-like values, then shorten."""
    text = _PASSWORDISH.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    text = _EMAIL.sub("[EMAIL]", text)
    text = _SECRET.sub("[REDACTED]", text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def start_run(customer_kind: str, page_path: str | None) -> dict:
    """Begin a new agent run; tool calls made during it share its run_id."""
    run = {"run_id": uuid.uuid4().hex[:12], "customer": customer_kind, "page": page_path, "tool_calls": 0, "cache": {}}
    current_run.set(run)
    return run


def record(event: dict[str, Any]) -> None:
    """Append one record. Never raises."""
    try:
        run = current_run.get()
        entry = {"timestamp": now_iso(), **event}
        if run and "run_id" not in entry:
            entry["run_id"] = run["run_id"]
        _append(entry)
    except Exception:  # Logging must never break the shopping experience.
        logger.exception("Audit trail write failed")


def _append(entry: dict) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = AUDIT_PATH.with_suffix(".lock")
    with _lock, open(lock_path, "a") as lock_file:
        if fcntl:
            fcntl.flock(lock_file, fcntl.LOCK_EX)
        try:
            records: list = []
            if AUDIT_PATH.exists() and AUDIT_PATH.stat().st_size > 0:
                try:
                    records = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
                    if not isinstance(records, list):
                        raise ValueError("audit trail is not a JSON array")
                except ValueError:
                    # Never overwrite an unreadable trail; keep the record elsewhere.
                    with open(AUDIT_PATH.with_suffix(".recovery.jsonl"), "a", encoding="utf-8") as f:
                        f.write(json.dumps(entry) + "\n")
                    logger.error("audit_trail.json is unreadable; wrote record to recovery file instead")
                    return
            records.append(entry)
            tmp = AUDIT_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            os.replace(tmp, AUDIT_PATH)  # atomic: readers see the old file or the new one, never half
        finally:
            if fcntl:
                fcntl.flock(lock_file, fcntl.LOCK_UN)


def read_all() -> list[dict]:
    if not AUDIT_PATH.exists():
        return []
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
