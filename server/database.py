from contextlib import contextmanager

import pymysql

from server.config import settings


def get_connection():
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=settings.mysql_database,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


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
        conn.close()
