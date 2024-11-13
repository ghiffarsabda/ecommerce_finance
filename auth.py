import streamlit as st
from database import get_db_cursor
import bcrypt
import uuid

class AuthSystem:
    def __init__(self):
        # Initialize session states if they don't exist
        if 'logged_in' not in st.session_state:
            st.session_state.logged_in = False
        if 'username' not in st.session_state:
            st.session_state.username = None
            
    def init_login_page(self):
        """Initialize the login page with tabs"""
        st.title("IncomeApp Login")
        tab1, tab2 = st.tabs(["Sign in", "Sign up"])
        
        with tab1:
            self.render_login_tab()
        with tab2:
            self.render_signup_tab()
    
    def render_login_tab(self):
        """Render the login tab"""
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        if st.button("Login", key="login_button"):
            if self.login_user(username, password):
                self.log_login(username)
                st.success("Login successful")
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Incorrect username or password")
    
    def render_signup_tab(self):
        """Render the signup tab"""
        username = st.text_input("Create Username", key="signup_username")
        password = st.text_input("Create Password", type="password", key="signup_password")
        
        if st.button("Create Account", key="create_account"):
            if not username and not password:
                st.error("You are mentally stupid")
            elif not username:
                st.error("Please fill in username")
            elif not password:
                st.error("Please fill in password")
            else:
                if self.create_user(username, password):
                    st.success("Account created, please head to sign in tab.")
                else:
                    st.error("Username already exists")
    
    def login_user(self, username, password):
        """Verify user credentials"""
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    "SELECT password FROM user_data WHERE username = %s",
                    (username,)
                )
                result = cur.fetchone()
                
                if result:
                    stored_password = result['password'].encode('utf-8')
                    return bcrypt.checkpw(password.encode('utf-8'), stored_password)
                return False
        except Exception as e:
            st.error(f"Login error: {str(e)}")
            return False
    
    def create_user(self, username, password):
        """Create a new user account"""
        try:
            with get_db_cursor(commit=True) as cur:
                # Check if username exists
                cur.execute(
                    "SELECT username FROM user_data WHERE username = %s",
                    (username,)
                )
                if cur.fetchone():
                    return False
                
                # Hash password
                salt = bcrypt.gensalt()
                hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
                
                # Create new user
                cur.execute(
                    """
                    INSERT INTO user_data (UniqueID, username, password)
                    VALUES (%s, %s, %s)
                    """,
                    (str(uuid.uuid4()), username, hashed_password.decode('utf-8'))
                )
                return True
        except Exception as e:
            st.error(f"Error creating account: {str(e)}")
            return False
    
    def log_login(self, username):
        """Log the login attempt"""
        try:
            with get_db_cursor(commit=True) as cur:
                cur.execute(
                    """
                    INSERT INTO login_log (UniqueID, username)
                    VALUES (%s, %s)
                    """,
                    (str(uuid.uuid4()), username)
                )
        except Exception as e:
            st.error(f"Error logging login: {str(e)}")
    
    def logout(self):
        """Log out the current user"""
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()
    
    def check_authentication(self):
        """Check if user is authenticated"""
        return st.session_state.logged_in