import streamlit as st
import pandas as pd
from database import get_db_cursor
import uuid
from datetime import datetime

class FileProcessor:
    def __init__(self):
        """Initialize the FileProcessor"""
        self.setup_session_state()

    def setup_session_state(self):
        """Initialize session state variables"""
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = []
        if 'processed_data' not in st.session_state:
            st.session_state.processed_data = []
        if 'file_store_mapping' not in st.session_state:
            st.session_state.file_store_mapping = {}

    def get_user_stores(self):
        """Get user's store accounts from database"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT Store_Account_ID, Store_name, Account_name 
                    FROM ecom_store 
                    WHERE username = %s
                    ORDER BY Store_name, Account_name
                """, (st.session_state.username,))
                return cur.fetchall()
        except Exception as e:
            st.error(f"Error fetching stores: {str(e)}")
            return []

    def render_process_page(self):
        """Main render method for file processing page"""
        st.title("E-commerce Income File Processor")
        
        # Get store accounts for dropdown
        stores = self.get_user_stores()
        if not stores:
            st.warning("Please add store accounts first before uploading files.")
            return
        
        # File upload section
        uploaded_files = st.file_uploader(
            "Upload Files (.xlsx)",
            type=['xlsx'],
            accept_multiple_files=True
        )

        if uploaded_files:
            st.header("Added files")
            
            # File processing section
            for file in uploaded_files:
                st.write(f"File: {file.name}")
                
                # Store selection for each file
                selected_store_id = st.selectbox(
                    "Select store account",
                    options=[store['store_account_id'] for store in stores],
                    key=f"store_select_{file.name}"
                )
                
                store_info = next(
                    (store for store in stores if store['store_account_id'] == selected_store_id),
                    None
                )
                
                if store_info:
                    st.session_state.file_store_mapping[file.name] = store_info
                    st.write(f"Selected store: {store_info['store_name']}")
                    st.write(f"Account: {store_info['account_name']}")
                
                st.markdown("---")
            
            # Process button
            if st.button("Process all Files"):
                self.process_files(uploaded_files)
            
            # Show summaries if data is processed
            if st.session_state.processed_data:
                self.show_summaries()

    def process_shopee_file(self, excel_file):
        """Process Shopee excel file"""
        try:
            # Read specific sheet
            df = pd.read_excel(excel_file, sheet_name='Income', header=None)
            
            # Find the header row (contains column names)
            for idx, row in df.iterrows():
                if row.astype(str).str.contains('No. Pesanan').any():
                    header_row = idx
                    break
            
            # Set proper headers and data
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row + 1:].reset_index(drop=True)
            
            # Process date and amount
            df['Tanggal Dana Dilepaskan'] = pd.to_datetime(df['Tanggal Dana Dilepaskan']).dt.date
            df['Total Penghasilan'] = pd.to_numeric(df['Total Penghasilan'], errors='coerce')
            
            # Create summary
            summary = df.groupby('Tanggal Dana Dilepaskan')['Total Penghasilan'].sum().reset_index()
            summary.columns = ['Date', 'Net_income']
            
            return summary
        
        except Exception as e:
            st.error(f"Error processing Shopee file: {str(e)}")
            return pd.DataFrame(columns=['Date', 'Net_income'])

    def process_tokopedia_file(self, excel_file):
        """Process Tokopedia excel file"""
        try:
            # Read Commission Report sheet
            df = pd.read_excel(excel_file, sheet_name='Commission Report')
            
            # Create filtered datasets
            df1 = df[df['Commission Name'] == 'Biaya Layanan Power Merchant']
            df2 = df[df['Commission Name'] == 'Biaya Layanan Bebas Ongkir Power Merchant']
            
            # Convert dates
            df1['Finish Date'] = pd.to_datetime(df1['Finish Date']).dt.date
            df2['Finish Date'] = pd.to_datetime(df2['Finish Date']).dt.date
            
            # Convert numeric values
            df1['Total Product Amount'] = pd.to_numeric(df1['Total Product Amount'], errors='coerce')
            df1['Service Fee Gross'] = pd.to_numeric(df1['Service Fee Gross'], errors='coerce')
            df2['Service Fee Gross'] = pd.to_numeric(df2['Service Fee Gross'], errors='coerce')
            
            # Calculate daily income
            summary_data = []
            dates = sorted(set(df1['Finish Date'].unique()) | set(df2['Finish Date'].unique()))
            
            for date in dates:
                gross = df1[df1['Finish Date'] == date]['Total Product Amount'].sum()
                fee1 = df1[df1['Finish Date'] == date]['Service Fee Gross'].sum()
                fee2 = df2[df2['Finish Date'] == date]['Service Fee Gross'].sum()
                
                net_income = gross - fee1 - fee2
                summary_data.append({
                    'Date': date,
                    'Net_income': net_income
                })
            
            return pd.DataFrame(summary_data)
        
        except Exception as e:
            st.error(f"Error processing Tokopedia file: {str(e)}")
            return pd.DataFrame(columns=['Date', 'Net_income'])

    def process_tiktok_file(self, excel_file):
        """Process TikTok excel file"""
        try:
            # Read Order Details sheet
            df = pd.read_excel(excel_file, sheet_name='Order details')
            
            # Convert date and amount
            df['Order settled time(UTC)'] = pd.to_datetime(df['Order settled time(UTC)']).dt.date
            df['Total settlement amount'] = pd.to_numeric(df['Total settlement amount'], errors='coerce')
            
            # Create summary
            summary = df.groupby('Order settled time(UTC)')['Total settlement amount'].sum().reset_index()
            summary.columns = ['Date', 'Net_income']
            
            return summary
        
        except Exception as e:
            st.error(f"Error processing TikTok file: {str(e)}")
            return pd.DataFrame(columns=['Date', 'Net_income'])

    def process_files(self, files):
        """Process all uploaded files"""
        st.session_state.processed_data = []
        
        for file in files:
            try:
                # Get store info
                store_info = st.session_state.file_store_mapping.get(file.name)
                if not store_info:
                    st.error(f"Please select a store for {file.name}")
                    continue
                
                # Process based on store type
                store_type = store_info['store_name'].lower()
                
                if store_type == 'shopee':
                    summary = self.process_shopee_file(file)
                elif store_type == 'tokopedia':
                    summary = self.process_tokopedia_file(file)
                elif store_type == 'tiktok':
                    summary = self.process_tiktok_file(file)
                else:
                    st.error(f"Unsupported store type: {store_info['store_name']}")
                    continue
                
                if not summary.empty:
                    processed_data = {
                        'filename': file.name,
                        'store_name': store_info['store_name'],
                        'account_name': store_info['account_name'],
                        'store_account_id': store_info['store_account_id'],
                        'data': summary
                    }
                    st.session_state.processed_data.append(processed_data)
                    st.success(f"Successfully processed {file.name}")
                
            except Exception as e:
                st.error(f"Error processing {file.name}: {str(e)}")

    def show_summaries(self):
        """Show summary tables for processed files"""
        st.header("Income Summary")
        
        # Create tabs
        summary_tab, *file_tabs = st.tabs(
            ["Summary"] + [f"File: {pd['filename']}" for pd in st.session_state.processed_data]
        )
        
        # Overall summary
        with summary_tab:
            all_data = []
            for processed in st.session_state.processed_data:
                df = processed['data'].copy()
                df['Store'] = processed['store_name']
                df['Account'] = processed['account_name']
                all_data.append(df)
            
            if all_data:
                combined_df = pd.concat(all_data)
                st.dataframe(combined_df)
                
                # Move save button here
                if st.button("Save to database", type="primary"):
                    self.save_to_database()
        
        # Individual file summaries
        for tab, processed in zip(file_tabs, st.session_state.processed_data):
            with tab:
                st.write(f"Store: {processed['store_name']}")
                st.write(f"Account: {processed['account_name']}")
                st.dataframe(processed['data'])

    def save_to_database(self):
        """Save processed data to database"""
        if not st.session_state.processed_data:
            st.warning("No processed data to save.")
            return
            
        try:
            with get_db_cursor(commit=True) as cur:
                for processed_file in st.session_state.processed_data:
                    for _, row in processed_file['data'].iterrows():
                        # Check for existing data from the same user
                        cur.execute("""
                            SELECT UniqueID 
                            FROM income_data 
                            WHERE Date = %s 
                            AND store_account_id = %s
                            AND username = %s
                        """, (row['Date'], 
                             processed_file['store_account_id'],
                             st.session_state.username))
                        
                        existing_record = cur.fetchone()
                        
                        if existing_record:
                            # Update existing record for this user
                            cur.execute("""
                                UPDATE income_data 
                                SET Net_income = %s 
                                WHERE UniqueID = %s
                            """, (float(row['Net_income']), existing_record['uniqueid']))
                        else:
                            # Insert new record for this user
                            cur.execute("""
                                INSERT INTO income_data 
                                (UniqueID, username, Date, store_account_id, 
                                 store_name, Account_name, Net_income)
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (
                                str(uuid.uuid4()),
                                st.session_state.username,
                                row['Date'],
                                processed_file['store_account_id'],
                                processed_file['store_name'],
                                processed_file['account_name'],
                                float(row['Net_income'])
                            ))
                            
            st.success("Data Saved Successfully!")
            
        except Exception as e:
            st.error(f"Error saving to database: {str(e)}")