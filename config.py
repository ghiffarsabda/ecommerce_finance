import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': 5432,
    'sslmode': 'require'  # Important for Neon.tech
}

# Security configuration
SECRET_KEY = os.getenv('SECRET_KEY', 'docilworks-secret-key-2024')
SALT_ROUNDS = 10

# File upload configuration
ALLOWED_EXTENSIONS = {'xlsx'}
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size