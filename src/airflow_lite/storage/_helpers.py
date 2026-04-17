"""Cross-cutting storage helpers shared by repositories and migration."""

from __future__ import annotations

from airflow_lite.storage.crypto import DECRYPT_FAILED, Crypto


def decode_password(raw_password: str | None, crypto: Crypto) -> str | None:
    if raw_password is None:
        return None
    decrypted = crypto.decrypt(raw_password)
    if decrypted == DECRYPT_FAILED:
        return raw_password
    return decrypted


def normalize_columns(columns: str | list[str] | None) -> str | None:
    if columns is None:
        return None
    if isinstance(columns, str):
        parts = [p.strip() for p in columns.split(",") if p and p.strip()]
        return ",".join(parts) or None
    if isinstance(columns, list):
        parts = [str(p).strip() for p in columns if str(p).strip()]
        return ",".join(parts) or None
    return None
