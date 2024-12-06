import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
import streamlit as st
import time

DB_CONFIG = {
    'host': 'ep-young-sound-a5fmuzwl.us-east-2.aws.neon.tech',
    'database': 'finance_data',
    'user': 'neondb_owner',
    'password': 'uqAcYd9sF3xl',
    'port': 5432,
    'sslmode': 'require',
    'keepalives': 1,
    'keepalives_idle': 30,
    'keepalives_interval': 10,
    'keepalives_count': 5,
    'connect_timeout': 10
}

MAX_RETRIES = 3
RETRY_DELAY = 1

pool = SimpleConnectionPool(
    minconn=5,
    maxconn=20,
    **DB_CONFIG
)

@contextmanager
def get_db_connection():
    conn = None
    for attempt in range(MAX_RETRIES):
        try:
            conn = pool.getconn()
            if not conn.closed:
                yield conn
                return
            pool.putconn(conn)
            conn = None
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            st.error(f"Database connection error: {str(e)}")
            raise e
        finally:
            if conn is not None:
                pool.putconn(conn)

@contextmanager
def get_db_cursor(commit=False):
    with get_db_connection() as conn:
        cursor = None
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            cursor.execute('SET statement_timeout = 30000')
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            if conn and not conn.closed:
                conn.rollback()
            raise e
        finally:
            if cursor is not None and not cursor.closed:
                cursor.close()

def test_connection():
    for attempt in range(MAX_RETRIES):
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT version();")
                    version = cur.fetchone()
                    print("Successfully connected to PostgreSQL database!")
                    print("Database version:", version)
                    return True
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
                continue
            print(f"Error connecting to database: {str(e)}")
            return False

def close_connections():
    if pool:
        pool.closeall()
        print("All database connections closed.")

import atexit
atexit.register(close_connections)

if __name__ == "__main__":
    test_connection()
