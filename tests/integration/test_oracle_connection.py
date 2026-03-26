"""Oracle 실제 연결 검증 테스트 (OC-01 ~ OC-05).

thick mode 초기화, 연결 생성, ping, 재연결, 에러 분류를 검증한다.
"""
import pytest

from airflow_lite.config.settings import OracleConfig
from airflow_lite.engine.stage import NonRetryableOracleError, RetryableOracleError
from airflow_lite.extract.oracle_client import OracleClient


@pytest.mark.integration
class TestOracleConnection:

    def test_connect_to_oracle(self, oracle_client):
        """OC-01: get_connection()이 유효한 연결을 반환한다."""
        conn = oracle_client.get_connection()
        assert conn is not None

    def test_thick_mode_initialized(self, oracle_client):
        """OC-02: OracleClient 초기화 시 thick mode가 설정된다."""
        from airflow_lite.extract import oracle_client as module
        assert module._thick_mode_initialized is True

    def test_ping_succeeds(self, oracle_client):
        """OC-03: 연결된 상태에서 ping()이 예외 없이 통과한다."""
        conn = oracle_client.get_connection()
        conn.ping()  # 예외 없이 통과해야 함

    def test_reconnect_after_close(self, oracle_client):
        """OC-04: close 후 get_connection() 호출 시 새 연결을 생성한다."""
        conn1 = oracle_client.get_connection()
        assert conn1 is not None
        # 내부 연결 강제 종료 (재연결 트리거)
        oracle_client._connection = None
        conn2 = oracle_client.get_connection()
        assert conn2 is not None

    def test_error_on_invalid_host(self):
        """OC-05: 잘못된 호스트 접속 시 Oracle 에러 타입으로 래핑된다."""
        bad_config = OracleConfig(
            host="127.0.0.1",
            port=9999,
            service_name="INVALID",
            user="nobody",
            password="nobody",
        )
        client = OracleClient(bad_config)
        with pytest.raises((RetryableOracleError, NonRetryableOracleError)):
            client.get_connection()
