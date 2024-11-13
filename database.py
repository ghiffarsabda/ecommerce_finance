import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
import streamlit as st

# Database configuration
DB_CONFIG = {
    'host': 'ep-young-sound-a5fmuzwl.us-east-2.aws.neon.tech',
    'database': 'finance_data',
    'user': 'neondb_owner',
    'password': 'uqAcYd9sF3xl',
    'port': 5432,
    'sslmode': 'require'
}

# Create a connection pool
pool = SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    **DB_CONFIG
)

@contextmanager
def get_db_connection():
    """Get a database connection from the pool"""
    conn = None
    try:
        conn = pool.getconn()
        yield conn
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        raise e
    finally:
        if conn is not None:
            pool.putconn(conn)

@contextmanager
def get_db_cursor(commit=False):
    """Get a database cursor with pooled connection"""
    with get_db_connection() as conn:
        cursor = None
        try:
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            yield cursor
            if commit:
                conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if cursor is not None:
                cursor.close()

def test_connection():
    """Test the database connection"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print("Successfully connected to PostgreSQL database!")
                print("Database version:", version)
                return True
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return False

def close_connections():
    """Close all connections in the pool"""
    if pool:
        pool.closeall()
        print("All database connections closed.")

# Clean up connections when the script ends
import atexit
atexit.register(close_connections)

if __name__ == "__main__":
    test_connection()