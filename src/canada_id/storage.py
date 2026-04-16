"""SQLite storage for all barcode operations.

Every encode, decode, and validation is logged with timestamps,
field data, images, and AAMVA strings for full audit history.
"""

from __future__ import annotations

import io
import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

DEFAULT_DB_PATH = Path.home() / ".canada-id" / "history.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    op_type TEXT NOT NULL,
    province TEXT,
    fields_json TEXT,
    aamva_string TEXT,
    raw_payload TEXT,
    barcode_image BLOB,
    source_image BLOB,
    errors TEXT,
    created_at REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ops_type ON operations(op_type);
CREATE INDEX IF NOT EXISTS idx_ops_province ON operations(province);
CREATE INDEX IF NOT EXISTS idx_ops_created ON operations(created_at);
"""


@dataclass
class OperationRecord:
    """A single logged operation."""

    id: int
    op_type: str
    province: str | None
    fields: dict | None
    aamva_string: str | None
    raw_payload: str | None
    errors: str | None
    created_at: float

    @property
    def created_at_iso(self) -> str:
        """Human-readable timestamp."""
        return time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(self.created_at),
        )


class HistoryDB:
    """Persistent storage for barcode operations."""

    def __init__(self, db_path: Path | str | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
        )
        self._conn.executescript(_SCHEMA)

    def log_encode(
        self,
        province: str,
        fields: dict,
        aamva_string: str,
        barcode_img: Image.Image | None = None,
    ) -> int:
        """Log an encode operation."""
        img_bytes = _image_to_bytes(barcode_img) if barcode_img else None
        return self._insert(
            op_type="encode",
            province=province,
            fields_json=json.dumps(fields),
            aamva_string=aamva_string,
            barcode_image=img_bytes,
        )

    def log_decode(
        self,
        fields: dict,
        raw_payload: str,
        province: str | None = None,
        source_img: Image.Image | None = None,
    ) -> int:
        """Log a decode operation."""
        img_bytes = _image_to_bytes(source_img) if source_img else None
        return self._insert(
            op_type="decode",
            province=province,
            fields_json=json.dumps(fields),
            raw_payload=raw_payload,
            source_image=img_bytes,
        )

    def log_validate(
        self,
        province: str,
        fields: dict,
        errors: list[str],
    ) -> int:
        """Log a validation operation."""
        return self._insert(
            op_type="validate",
            province=province,
            fields_json=json.dumps(fields),
            errors=json.dumps(errors) if errors else None,
        )

    def get_history(
        self,
        op_type: str | None = None,
        province: str | None = None,
        limit: int = 50,
    ) -> list[OperationRecord]:
        """Retrieve operation history with optional filters."""
        query = (
            "SELECT id, op_type, province, fields_json, aamva_string,"
            " raw_payload, errors, created_at FROM operations WHERE 1=1"
        )
        params: list = []

        if op_type:
            query += " AND op_type = ?"
            params.append(op_type)
        if province:
            query += " AND province = ?"
            params.append(province)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(query, params).fetchall()
        return [
            OperationRecord(
                id=r[0],
                op_type=r[1],
                province=r[2],
                fields=json.loads(r[3]) if r[3] else None,
                aamva_string=r[4],
                raw_payload=r[5],
                errors=r[6],
                created_at=r[7],
            )
            for r in rows
        ]

    def get_barcode_image(self, record_id: int) -> Image.Image | None:
        """Retrieve stored barcode image by record ID."""
        row = self._conn.execute(
            "SELECT barcode_image FROM operations WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row and row[0]:
            return Image.open(io.BytesIO(row[0]))
        return None

    def get_source_image(self, record_id: int) -> Image.Image | None:
        """Retrieve stored source image by record ID."""
        row = self._conn.execute(
            "SELECT source_image FROM operations WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row and row[0]:
            return Image.open(io.BytesIO(row[0]))
        return None

    def get_stats(self) -> dict[str, int]:
        """Get operation counts by type."""
        rows = self._conn.execute(
            "SELECT op_type, COUNT(*) FROM operations GROUP BY op_type",
        ).fetchall()
        return dict(rows)

    def _insert(self, **kwargs) -> int:
        """Insert a row and return its ID."""
        kwargs["created_at"] = time.time()
        cols = ", ".join(kwargs.keys())
        placeholders = ", ".join("?" for _ in kwargs)
        cursor = self._conn.execute(
            f"INSERT INTO operations ({cols}) VALUES ({placeholders})",
            list(kwargs.values()),
        )
        self._conn.commit()
        return cursor.lastrowid

    def close(self):
        """Close the database connection."""
        self._conn.close()


def _image_to_bytes(img: Image.Image) -> bytes:
    """Convert PIL Image to PNG bytes."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
