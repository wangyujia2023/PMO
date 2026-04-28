from contextlib import contextmanager
from queue import Empty, Full, Queue

import pymysql

from server.config import settings


POOL_SIZE = 5
_pool: Queue = Queue(maxsize=POOL_SIZE)


def _create_connection(database: str | None = settings.mysql_database):
    kwargs = {
        "host": settings.mysql_host,
        "port": settings.mysql_port,
        "user": settings.mysql_user,
        "password": settings.mysql_password,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }
    if database:
        kwargs["database"] = database
    return pymysql.connect(**kwargs)


def get_connection():
    try:
        conn = _pool.get_nowait()
        conn.ping(reconnect=True)
        return conn
    except Empty:
        return _create_connection()
    except Exception:
        return _create_connection()


def release_connection(conn):
    try:
        _pool.put_nowait(conn)
    except Full:
        conn.close()


def get_server_connection():
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


@contextmanager
def get_cursor():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            yield cursor
    finally:
        release_connection(conn)
