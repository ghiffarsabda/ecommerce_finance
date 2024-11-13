import streamlit as st
from auth import AuthSystem
from store_management import StoreManager
from file_processor import FileProcessor
from reports import ReportGenerator

class IncomeReportApp:
    def __init__(self):
        """Initialize the application components"""
        self.setup_page_config()
        self.auth = AuthSystem()
        self.store_manager = StoreManager()
        self.file_processor = FileProcessor()
        self.report_generator = ReportGenerator()

    def setup_page_config(self):
        """Configure the Streamlit page"""
        st.set_page_config(
            page_title="Income Report Manager",
            page_icon="💰",
            layout="wide",
            initial_sidebar_state="expanded"
        )

    def run(self):
        """Run the main application"""
        try:
            # Check authentication first
            if not self.auth.check_authentication():
                self.auth.init_login_page()
                return

            # If authenticated, show the main application
            self.render_sidebar()
            self.handle_navigation()
            
        except Exception as e:
            st.error(f"Runtime Error: {str(e)}")

    def render_sidebar(self):
        """Render the sidebar navigation"""
        with st.sidebar:
            st.title("Navigation")
            
            # Main navigation
            self.selected_page = st.radio(
                "Select Page",
                options=["Store Accounts", "Process Files", "Reports"]
            )
            
            st.markdown("---")
            
            # User info and logout
            st.write(f"Logged in as: {st.session_state.username}")
            if st.button("Logout", type="primary"):
                self.auth.logout()
                st.rerun()

    def handle_navigation(self):
        """Handle page navigation based on selection"""
        try:
            if self.selected_page == "Store Accounts":
                st.session_state.current_page = "store_accounts"
                self.store_manager.render_store_page()
                
            elif self.selected_page == "Process Files":
                st.session_state.current_page = "process_files"
                self.file_processor.render_process_page()
                
            elif self.selected_page == "Reports":
                st.session_state.current_page = "reports"
                self.report_generator.render_reports_page()
                
        except Exception as e:
            st.error(f"Navigation Error: {str(e)}")
            st.error(str(e))  # Show detailed error message
            
            # Add refresh button
            if st.button("Refresh Page"):
                st.rerun()

def main():
    """Main function to run the application"""
    try:
        app = IncomeReportApp()
        app.run()
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        
        # Show technical details in expander
        with st.expander("Technical Details"):
            st.code(str(e))
            
        # Add application reset button
        if st.button("Reset Application"):
            # Clear session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()