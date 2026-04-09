import os
from cryptography.fernet import Fernet, InvalidToken

# 환경변수 AIRFLOW_LITE_FERNET_KEY가 없으면 임시 키 생성 (운영 환경에서는 반드시 설정 필요)
_fernet_key = os.environ.get("AIRFLOW_LITE_FERNET_KEY")
if not _fernet_key:
    _fernet_key = Fernet.generate_key().decode("utf-8")

_fernet = Fernet(_fernet_key.encode("utf-8"))


class Crypto:
    """비밀번호 암복호화를 담당하는 헬퍼 클래스 (SOLID - 단일 책임, 의존성 역전 지원)"""
    
    @staticmethod
    def encrypt(text: str | None) -> str | None:
        if text is None:
            return None
        return _fernet.encrypt(text.encode("utf-8")).decode("utf-8")

    @staticmethod
    def decrypt(encrypted_text: str | None) -> str | None:
        if encrypted_text is None:
            return None
        try:
            return _fernet.decrypt(encrypted_text.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            return "---DECRYPTION_FAILED---"
