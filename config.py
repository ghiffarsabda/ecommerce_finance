import streamlit as st

# Database configuration
DB_CONFIG = {
    'host': st.secrets["postgres"]["host"],
    'database': st.secrets["postgres"]["database"],
    'user': st.secrets["postgres"]["user"],
    'password': st.secrets["postgres"]["password"],
    'port': st.secrets["postgres"]["port"],
    'sslmode': 'require'
}

# Security configuration
SECRET_KEY = st.secrets["SECRET_KEY"]
SALT_ROUNDS = 10

# File upload configuration
ALLOWED_EXTENSIONS = {'xlsx'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
