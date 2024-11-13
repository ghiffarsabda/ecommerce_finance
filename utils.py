import uuid
import bcrypt
from datetime import datetime

def generate_unique_id():
    """Generate a unique identifier"""
    return str(uuid.uuid4())

def hash_password(password):
    """Hash a password for storing"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

def check_password(password, hashed):
    """Check a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def format_date(date_str):
    """Format date string to mm/dd/yyyy"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return date_obj.strftime('%m/%d/%Y')
    except ValueError:
        try:
            date_obj = datetime.strptime(date_str, '%Y/%m/%d')
            return date_obj.strftime('%m/%d/%Y')
        except ValueError:
            return None