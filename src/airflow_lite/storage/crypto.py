"""Fernet 기반 비밀번호 암복호화 헬퍼.

Crypto 는 인스턴스화 가능한 값 객체다. 호출 측(Settings, AdminRepository 등)이
Fernet 키를 명시 주입하거나 Crypto.from_env() 로 환경변수에서 로드한다.
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken

_ENV_VAR = "AIRFLOW_LITE_FERNET_KEY"
DECRYPT_FAILED = "---DECRYPTION_FAILED---"


def _missing_key_error() -> RuntimeError:
    return RuntimeError(
        "Fernet 키가 설정되지 않았습니다. pipelines.yaml의 "
        "security.fernet_key 또는 환경변수 "
        f"{_ENV_VAR}을(를) 설정하세요."
    )


class Crypto:
    """비밀번호 암복호화 헬퍼 (SOLID - 단일 책임)."""

    def __init__(self, key: str):
        if not key:
            raise _missing_key_error()
        self._fernet = Fernet(key.encode("utf-8"))

    @classmethod
    def from_env(cls) -> "Crypto":
        return cls(os.environ.get(_ENV_VAR, ""))

    @classmethod
    def from_key_or_env(cls, key: str | None) -> "Crypto":
        return cls(key or os.environ.get(_ENV_VAR, ""))

    def encrypt(self, text: str | None) -> str | None:
        if text is None:
            return None
        return self._fernet.encrypt(text.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted_text: str | None) -> str | None:
        if encrypted_text is None:
            return None
        try:
            return self._fernet.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return DECRYPT_FAILED
