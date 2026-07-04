"""System logging module - integrated DB logger and structured logging."""
import json
import logging
import logging.handlers
import sys
import traceback
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import get_settings

settings = get_settings()


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogCategory(str, Enum):
    SYSTEM = "system"
    API = "api"
    WEBSOCKET = "websocket"
    LLM = "llm"
    MEMORY = "memory"
    DATABASE = "database"
    SECURITY = "security"


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that writes to SQLite database."""

    def __init__(self):
        super().__init__()
        self._db_ready = False

    def emit(self, record: logging.LogRecord):
        if not settings.LOG_TO_DB:
            return
        try:
            # Deferred import to avoid circular dependency
            from app.db.database import get_sync_db
            log_entry = self._format_record(record)
            db = get_sync_db()
            db.execute(
                """
                INSERT INTO system_logs (level, category, message, details, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    log_entry["level"],
                    log_entry.get("category", "system"),
                    log_entry["message"],
                    log_entry.get("details"),
                    log_entry.get("source", record.name),
                    log_entry.get("created_at", datetime.utcnow().isoformat()),
                ),
            )
            db.commit()
        except Exception:
            # Never raise from logging handler
            pass

    def _format_record(self, record: logging.LogRecord) -> dict:
        details = {}
        if hasattr(record, "category"):
            details["category"] = record.category
        if hasattr(record, "details"):
            extra = record.details
            if isinstance(extra, dict):
                details.update(extra)
            else:
                details["extra"] = str(extra)
        if record.exc_info:
            details["traceback"] = traceback.format_exception(*record.exc_info)

        return {
            "level": record.levelname,
            "message": self.format(record),
            "category": getattr(record, "category", "system"),
            "details": json.dumps(details, ensure_ascii=False, default=str) if details else None,
            "source": f"{record.name}:{record.filename}:{record.lineno}",
            "created_at": datetime.utcnow().isoformat(),
        }


class StructuredLogger:
    """Structured logger that supports both console and database output."""

    def __init__(self, name: str = "app"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, settings.LOG_LEVEL, logging.INFO))

        if not self.logger.handlers:
            # Console handler
            console = logging.StreamHandler(sys.stdout)
            console.setLevel(logging.DEBUG)
            fmt = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
            console.setFormatter(logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S"))
            self.logger.addHandler(console)

            # Database handler
            db_handler = DatabaseLogHandler()
            db_handler.setLevel(logging.DEBUG)
            db_handler.setFormatter(logging.Formatter("%(message)s"))
            self.logger.addHandler(db_handler)

            # File handler — daily rotation, keep 30 days
            if settings.LOG_TO_FILE:
                log_path = Path(settings.LOG_FILE_PATH)
                log_path.parent.mkdir(parents=True, exist_ok=True)
                file_handler = logging.handlers.TimedRotatingFileHandler(
                    str(log_path),
                    when="midnight",
                    interval=1,
                    backupCount=settings.LOG_RETENTION_DAYS,
                    encoding="utf-8",
                )
                file_handler.suffix = "%Y-%m-%d"
                file_handler.setLevel(logging.DEBUG)
                file_handler.setFormatter(
                    logging.Formatter(
                        "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S",
                    )
                )
                self.logger.addHandler(file_handler)

    def _log(self, level: int, category: LogCategory, message: str, details: Optional[Dict] = None):
        extra = {"category": category.value}
        if details:
            extra["details"] = details
        self.logger.log(level, message, extra=extra)

    def debug(self, category: LogCategory, message: str, details: Optional[Dict] = None):
        self._log(logging.DEBUG, category, message, details)

    def info(self, category: LogCategory, message: str, details: Optional[Dict] = None):
        self._log(logging.INFO, category, message, details)

    def warning(self, category: LogCategory, message: str, details: Optional[Dict] = None):
        self._log(logging.WARNING, category, message, details)

    def error(self, category: LogCategory, message: str, details: Optional[Dict] = None):
        self._log(logging.ERROR, category, message, details)

    def critical(self, category: LogCategory, message: str, details: Optional[Dict] = None):
        self._log(logging.CRITICAL, category, message, details)

    def api_request(self, method: str, path: str, status_code: int, duration_ms: float, client_ip: str = "", error: Optional[str] = None):
        """Log API request details."""
        details = {
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
        }
        if error:
            details["error"] = error
            self.error(LogCategory.API, f"API {method} {path} -> {status_code}", details)
        else:
            self.info(LogCategory.API, f"API {method} {path} -> {status_code}", details)

    def websocket_event(self, event_type: str, session_id: Optional[int] = None, details: Optional[Dict] = None):
        """Log WebSocket events."""
        d = {"event_type": event_type}
        if session_id is not None:
            d["session_id"] = session_id
        if details:
            d.update(details)
        self.info(LogCategory.WEBSOCKET, f"WS {event_type}", d)

    def llm_call(self, model: str, prompt_tokens: int, completion_tokens: int, duration_ms: float, success: bool = True, error: Optional[str] = None):
        """Log LLM API calls."""
        details = {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "duration_ms": round(duration_ms, 2),
            "success": success,
        }
        if error:
            details["error"] = error
        self.info(LogCategory.LLM, f"LLM call {model} {'success' if success else 'failed'}", details)

    def db_operation(self, operation: str, table: str, rows_affected: int = 0, duration_ms: float = 0, error: Optional[str] = None):
        """Log database operations."""
        details = {
            "operation": operation,
            "table": table,
            "rows_affected": rows_affected,
            "duration_ms": round(duration_ms, 2),
        }
        if error:
            details["error"] = error
            self.error(LogCategory.DATABASE, f"DB {operation} on {table} failed", details)
        else:
            self.debug(LogCategory.DATABASE, f"DB {operation} on {table}", details)

    def memory_operation(self, operation: str, character_id: int, count: int = 0, error: Optional[str] = None):
        """Log memory engine operations."""
        details = {"operation": operation, "character_id": character_id, "count": count}
        if error:
            details["error"] = error
            self.error(LogCategory.MEMORY, f"Memory {operation} failed", details)
        else:
            self.debug(LogCategory.MEMORY, f"Memory {operation}", details)

    def security_event(self, event_type: str, source_ip: str = "", details: Optional[Dict] = None):
        """Log security events."""
        d = {"event_type": event_type, "source_ip": source_ip}
        if details:
            d.update(details)
        self.warning(LogCategory.SECURITY, f"Security event: {event_type}", d)


# Global logger instance
logger = StructuredLogger()
