import streamlit as st
from database import get_db_cursor
import uuid
from datetime import datetime
from utils import generate_unique_id 

class StoreManager:
    def __init__(self):
        self.setup_session_state()

    def setup_session_state(self):
        """Initialize session state variables"""
        if 'store_update_message' not in st.session_state:
            st.session_state.store_update_message = None
        if 'selected_store' not in st.session_state:
            st.session_state.selected_store = None

    def render_store_page(self):
        """Main render method for store account manager"""
        st.title("Store Account Manager")
        tab1, tab2, tab3, tab4 = st.tabs([
            "Add New Account", 
            "Update Account Info", 
            "Delete Account",
            "View Accounts"
        ])

        with tab1:
            self.render_add_account_tab()
        with tab2:
            self.render_update_account_tab()
        with tab3:
            self.render_delete_account_tab()
        with tab4:
            self.render_view_accounts_tab()

    def generate_store_account_id(self, store_name, account_name):
        """Generate store account ID from store name and account name"""
        return f"{store_name}_{account_name}"

    def render_add_account_tab(self):
        """Render the add account tab"""
        store_name = st.text_input("Store Name")
        account_name = st.text_input("Account Name")
        store_create_date = st.date_input("Date Created")

        if st.button("Add Account"):
            if not store_name:
                st.error("Store name cannot be blank. (e.g, shopee, tokopedia, toko offline, etc.)")
                return
            if not account_name:
                st.error("Account name cannot be blank. (e.g. Docilworks, bursawindshield, etc.)")
                return
            if not store_create_date:
                st.error("Account creation date cannot be blank")
                return

            store_account_id = self.generate_store_account_id(store_name, account_name)
            
            # Check if store account already exists for this user only
            try:
                with get_db_cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM ecom_store 
                        WHERE LOWER(Store_Account_ID) = LOWER(%s)
                        AND username = %s
                        """, 
                        (store_account_id, st.session_state.username)
                    )
                    if cur.fetchone():
                        st.error("You already have this store and account name combination")
                        return

                # Add new store
                with get_db_cursor(commit=True) as cur:
                    cur.execute(
                        """
                        INSERT INTO ecom_store 
                        (UniqueID, username, Store_name, Account_name, 
                         Store_create_date, Store_Account_ID)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (generate_unique_id(), st.session_state.username, 
                         store_name, account_name, store_create_date, 
                         store_account_id)
                    )
                st.success("New account saved!")
            except Exception as e:
                st.error(f"Error saving account: {str(e)}")

    def render_update_account_tab(self):
        """Render the update account tab"""
        try:
            with get_db_cursor() as cur:
                # Get list of store accounts for current user
                cur.execute(
                    """
                    SELECT Store_Account_ID, Store_name, Account_name 
                    FROM ecom_store 
                    WHERE username = %s
                    """, 
                    (st.session_state.username,)
                )
                stores = cur.fetchall()

            if not stores:
                st.warning("No stores found. Please add a store first.")
                return

            # Create selection dropdown
            store_options = [store['store_account_id'] for store in stores]
            selected_store_id = st.selectbox(
                "Select Store Account", 
                options=store_options,
                key="update_store_select"
            )

            # Get current store info
            current_store = next(
                (store for store in stores 
                 if store['store_account_id'] == selected_store_id),
                None
            )

            if current_store:
                st.text(f"Current store name: {current_store['store_name']}")
                st.text(f"Current account name: {current_store['account_name']}")

                new_store_name = st.text_input(
                    "Changed store name", 
                    value=current_store['store_name']
                )
                new_account_name = st.text_input(
                    "Changed account name", 
                    value=current_store['account_name']
                )

                if st.button("Save Changes"):
                    if (new_store_name == current_store['store_name'] and 
                        new_account_name == current_store['account_name']):
                        st.info("No changes have been made")
                        return

                    try:
                        with get_db_cursor(commit=True) as cur:
                            # First update the income_data table
                            cur.execute(
                                """
                                UPDATE income_data 
                                SET store_name = %s,
                                    account_name = %s,
                                    store_account_id = %s
                                WHERE store_account_id = %s 
                                AND username = %s
                                """,
                                (new_store_name, new_account_name,
                                 self.generate_store_account_id(new_store_name, new_account_name),
                                 selected_store_id, st.session_state.username)
                            )

                            # Then update the ecom_store table
                            cur.execute(
                                """
                                UPDATE ecom_store 
                                SET Store_name = %s, 
                                    Account_name = %s, 
                                    Store_Account_ID = %s
                                WHERE Store_Account_ID = %s 
                                AND username = %s
                                """,
                                (new_store_name, new_account_name,
                                 self.generate_store_account_id(new_store_name, new_account_name),
                                 selected_store_id, st.session_state.username)
                            )

                            # Log the edit
                            cur.execute(
                                """
                                INSERT INTO store_edit_log 
                                (UniqueID, username, prev_store_account_id, 
                                 new_store_account_id)
                                VALUES (%s, %s, %s, %s)
                                """,
                                (generate_unique_id(), st.session_state.username,
                                 selected_store_id, 
                                 self.generate_store_account_id(new_store_name, new_account_name))
                            )

                        st.success("Changes saved!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error updating store: {str(e)}")

        except Exception as e:
            st.error(f"Error: {str(e)}")

    def render_delete_account_tab(self):
        """Render the delete account tab"""
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    SELECT Store_Account_ID, Store_name, Account_name 
                    FROM ecom_store 
                    WHERE username = %s
                    """, 
                    (st.session_state.username,)
                )
                stores = cur.fetchall()

            if not stores:
                st.warning("No stores found.")
                return

            # Create selection dropdown
            store_options = [store['store_account_id'] for store in stores]
            selected_store_id = st.selectbox(
                "Select Store Account", 
                options=store_options,
                key="delete_store_select"
            )

            # Get current store info
            current_store = next(
                (store for store in stores 
                 if store['store_account_id'] == selected_store_id),
                None
            )

            if current_store:
                st.text(f"Store name: {current_store['store_name']}")
                st.text(f"Account name: {current_store['account_name']}")

                if st.button("Delete"):
                    if st.button(f"Are you sure you want to delete {selected_store_id}?"):
                        with get_db_cursor(commit=True) as cur:
                            # Log the deletion
                            cur.execute(
                                """
                                INSERT INTO store_delete_log 
                                (UniqueID, username, deleted_store_account_id)
                                VALUES (%s, %s, %s)
                                """,
                                (str(uuid.uuid4()), st.session_state.username,
                                 selected_store_id)
                            )
                            
                            # Delete the store
                            cur.execute(
                                """
                                DELETE FROM ecom_store 
                                WHERE Store_Account_ID = %s 
                                AND username = %s
                                """,
                                (selected_store_id, st.session_state.username)
                            )

                        st.success("Store deleted successfully!")
                        st.rerun()

        except Exception as e:
            st.error(f"Error: {str(e)}")

    def render_view_accounts_tab(self):
        """Render the view accounts tab"""
        try:
            with get_db_cursor() as cur:
                cur.execute(
                    """
                    SELECT Store_Account_ID, Store_create_date, 
                           Store_name, Account_name 
                    FROM ecom_store 
                    WHERE username = %s
                    ORDER BY Store_create_date
                    """, 
                    (st.session_state.username,)
                )
                stores = cur.fetchall()

            if stores:
                # Convert to list of dicts for better display
                store_list = []
                for store in stores:
                    store_list.append({
                        'Store Account ID': store['store_account_id'],
                        'Create Date': store['store_create_date'],
                        'Store Name': store['store_name'],
                        'Account Name': store['account_name']
                    })
                
                st.table(store_list)
            else:
                st.info("No stores found. Please add a store first.")

        except Exception as e:
            st.error(f"Error: {str(e)}")