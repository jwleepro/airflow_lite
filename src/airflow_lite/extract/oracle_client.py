import logging
import os
import time

import oracledb

from airflow_lite.engine.stage import (
    RETRYABLE_ORACLE_ERRORS,
    NonRetryableOracleError,
    RetryableOracleError,
)

logger = logging.getLogger("airflow_lite.extract.oracle_client")

_thick_mode_initialized = False


class OracleClient:
    """Oracle 11g 연결 관리.

    - 연결 생성 시 RetryableOracleError/NonRetryableOracleError로 래핑
    - oracledb.DatabaseError의 에러 코드를 검사하여 재시도 가능 여부 판별
    - Oracle 11g 연결을 위해 thick mode 자동 초기화
    """

    def __init__(self, config):
        self.config = config
        self._connection = None
        self._ensure_thick_mode()

    def _connection_target(self) -> str:
        host = getattr(self.config, "host", "<unknown>")
        port = getattr(self.config, "port", "<unknown>")
        service_name = getattr(self.config, "service_name", "<unknown>")
        return f"host={host} port={port} service_name={service_name}"

    def _ensure_thick_mode(self):
        """Oracle 11g 연결을 위해 thick mode를 초기화.

        프로세스당 한 번만 실행된다. oracle_home이 설정된 경우 해당 경로의
        Oracle Client 라이브러리를 사용한다.
        """
        global _thick_mode_initialized
        if _thick_mode_initialized:
            return
        oracle_home = getattr(self.config, "oracle_home", None)
        # Oracle Database Home의 경우 oci.dll은 bin/ 서브폴더에 있음
        lib_dir = oracle_home
        if lib_dir and not os.path.isfile(os.path.join(lib_dir, "oci.dll")):
            bin_dir = os.path.join(lib_dir, "bin")
            if os.path.isfile(os.path.join(bin_dir, "oci.dll")):
                lib_dir = bin_dir
        try:
            oracledb.init_oracle_client(lib_dir=lib_dir)
            _thick_mode_initialized = True
            logger.info("oracledb thick mode 초기화 완료 (lib_dir=%s)", lib_dir)
        except Exception as e:
            logger.warning("oracledb thick mode 초기화 실패: %s", e)

    def get_connection(self):
        """Oracle 연결 반환. 연결 끊김 시 재연결 시도."""
        target = self._connection_target()
        if self._connection is None:
            logger.info("Oracle connection not initialized, opening new connection (%s)", target)
            self._connection = self._create_connection()
        elif not self._is_alive():
            logger.warning("Oracle connection health check failed, reconnecting (%s)", target)
            self._connection = self._create_connection()
        else:
            logger.debug("Reusing healthy Oracle connection (%s)", target)
        return self._connection

    def _create_connection(self):
        target = self._connection_target()
        start = time.perf_counter()
        try:
            dsn = oracledb.makedsn(
                self.config.host,
                self.config.port,
                service_name=self.config.service_name,
            )
            logger.info("Opening Oracle connection (%s)", target)
            connection = oracledb.connect(
                user=self.config.user,
                password=self.config.password,
                dsn=dsn,
            )
            elapsed = time.perf_counter() - start
            logger.info("Oracle connection established in %.2fs (%s)", elapsed, target)
            return connection
        except oracledb.DatabaseError as e:
            elapsed = time.perf_counter() - start
            classified = self.classify_error(e)
            error_obj = e.args[0] if e.args else None
            code = getattr(error_obj, "code", None)
            logger.warning(
                "Oracle connection failed after %.2fs (%s, code=%s, retryable=%s): %s",
                elapsed,
                target,
                code,
                isinstance(classified, RetryableOracleError),
                e,
            )
            raise classified from e

    def _is_alive(self) -> bool:
        try:
            self._connection.ping()
            return True
        except Exception as exc:
            logger.warning(
                "Oracle connection ping failed (%s): %s",
                self._connection_target(),
                exc,
            )
            return False

    def classify_error(self, error) -> Exception:
        """Oracle 에러 코드를 검사하여 재시도 가능 여부에 따라 래핑.

        RETRYABLE_ORACLE_ERRORS = {3113, 3114, 12541, 12170, 12571}
        """
        error_obj = error.args[0] if error.args else None
        code = getattr(error_obj, "code", None)
        if code in RETRYABLE_ORACLE_ERRORS:
            return RetryableOracleError(str(error))
        return NonRetryableOracleError(str(error))

    def close(self):
        """연결 종료."""
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            finally:
                self._connection = None
