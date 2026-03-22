"""Database connection pool management."""
from contextlib import contextmanager
from typing import Generator, Optional, Any

import mysql.connector
from mysql.connector import errorcode, Error
from mysql.connector.pooling import MySQLConnectionPool


class DatabasePool:
    """Manages MySQL connection pooling."""

    _pool: Optional[MySQLConnectionPool] = None

    @classmethod
    def initialize(
        cls,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
        pool_size: int = 5,
        pool_name: str = 'iam_pool'
    ) -> None:
        """Initialize the connection pool."""
        if cls._pool is not None:
            return

        try:
            cls._pool = MySQLConnectionPool(
                pool_name=pool_name,
                pool_size=pool_size,
                pool_reset_session=True,
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                raise_on_warnings=True
            )
        except Error as err:
            if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
                raise Exception("Database access denied: check username/password")
            elif err.errno == errorcode.ER_BAD_DB_ERROR:
                raise Exception(f"Database '{database}' does not exist")
            raise

    @classmethod
    def close(cls) -> None:
        """Close all connections in the pool."""
        cls._pool = None

    @classmethod
    @contextmanager
    def get_connection(cls) -> Generator[Any, None, None]:
        """Get a connection from the pool (context manager)."""
        if cls._pool is None:
            raise Exception("Database pool not initialized")

        connection = cls._pool.get_connection()
        try:
            yield connection
        finally:
            connection.close()

    @classmethod
    @contextmanager
    def get_cursor(cls, dictionary: bool = False) -> Generator[Any, None, None]:
        """Get a cursor with automatic connection management."""
        with cls.get_connection() as connection:
            cursor = connection.cursor(dictionary=dictionary)
            try:
                yield cursor
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                cursor.close()

    @classmethod
    def execute_query(
        cls,
        query: str,
        params: Optional[tuple] = None,
        dictionary: bool = False
    ) -> list:
        """Execute a query and return results."""
        with cls.get_cursor(dictionary=dictionary) as cursor:
            cursor.execute(query, params or ())
            return cursor.fetchall()

    @classmethod
    def execute_function(
        cls,
        function_name: str,
        params: tuple
    ) -> Any:
        """Execute a MySQL function and return the result."""
        with cls.get_cursor() as cursor:
            placeholders = ', '.join(['%s'] * len(params))
            query = f"SELECT {function_name}({placeholders})"
            cursor.execute(query, params)
            result = cursor.fetchone()
            return result[0] if result else None

    @classmethod
    def call_procedure(
        cls,
        procedure_name: str,
        params: tuple,
        dictionary: bool = False
    ) -> list:
        """Call a stored procedure and return results."""
        with cls.get_connection() as connection:
            cursor = connection.cursor(dictionary=dictionary)
            try:
                cursor.callproc(procedure_name, params)
                results = []
                for result_set in cursor.stored_results():
                    results.extend(result_set.fetchall())
                return results
            finally:
                cursor.close()

    @classmethod
    def call_procedure_with_out(
        cls,
        procedure_name: str,
        params: list
    ) -> list:
        """Call a stored procedure with OUT parameters."""
        with cls.get_connection() as connection:
            cursor = connection.cursor()
            try:
                result = cursor.callproc(procedure_name, params)
                return list(result)
            finally:
                cursor.close()
