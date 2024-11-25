import streamlit as st
import pandas as pd
from database import get_db_cursor
from datetime import datetime, timedelta
import plotly.express as px
from io import BytesIO
import xlsxwriter
import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import tempfile
import calendar
from datetime import datetime, timedelta
import plotly.io as pio
from functools import lru_cache
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
import plotly.io as pio

class ReportGenerator:
    def __init__(self):
        self.setup_session_state()

    def setup_session_state(self):
        if 'report_start_date' not in st.session_state:
            st.session_state.report_start_date = None
        if 'report_end_date' not in st.session_state:
            st.session_state.report_end_date = None

    @st.cache_data(ttl=3600)  # Cache for 1 hour
    def get_available_date_range(_self):
        """Get the available date range from income_data"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT MIN(date) as min_date, MAX(date) as max_date 
                    FROM income_data 
                    WHERE username = %s
                """, (st.session_state.username,))
                result = cur.fetchone()
                return result['min_date'], result['max_date']
        except Exception as e:
            st.error(f"Error getting date range: {str(e)}")
            return None, None

    @st.cache_data(ttl=3600)
    def get_unique_stores(_self):
        """Get unique store account IDs"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT store_account_id 
                    FROM income_data 
                    WHERE username = %s
                    ORDER BY store_account_id
                """, (st.session_state.username,))
                return [row['store_account_id'] for row in cur.fetchall()]
        except Exception as e:
            st.error(f"Error getting stores: {str(e)}")
            return []

    def render_reports_page(self):
        """Main render method with performance optimization"""
        # Initialize session state if needed
        if 'current_tab' not in st.session_state:
            st.session_state.current_tab = "Overview"
        
        # Use radio buttons instead of tabs for better performance
        st.session_state.current_tab = st.sidebar.radio(
            "Select Report Section",
            ["Report Overview", "Create Report", "Income Data"]
        )
        
        # Render selected section
        if st.session_state.current_tab == "Report Overview":
            self.render_overview_section()
        elif st.session_state.current_tab == "Create Report":
            self.render_create_report()
        else:
            self.render_income_data_section()  # Renamed from render_details_section
            
    def render_overview_section(self):
        """Render the overview section"""
        # Get available date range
        min_date, max_date = self.get_available_date_range()
        if not min_date or not max_date:
            st.warning("No data available for reports.")
            return

        # Report Overview Section
        st.header("Report Overview")
        
        # Date range selection
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", 
                                     min_value=min_date,
                                     max_value=max_date,
                                     value=min_date)
        with col2:
            end_date = st.date_input("End Date",
                                   min_value=min_date,
                                   max_value=max_date,
                                   value=max_date)

        # Store selection
        available_stores = self.get_unique_stores()
        selected_stores = st.multiselect(
            "Choose Store Account(s)", 
            available_stores,
            placeholder="Choose Store Account(s)"
        )

        # Total income chart
        total_income_df = self.get_total_income_data(start_date, end_date)
        if not total_income_df.empty:
            fig1 = px.line(total_income_df, 
                          x='date', 
                          y='net_income',
                          title='Total Income Across All Stores')
            fig1.update_layout(
                yaxis_title="Income (Rp)",
                xaxis_title="Date"
            )
            st.plotly_chart(fig1, use_container_width=True)

        # Store income comparison chart
        store_income_df = self.get_store_income_data(start_date, end_date, selected_stores)
        if not store_income_df.empty:
            fig2 = px.line(store_income_df, 
                          x='date', 
                          y='net_income',
                          color='store_account_id',
                          title='Income by Store Account')
            fig2.update_layout(
                yaxis_title="Income (Rp)",
                xaxis_title="Date"
            )
            st.plotly_chart(fig2, use_container_width=True)

        # New admin input charts
        # Visitors chart
        visitors_df = self.get_admin_data_by_type("Pengunjung", start_date, end_date, selected_stores)
        if not visitors_df.empty:
            fig3 = px.line(visitors_df,
                          x='date',
                          y='value',
                          color='store_account_id',
                          title='Visitors by Store Account')
            fig3.update_layout(
                yaxis_title="Visitors",
                xaxis_title="Date"
            )
            st.plotly_chart(fig3, use_container_width=True)

        # Sales chart
        sales_df = self.get_admin_data_by_type("Penjualan", start_date, end_date, selected_stores)
        if not sales_df.empty:
            fig4 = px.line(sales_df,
                          x='date',
                          y='value',
                          color='store_account_id',
                          title='Sales by Store Account')
            fig4.update_layout(
                yaxis_title="Sales",
                xaxis_title="Date"
            )
            st.plotly_chart(fig4, use_container_width=True)

        # Orders chart
        orders_df = self.get_admin_data_by_type("Pesanan", start_date, end_date, selected_stores)
        if not orders_df.empty:
            fig5 = px.line(orders_df,
                          x='date',
                          y='value',
                          color='store_account_id',
                          title='Orders by Store Account')
            fig5.update_layout(
                yaxis_title="Orders",
                xaxis_title="Date"
            )
            st.plotly_chart(fig5, use_container_width=True)
    
    

    def get_total_income_data(self, start_date, end_date):
        """Get total income data across all stores"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT 
                        date,
                        SUM(net_income) as net_income
                    FROM income_data
                    WHERE username = %s
                    AND date BETWEEN %s AND %s
                    GROUP BY date
                    ORDER BY date
                """, (st.session_state.username, start_date, end_date))
                return pd.DataFrame(cur.fetchall())
        except Exception as e:
            st.error(f"Error getting total income: {str(e)}")
            return pd.DataFrame()

    def get_store_income_data(self, start_date, end_date, selected_store_ids=None):
        """Get income data by store account ID"""
        try:
            with get_db_cursor() as cur:
                if selected_store_ids:
                    cur.execute("""
                        SELECT 
                            date,
                            store_account_id,
                            SUM(net_income) as net_income
                        FROM income_data
                        WHERE username = %s
                        AND date BETWEEN %s AND %s
                        AND store_account_id = ANY(%s)
                        GROUP BY date, store_account_id
                        ORDER BY date, store_account_id
                    """, (st.session_state.username, start_date, end_date, selected_store_ids))
                else:
                    cur.execute("""
                        SELECT 
                            date,
                            store_account_id,
                            SUM(net_income) as net_income
                        FROM income_data
                        WHERE username = %s
                        AND date BETWEEN %s AND %s
                        GROUP BY date, store_account_id
                        ORDER BY date, store_account_id
                    """, (st.session_state.username, start_date, end_date))
                return pd.DataFrame(cur.fetchall())
        except Exception as e:
            st.error(f"Error getting store income: {str(e)}")
            return pd.DataFrame()
    
    def get_admin_monthly_comparison_data(self, data_type, main_month, comp_month):
        """Get monthly comparison data for admin input"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    WITH main_month_data AS (
                        SELECT 
                            store_account_id,
                            SUM(value) as current_mo
                        FROM imp_gs_admininput
                        WHERE username = %s
                        AND type = %s
                        AND date >= %s 
                        AND date < (%s + INTERVAL '1 month')
                        GROUP BY store_account_id
                    ),
                    comp_month_data AS (
                        SELECT 
                            store_account_id,
                            SUM(value) as previous_mo
                        FROM imp_gs_admininput
                        WHERE username = %s
                        AND type = %s
                        AND date >= %s 
                        AND date < (%s + INTERVAL '1 month')
                        GROUP BY store_account_id
                    )
                    SELECT 
                        COALESCE(m.store_account_id, c.store_account_id) as "Accounts",
                        COALESCE(m.current_mo, 0) as current_mo,
                        COALESCE(c.previous_mo, 0) as previous_mo
                    FROM main_month_data m
                    FULL OUTER JOIN comp_month_data c 
                        ON m.store_account_id = c.store_account_id
                    WHERE COALESCE(m.current_mo, 0) != 0 
                       OR COALESCE(c.previous_mo, 0) != 0
                    ORDER BY "Accounts"
                """, (st.session_state.username, data_type, main_month, main_month, 
                     st.session_state.username, data_type, comp_month, comp_month))
                
                result = cur.fetchall()
                if not result:
                    return pd.DataFrame()
                    
                df = pd.DataFrame(result)
                
                # Calculate differences
                df['Diff_num'] = df['current_mo'] - df['previous_mo']
                
                # Calculate percentage difference
                df['Difference %'] = df.apply(
                    lambda row: 0 if row['previous_mo'] == 0 
                    else ((row['current_mo'] - row['previous_mo']) / row['previous_mo'] * 100), 
                    axis=1
                )
                
                # Format number columns if not sales
                if data_type != 'Penjualan':
                    for col in ['current_mo', 'previous_mo', 'Diff_num']:
                        df[col] = df[col].apply(lambda x: f"{int(x):,}")
                else:
                    # Format currency for sales
                    for col in ['current_mo', 'previous_mo', 'Diff_num']:
                        df[col] = df[col].apply(lambda x: f"Rp{int(x):,}")
                
                df['Difference %'] = df['Difference %'].apply(lambda x: f"{x:.2f}%")
                
                return df
                
        except Exception as e:
            st.error(f"Error in {data_type} monthly comparison: {str(e)}")
            return pd.DataFrame()
        
    def get_admin_data_by_type(self, data_type, start_date, end_date, selected_stores=None):
        """Get admin input data filtered by type and date range"""
        try:
            with get_db_cursor() as cur:
                if selected_stores:
                    cur.execute("""
                        SELECT 
                            date,
                            store_account_id,
                            value
                        FROM imp_gs_admininput
                        WHERE username = %s
                        AND type = %s
                        AND date BETWEEN %s AND %s
                        AND store_account_id = ANY(%s)
                        GROUP BY date, store_account_id, value
                        ORDER BY date, store_account_id
                    """, (st.session_state.username, data_type, start_date, end_date, selected_stores))
                else:
                    cur.execute("""
                        SELECT 
                            date,
                            store_account_id,
                            value
                        FROM imp_gs_admininput
                        WHERE username = %s
                        AND type = %s
                        AND date BETWEEN %s AND %s
                        GROUP BY date, store_account_id, value
                        ORDER BY date, store_account_id
                    """, (st.session_state.username, data_type, start_date, end_date))
                return pd.DataFrame(cur.fetchall())
        except Exception as e:
            st.error(f"Error getting {data_type} data: {str(e)}")
            return pd.DataFrame()

    def get_total_admin_data_by_type(self, data_type, start_date, end_date):
        """Get total admin input data for a specific type"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT 
                        date,
                        SUM(value) as total_value
                    FROM imp_gs_admininput
                    WHERE username = %s
                    AND type = %s
                    AND date BETWEEN %s AND %s
                    GROUP BY date
                    ORDER BY date
                """, (st.session_state.username, data_type, start_date, end_date))
                return pd.DataFrame(cur.fetchall())
        except Exception as e:
            st.error(f"Error getting total {data_type} data: {str(e)}")
            return pd.DataFrame()

    def render_as_per_today_tab(self):
        """Render As Per Today tab content"""
        try:
            # Month selection
            col1, col2 = st.columns(2)
            with col1:
                main_month = st.date_input(
                    "Choose main month", 
                    value=datetime.now().date().replace(day=1),
                    key="main_month"
                )
            with col2:
                comp_month = st.date_input(
                    "Choose comparison month",
                    value=(datetime.now().date() - timedelta(days=30)).replace(day=1),
                    key="comp_month"
                )

            # Get comparison data
            comparison_data = self.get_monthly_comparison_data(main_month, comp_month)
            
            if comparison_data.empty:
                st.info("No data for current month")
                return
                
            st.subheader("Monthly Comparison")
            st.dataframe(comparison_data, hide_index=True, use_container_width=True)
            
        except Exception as e:
            st.info("No data for current month")

    def get_monthly_comparison_data(self, main_month, comp_month):
        """Get monthly comparison data"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    WITH main_month_data AS (
                        SELECT 
                            store_account_id,
                            store_name,
                            account_name,
                            SUM(net_income) as current_mo
                        FROM income_data
                        WHERE username = %s
                        AND date >= %s 
                        AND date < (%s + INTERVAL '1 month')
                        GROUP BY store_account_id, store_name, account_name
                    ),
                    comp_month_data AS (
                        SELECT 
                            store_account_id,
                            store_name,
                            account_name,
                            SUM(net_income) as previous_mo
                        FROM income_data
                        WHERE username = %s
                        AND date >= %s 
                        AND date < (%s + INTERVAL '1 month')
                        GROUP BY store_account_id, store_name, account_name
                    )
                    SELECT 
                        COALESCE(m.store_account_id, c.store_account_id) as "Accounts",
                        COALESCE(m.current_mo, 0) as current_mo,
                        COALESCE(c.previous_mo, 0) as previous_mo
                    FROM main_month_data m
                    FULL OUTER JOIN comp_month_data c 
                        ON m.store_account_id = c.store_account_id
                    WHERE COALESCE(m.current_mo, 0) != 0 
                       OR COALESCE(c.previous_mo, 0) != 0
                    ORDER BY "Accounts"
                """, (st.session_state.username, main_month, main_month, 
                     st.session_state.username, comp_month, comp_month))
                
                result = cur.fetchall()
                if not result:
                    return pd.DataFrame()
                    
                df = pd.DataFrame(result)
                
                # Calculate differences
                df['Difference Rp'] = df['current_mo'] - df['previous_mo']
                df['Difference %'] = df.apply(lambda row: 
                    0 if row['previous_mo'] == 0
                    else (row['Difference Rp'] / row['previous_mo'] * 100)
                    if row['previous_mo'] != 0 else 0, axis=1)
                
                # Format currency columns
                currency_cols = ['current_mo', 'previous_mo', 'Difference Rp']
                for col in currency_cols:
                    df[col] = df[col].apply(lambda x: f"Rp{x:,.0f}")
                df['Difference %'] = df['Difference %'].apply(lambda x: f"{x:,.2f}%")
                
                return df
                
        except Exception as e:
            st.error(f"Error in monthly comparison: {str(e)}")
            return pd.DataFrame()
        
    def get_daily_comparison_data(self):
        """Get today vs yesterday comparison data"""
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)

            with get_db_cursor() as cur:
                cur.execute("""
                    WITH today_data AS (
                        SELECT 
                            store_account_id,
                            SUM(net_income) as today_income
                        FROM income_data
                        WHERE username = %s
                        AND date = %s
                        GROUP BY store_account_id
                    ),
                    yesterday_data AS (
                        SELECT 
                            store_account_id,
                            SUM(net_income) as yesterday_income
                        FROM income_data
                        WHERE username = %s
                        AND date = %s
                        GROUP BY store_account_id
                    )
                    SELECT 
                        COALESCE(t.store_account_id, y.store_account_id) as "Accounts",
                        COALESCE(t.today_income, 0) as today_income,
                        COALESCE(y.yesterday_income, 0) as yesterday_income
                    FROM today_data t
                    FULL OUTER JOIN yesterday_data y ON t.store_account_id = y.store_account_id
                    WHERE COALESCE(t.today_income, 0) != 0 
                       OR COALESCE(y.yesterday_income, 0) != 0
                    ORDER BY "Accounts"
                """, (st.session_state.username, today, 
                     st.session_state.username, yesterday))
                
                result = cur.fetchall()
                if not result:
                    return pd.DataFrame()
                    
                df = pd.DataFrame(result)
                
                # Calculate differences
                df['Difference Rp'] = df['today_income'] - df['yesterday_income']
                df['Difference %'] = df.apply(lambda row: 
                    0 if row['yesterday_income'] == 0
                    else (row['Difference Rp'] / row['yesterday_income'] * 100)
                    if row['yesterday_income'] != 0 else 0, axis=1)
                
                # Format currency columns
                for col in ['today_income', 'yesterday_income', 'Difference Rp']:
                    df[col] = df[col].apply(lambda x: f"Rp{x:,.0f}")
                df['Difference %'] = df['Difference %'].apply(lambda x: f"{x:,.2f}%")
                
                return df
                
        except Exception as e:
            st.error(f"Error getting daily comparison: {str(e)}")
            return pd.DataFrame()
        
    def get_daily_admin_comparison_data(self, data_type):
        """Get today vs yesterday comparison data for admin input"""
        try:
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)

            with get_db_cursor() as cur:
                cur.execute("""
                    WITH today_data AS (
                        SELECT 
                            store_account_id,
                            SUM(value) as today
                        FROM imp_gs_admininput
                        WHERE username = %s
                        AND type = %s
                        AND date = %s
                        GROUP BY store_account_id
                    ),
                    yesterday_data AS (
                        SELECT 
                            store_account_id,
                            SUM(value) as yesterday
                        FROM imp_gs_admininput
                        WHERE username = %s
                        AND type = %s
                        AND date = %s
                        GROUP BY store_account_id
                    )
                    SELECT 
                        COALESCE(t.store_account_id, y.store_account_id) as "Accounts",
                        COALESCE(t.today, 0) as today,
                        COALESCE(y.yesterday, 0) as yesterday
                    FROM today_data t
                    FULL OUTER JOIN yesterday_data y ON t.store_account_id = y.store_account_id
                    WHERE COALESCE(t.today, 0) != 0 
                       OR COALESCE(y.yesterday, 0) != 0
                    ORDER BY "Accounts"
                """, (st.session_state.username, data_type, today, 
                     st.session_state.username, data_type, yesterday))
                
                result = cur.fetchall()
                if not result:
                    return pd.DataFrame()
                    
                df = pd.DataFrame(result)
                
                # Calculate differences
                df['Diff_num'] = df['today'] - df['yesterday']
                
                # Calculate percentage difference
                df['Diff_%'] = df.apply(
                    lambda row: 0 if row['yesterday'] == 0 
                    else ((row['today'] - row['yesterday']) / row['yesterday'] * 100), 
                    axis=1
                )
                
                # Format columns based on type
                if data_type != 'Penjualan':
                    for col in ['today', 'yesterday', 'Diff_num']:
                        df[col] = df[col].apply(lambda x: f"{int(x):,}")
                else:
                    # Format currency for sales
                    for col in ['today', 'yesterday', 'Diff_num']:
                        df[col] = df[col].apply(lambda x: f"Rp{int(x):,}")
                
                df['Diff_%'] = df['Diff_%'].apply(lambda x: f"{x:.2f}%")
                
                return df
                
        except Exception as e:
            st.error(f"Error in {data_type} daily comparison: {str(e)}")
            return pd.DataFrame()

    def render_todays_income_tab(self):
        """Render Today's Income tab content"""
        st.subheader("Today's Income")
        
        today_data = self.get_today_income_data()
        if not today_data.empty:
            st.dataframe(
                today_data,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No data available for today")

    def get_today_income_data(self):
        """Get today's income comparison data"""
        try:
            today = datetime.now().date()
            last_month = today - timedelta(days=30)
            
            with get_db_cursor() as cur:
                cur.execute("""
                    WITH today_data AS (
                        SELECT 
                            store_account_id,
                            store_name,
                            account_name,
                            SUM(net_income) as today_income
                        FROM income_data
                        WHERE username = %s
                        AND date = %s
                        GROUP BY store_account_id, store_name, account_name
                    ),
                    last_month_data AS (
                        SELECT 
                            store_account_id,
                            store_name,
                            account_name,
                            SUM(net_income) as last_month_income
                        FROM income_data
                        WHERE username = %s
                        AND date = %s
                        GROUP BY store_account_id, store_name, account_name
                    )
                    SELECT 
                        COALESCE(t.store_account_id, l.store_account_id) as "Store ID",
                        COALESCE(t.store_name, l.store_name) as "Store",
                        COALESCE(t.account_name, l.account_name) as "Account",
                        COALESCE(t.today_income, 0) as today_income,
                        COALESCE(l.last_month_income, 0) as last_month_income,
                        COALESCE(t.today_income, 0) - COALESCE(l.last_month_income, 0) as "Diff_IDR",
                        CASE 
                            WHEN COALESCE(l.last_month_income, 0) = 0 THEN 0
                            ELSE ROUND(((COALESCE(t.today_income, 0) - COALESCE(l.last_month_income, 0)) * 100.0 / 
                                  NULLIF(COALESCE(l.last_month_income, 0), 0))::numeric, 2)
                        END as "Diff_%"
                    FROM today_data t
                    FULL OUTER JOIN last_month_data l 
                        ON t.store_account_id = l.store_account_id
                    ORDER BY "Store", "Account"
                """, (st.session_state.username, today, st.session_state.username, last_month))
                
                result = cur.fetchall()
                if result:
                    df = pd.DataFrame(result)
                    # Format currency columns
                    currency_cols = ['today_income', 'last_month_income', 'Diff_IDR']
                    for col in currency_cols:
                        df[col] = df[col].apply(lambda x: f"Rp{x:,.0f}")
                    df['Diff_%'] = df['Diff_%'].apply(lambda x: f"{x:,.2f}%")
                    return df
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error in today's income: {str(e)}")
            return pd.DataFrame()

    def render_income_data_tab(self):
        """Render Income Data tab content"""
        # Store filter
        stores = self.get_unique_stores()
        selected_store = st.selectbox(
            "Filter by Store Account", 
            ["All"] + stores
        )
        
        # Sort direction
        sort_direction = st.radio(
            "Sort by date", 
            ["Ascending", "Descending"],
            horizontal=True
        )
        
        # Get and display filtered data
        filtered_data = self.get_filtered_income_data(
            selected_store,
            sort_direction.lower()
        )
        
        if not filtered_data.empty:
            st.dataframe(
                filtered_data,
                hide_index=True,
                use_container_width=True
            )
        else:
            st.info("No data available")

    def get_filtered_income_data(self, store_account_id_filter, sort_direction):
        """Get filtered income data"""
        try:
            with get_db_cursor() as cur:
                if store_account_id_filter == "All":
                    cur.execute("""
                        SELECT 
                            date::date as "Date",
                            store_account_id as "Store Account ID",
                            store_name as "Store",
                            account_name as "Account",
                            net_income as "Net Income"
                        FROM income_data
                        WHERE username = %s
                        ORDER BY date {}
                    """.format('ASC' if sort_direction == 'ascending' else 'DESC'),
                        (st.session_state.username,))
                else:
                    cur.execute("""
                        SELECT 
                            date::date as "Date",
                            store_account_id as "Store Account ID",
                            store_name as "Store",
                            account_name as "Account",
                            net_income as "Net Income"
                        FROM income_data
                        WHERE username = %s
                        AND store_account_id = %s
                        ORDER BY date {}
                    """.format('ASC' if sort_direction == 'ascending' else 'DESC'),
                        (st.session_state.username, store_account_id_filter))
                
                result = cur.fetchall()
                if result:
                    df = pd.DataFrame(result)
                    # Format currency columns
                    df["Net Income"] = df["Net Income"].apply(lambda x: f"Rp{x:,.0f}")
                    return df
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error in filtered data: {str(e)}")
            return pd.DataFrame()

    def generate_excel_report(self, total_income_df, store_income_df, start_date, end_date):
        """Generate Excel report with multiple sheets"""
        output = BytesIO()
        
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # Write overview data
            if not total_income_df.empty:
                total_income_df.to_excel(
                    writer, 
                    sheet_name='Total Income',
                    index=False
                )
            
            # Write store income data
            if not store_income_df.empty:
                store_income_df.to_excel(
                    writer, 
                    sheet_name='Store Income',
                    index=False
                )
            
            # Write monthly comparison
            monthly_data = self.get_monthly_comparison_data(
                datetime.now().date().replace(day=1),
                (datetime.now().date() - timedelta(days=30)).replace(day=1)
            )
            if not monthly_data.empty:
                monthly_data.to_excel(
                    writer,
                    sheet_name='Monthly Comparison',
                    index=False
                )
            
            # Write today's income
            today_data = self.get_today_income_data()
            if not today_data.empty:
                today_data.to_excel(
                    writer,
                    sheet_name="Today's Income",
                    index=False
                )
            
            # Get workbook and add formats
            workbook = writer.book
            currency_format = workbook.add_format({'num_format': 'Rp#,##0'})
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            
            # Apply formats to each sheet
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                worksheet.set_column('A:A', 15, date_format)  # Date columns
                worksheet.set_column('B:D', 20)  # ID and name columns
                worksheet.set_column('E:G', 15, currency_format)  # Amount columns
        
        output.seek(0)
        return output.getvalue()

    def export_report(self, start_date, end_date, selected_stores=None):
        """Export reports to Excel"""
        total_income_df = self.get_total_income_data(start_date, end_date)
        store_income_df = self.get_store_income_data(start_date, end_date, selected_stores)
        
        excel_binary = self.generate_excel_report(
            total_income_df,
            store_income_df,
            start_date,
            end_date
        )
        
        # Download button for Excel file
        filename = f"income_report_{start_date}_to_{end_date}.xlsx"
        st.download_button(
            label="Download Excel Report",
            data=excel_binary,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    def render_create_report(self):
        """Render the Create Reports section"""
        st.header("Create Reports")
        
        # Get available years from data
        available_years = self.get_available_years()
        if not available_years:
            st.warning("No data available for reports.")
            return

        # Year selection
        current_year = datetime.now().year
        year = st.selectbox(
            "Year",
            options=available_years,
            index=available_years.index(current_year) if current_year in available_years else 0
        )

        # Period selection
        period = st.selectbox(
            "Period",
            options=["Current Month", "Monthly", "Quarterly", "Yearly"]
        )

        # Period-specific selections and report generation
        if period == "Current Month":
            self.generate_current_month_report(year)
        elif period == "Monthly":
            month = st.selectbox(
                "Select Month",
                options=range(1, 13),
                format_func=lambda x: calendar.month_name[x]
            )
            self.generate_monthly_report(year, month)
        elif period == "Quarterly":
            # Get completed quarters
            available_quarters = self.get_available_quarters(year)
            if available_quarters:
                quarter = st.selectbox(
                    "Select Quarter",
                    options=available_quarters,
                    format_func=lambda x: f"Q{x}"
                )
                self.generate_quarterly_report(year, quarter)
            else:
                st.info("No completed quarters available for selected year.")
        elif period == "Yearly":
            # Only show completed years
            if self.is_year_complete(year):
                self.generate_yearly_report(year)
            else:
                st.info("Selected year is not yet complete.")

    def get_available_years(self):
        """Get list of years available in data"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT DISTINCT EXTRACT(YEAR FROM date) as year
                    FROM income_data
                    WHERE username = %s
                    ORDER BY year DESC
                """, (st.session_state.username,))
                return [int(row['year']) for row in cur.fetchall()]
        except Exception as e:
            st.error(f"Error fetching available years: {str(e)}")
            return []

    def get_available_quarters(self, year):
        """Get list of completed quarters for given year"""
        current_date = datetime.now()
        current_year = current_date.year
        current_quarter = (current_date.month - 1) // 3 + 1
        
        if year < current_year:
            return [1, 2, 3, 4]  # All quarters for past years
        elif year == current_year:
            return list(range(1, current_quarter))  # Only completed quarters
        return []  # No quarters for future years

    def is_year_complete(self, year):
        """Check if year is complete"""
        current_date = datetime.now()
        return year < current_date.year
    
    def generate_current_month_pdf(self, comparison_data, monthly_chart,
                                 visitors_data, orders_data, sales_data,
                                 daily_visitors, daily_orders, daily_sales,
                                 month_year):
        """Generate PDF for current month report including all data"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20,
            leftMargin=20,
            topMargin=30,
            bottomMargin=30
        )
        
        # Calculate available width
        available_width = doc.width + doc.rightMargin + doc.leftMargin
        
        story = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            spaceAfter=30
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceAfter=20
        )
        
        # Title
        story.append(Paragraph(f"Current Month Report - {month_year}", title_style))
        story.append(Spacer(1, 20))
        
        # Income section
        story.append(Paragraph("Monthly Income Comparison", subtitle_style))
        if monthly_chart:
            chart_buffer = self.save_chart_for_pdf(monthly_chart)
            if chart_buffer:
                story.append(Image(chart_buffer, width=available_width, height=300))
        
        if not comparison_data.empty:
            story.append(Spacer(1, 20))
            income_table = self.create_pdf_table(comparison_data)
            story.append(income_table)
        
        story.append(Spacer(1, 30))
        
        # Visitors section
        if not visitors_data.empty:
            story.append(Paragraph("Monthly Visitors Comparison", subtitle_style))
            visitors_table = self.create_pdf_table(visitors_data)
            story.append(visitors_table)
            story.append(Spacer(1, 20))
            
            if not daily_visitors.empty:
                story.append(Paragraph("Visitors Today", subtitle_style))
                daily_visitors_table = self.create_pdf_table(daily_visitors)
                story.append(daily_visitors_table)
                story.append(Spacer(1, 30))
        
        # Orders section
        if not orders_data.empty:
            story.append(Paragraph("Monthly Orders Comparison", subtitle_style))
            orders_table = self.create_pdf_table(orders_data)
            story.append(orders_table)
            story.append(Spacer(1, 20))
            
            if not daily_orders.empty:
                story.append(Paragraph("Orders Today", subtitle_style))
                daily_orders_table = self.create_pdf_table(daily_orders)
                story.append(daily_orders_table)
                story.append(Spacer(1, 30))
        
        # Sales section
        if not sales_data.empty:
            story.append(Paragraph("Monthly Sales Comparison", subtitle_style))
            sales_table = self.create_pdf_table(sales_data)
            story.append(sales_table)
            story.append(Spacer(1, 20))
            
            if not daily_sales.empty:
                story.append(Paragraph("Sales Today", subtitle_style))
                daily_sales_table = self.create_pdf_table(daily_sales)
                story.append(daily_sales_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def create_current_month_chart(self, comparison_data):
        """Create comparison bar chart for current month"""
        # Extract current and previous month columns
        current_month_col = comparison_data.columns[1]  # The current month column
        prev_month_col = comparison_data.columns[2]     # The previous month column
        
        # Create figure
        fig = go.Figure()
        
        # Add current month bars
        fig.add_trace(go.Bar(
            x=comparison_data['Accounts'],
            y=comparison_data[current_month_col].apply(
                lambda x: float(x.replace('Rp', '').replace(',', ''))
            ),
            name=current_month_col,
            text=comparison_data[current_month_col],
            textposition='auto',
        ))
        
        # Add previous month bars
        fig.add_trace(go.Bar(
            x=comparison_data['Accounts'],
            y=comparison_data[prev_month_col].apply(
                lambda x: float(x.replace('Rp', '').replace(',', ''))
            ),
            name=prev_month_col,
            text=comparison_data[prev_month_col],
            textposition='auto',
            opacity=0.7
        ))
        
        # Update layout
        fig.update_layout(
            title="Current Month vs Previous Month Comparison",
            xaxis_title="Store Accounts",
            yaxis_title="Net Income (Rp)",
            barmode='group',
            height=500,
            xaxis={'categoryorder':'total descending'}  # Order bars by total value
        )
        
        return fig
    
    def create_daily_comparison_chart(self, daily_data):
        """Create bar chart for today vs yesterday comparison"""
        try:
            # Convert currency strings back to numbers for plotting
            df = daily_data.copy()
            for col in ['today_income', 'yesterday_income']:
                df[col] = df[col].str.replace('Rp', '').str.replace(',', '').astype(float)
            
            fig = go.Figure()
            
            # Add today's bars
            fig.add_trace(go.Bar(
                x=df['Accounts'],
                y=df['today_income'],
                name="Today",
                text=daily_data['today_income'],
                textposition='auto',
            ))
            
            # Add yesterday's bars
            fig.add_trace(go.Bar(
                x=df['Accounts'],
                y=df['yesterday_income'],
                name="Yesterday",
                text=daily_data['yesterday_income'],
                textposition='auto',
                opacity=0.7
            ))
            
            # Update layout with legend at bottom
            fig.update_layout(
                title="Today vs Yesterday Income Comparison",
                xaxis_title="Store Accounts",
                yaxis_title="Net Income (Rp)",
                barmode='group',
                height=500,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.25,
                    xanchor="center",
                    x=0.5
                ),
                margin=dict(l=50, r=50, t=70, b=100)  # Adjust margins for legend
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating daily comparison chart: {str(e)}")
            return None

    def create_as_per_today_table(self, current_data, prev_data):
        """Create as per today comparison table"""
        # Group by store_account_id
        current_totals = current_data.groupby('store_account_id')['net_income'].sum()
        prev_totals = prev_data.groupby('store_account_id')['net_income'].sum()
        
        # Create DataFrame
        df = pd.DataFrame({
            'Accounts': current_totals.index,
            current_data['date'].dt.strftime('%B %Y').iloc[0]: current_totals.values,
            prev_data['date'].dt.strftime('%B %Y').iloc[0]: prev_totals
        })
        
        # Calculate differences
        df['Difference Rp'] = df.iloc[:, 1] - df.iloc[:, 2]
        df['Difference %'] = (df['Difference Rp'] / df.iloc[:, 2] * 100).round(2)
        
        # Add total row
        total_row = pd.DataFrame({
            'Accounts': ['Total'],
            df.columns[1]: [df.iloc[:, 1].sum()],
            df.columns[2]: [df.iloc[:, 2].sum()],
            'Difference Rp': [df['Difference Rp'].sum()],
            'Difference %': [(df.iloc[:, 1].sum() - df.iloc[:, 2].sum()) / df.iloc[:, 2].sum() * 100]
        })
        
        df = pd.concat([df, total_row])
        
        # Format currency columns
        for col in [df.columns[1], df.columns[2], 'Difference Rp']:
            df[col] = df[col].apply(lambda x: f"Rp{x:,.0f}")
        df['Difference %'] = df['Difference %'].apply(lambda x: f"{x:,.2f}%")
        
        return df

    def create_todays_income_table(self, current_data, prev_data):
        """Create today's income comparison table"""
        # Get today's data and last month's same day
        today = current_data['date'].max()
        current_today = current_data[current_data['date'] == today]
        prev_today = prev_data[prev_data['date'] == today]
        
        # Group by store_account_id
        current_totals = current_today.groupby('store_account_id')['net_income'].sum()
        prev_totals = prev_today.groupby('store_account_id')['net_income'].sum()
        
        # Create DataFrame
        df = pd.DataFrame({
            'Accounts': current_totals.index,
            current_today['date'].dt.strftime('%B %Y').iloc[0]: current_totals.values,
            prev_today['date'].dt.strftime('%B %Y').iloc[0]: prev_totals
        })
        
        # Calculate differences
        df['Difference Rp'] = df.iloc[:, 1] - df.iloc[:, 2]
        df['Difference %'] = (df['Difference Rp'] / df.iloc[:, 2] * 100).round(2)
        
        # Add total row
        total_row = pd.DataFrame({
            'Accounts': ['Total'],
            df.columns[1]: [df.iloc[:, 1].sum()],
            df.columns[2]: [df.iloc[:, 2].sum()],
            'Difference Rp': [df['Difference Rp'].sum()],
            'Difference %': [(df.iloc[:, 1].sum() - df.iloc[:, 2].sum()) / df.iloc[:, 2].sum() * 100]
        })
        
        df = pd.concat([df, total_row])
        
        # Format currency columns
        for col in [df.columns[1], df.columns[2], 'Difference Rp']:
            df[col] = df[col].apply(lambda x: f"Rp{x:,.0f}")
        df['Difference %'] = df['Difference %'].apply(lambda x: f"{x:,.2f}%")
        
        return df

    def generate_current_month_report(self, year):
        """Generate current month report"""
        try:
            current_date = datetime.now()
            current_month = current_date.month
            
            # Income comparison section
            comparison_data = self.get_monthly_comparison_data(
                current_date.replace(day=1),
                (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
            )
            
            if not comparison_data.empty:
                st.subheader("Monthly Income Comparison")
                monthly_chart = self.create_current_month_chart(comparison_data)
                st.plotly_chart(monthly_chart, use_container_width=True)
                st.dataframe(comparison_data, hide_index=True, use_container_width=True)

            # Admin input data section
            st.markdown("---")
            
            # Visitors section
            st.subheader("Monthly Visitors Comparison")
            visitors_data = self.get_admin_monthly_comparison_data(  # Fixed method name
                "Pengunjung",
                current_date.replace(day=1),
                (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
            )
            if not visitors_data.empty:
                st.dataframe(visitors_data, hide_index=True, use_container_width=True)
                
            # Today's visitors
            st.subheader("Visitors Today")
            daily_visitors = self.get_daily_admin_comparison_data("Pengunjung")
            if not daily_visitors.empty:
                st.dataframe(daily_visitors, hide_index=True, use_container_width=True)
            else:
                st.info("No visitors data for today")
            
            st.markdown("---")
            
            # Orders section
            st.subheader("Monthly Orders Comparison")
            orders_data = self.get_admin_monthly_comparison_data(  # Fixed method name
                "Pesanan",
                current_date.replace(day=1),
                (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
            )
            if not orders_data.empty:
                st.dataframe(orders_data, hide_index=True, use_container_width=True)
                
            # Today's orders
            st.subheader("Orders Today")
            daily_orders = self.get_daily_admin_comparison_data("Pesanan")
            if not daily_orders.empty:
                st.dataframe(daily_orders, hide_index=True, use_container_width=True)
            else:
                st.info("No orders data for today")
            
            st.markdown("---")
            
            # Sales section
            st.subheader("Monthly Sales Comparison")
            sales_data = self.get_admin_monthly_comparison_data(  # Fixed method name
                "Penjualan",
                current_date.replace(day=1),
                (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
            )
            if not sales_data.empty:
                st.dataframe(sales_data, hide_index=True, use_container_width=True)
                
            # Today's sales
            st.subheader("Sales Today")
            daily_sales = self.get_daily_admin_comparison_data("Penjualan")
            if not daily_sales.empty:
                st.dataframe(daily_sales, hide_index=True, use_container_width=True)
            else:
                st.info("No sales data for today")
            
            # Generate PDF button
            #st.markdown("---")
            #if st.button("Generate PDF Report"):
            #    pdf = self.generate_current_month_pdf(
            #        comparison_data=comparison_data,
            #        monthly_chart=monthly_chart,
            #        visitors_data=visitors_data if 'visitors_data' in locals() else None,
            #        orders_data=orders_data if 'orders_data' in locals() else None,
            #        sales_data=sales_data if 'sales_data' in locals() else None,
            #        daily_visitors=daily_visitors if 'daily_visitors' in locals() else None,
            #       daily_orders=daily_orders if 'daily_orders' in locals() else None,
            #        daily_sales=daily_sales if 'daily_sales' in locals() else None,
            #        month_year=current_date.strftime('%B %Y')
            #   )
            #    st.download_button(
            #        "Download PDF",
            #        data=pdf,
            #        file_name=f"current_month_report_{current_date.strftime('%Y_%m')}.pdf",
            #        mime="application/pdf"
            #    )
                
        except Exception as e:
            st.error(f"Error generating current month report: {str(e)}")
            import traceback
            st.error(traceback.format_exc())

    def create_pdf_table(self, df):
        """Create formatted table for PDF with totals row"""
        try:
            # Create totals dictionary
            totals_dict = {}
            for column in df.columns:
                if column == df.columns[0]:  # First column (usually 'Accounts')
                    totals_dict[column] = 'Total'
                elif 'Rp' in str(df[column].iloc[0]):  # Currency columns
                    value = df[column].str.replace('Rp', '').str.replace(',', '').astype(float).sum()
                    totals_dict[column] = f"Rp{value:,.0f}"
                elif '%' in str(df[column].iloc[0]):  # Percentage columns
                    totals_dict[column] = ''
                else:
                    totals_dict[column] = ''
            
            # Create totals row DataFrame
            totals_df = pd.DataFrame([totals_dict])
            
            # Combine data with totals
            df_with_totals = pd.concat([df, totals_df], ignore_index=True)
            
            # Convert DataFrame to list of lists
            data = [df_with_totals.columns.tolist()] + df_with_totals.values.tolist()
            
            # Create table
            table = Table(data)
            
            # Style table
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Header row
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, -1), (-1, -1), colors.grey),  # Totals row
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),  # Right align numbers
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),    # Left align first column
            ])
            
            # Add alternating row colors
            for i in range(1, len(data)-1):
                if i % 2 == 0:
                    style.add('BACKGROUND', (0, i), (-1, i), colors.whitesmoke)
                else:
                    style.add('BACKGROUND', (0, i), (-1, i), colors.white)
            
            table.setStyle(style)
            return table
            
        except Exception as e:
            st.error(f"Error creating PDF table: {str(e)}")
            return None
    
    def generate_monthly_report(self, year, month):
        try:
            # Get monthly data
            monthly_data = self.get_all_monthly_data(year)
            if monthly_data.empty:
                st.warning("No data available for selected period.")
                return
            
            # Create and display bar chart
            fig = self.create_monthly_bar_chart(monthly_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Get comparison dates
            selected_date = datetime(year, month, 1).date()
            prev_date = (selected_date - timedelta(days=1)).replace(day=1)
            
            # Income comparison
            st.subheader(f"{calendar.month_name[month]} Income Report")
            monthly_table = self.create_monthly_comparison_table(year, month)
            if not monthly_table.empty:
                st.dataframe(monthly_table, use_container_width=True)
            
            st.markdown("---")
            
            # Visitors comparison
            st.subheader(f"{calendar.month_name[month]} Visitors Report")
            visitors_data = self.get_admin_monthly_comparison_data(  # Fixed method name
                "Pengunjung",
                selected_date,
                prev_date
            )
            if not visitors_data.empty:
                st.dataframe(visitors_data, hide_index=True, use_container_width=True)
            
            st.markdown("---")
            
            # Orders comparison
            st.subheader(f"{calendar.month_name[month]} Orders Report")
            orders_data = self.get_admin_monthly_comparison_data(  # Fixed method name
                "Pesanan",
                selected_date,
                prev_date
            )
            if not orders_data.empty:
                st.dataframe(orders_data, hide_index=True, use_container_width=True)
            
            st.markdown("---")
            
            # Sales comparison
            st.subheader(f"{calendar.month_name[month]} Sales Report")
            sales_data = self.get_admin_monthly_comparison_data(  # Fixed method name
                "Penjualan",
                selected_date,
                prev_date
            )
            if not sales_data.empty:
                st.dataframe(sales_data, hide_index=True, use_container_width=True)
            
            # Generate PDF button
            #st.markdown("---")
            #if st.button("Generate PDF Report"):
            #    pdf = self.generate_monthly_pdf(
            #        monthly_data=monthly_data,
            #        monthly_table=monthly_table,
            #        visitors_data=visitors_data if 'visitors_data' in locals() else None,
            #        orders_data=orders_data if 'orders_data' in locals() else None,
            #       sales_data=sales_data if 'sales_data' in locals() else None,
            #        fig=fig,
            #        year=year,
            #        month=month
            #    )
            #    st.download_button(
            #        "Download PDF",
            #      file_name=f"monthly_report_{year}_{month:02d}.pdf",
            #       mime="application/pdf"
            #    )
                
        except Exception as e:
            st.error(f"Error generating monthly report: {str(e)}")

    def get_all_monthly_data(self, year):
        """Get all monthly data for the year"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    SELECT 
                        date_trunc('month', date) as month,
                        SUM(net_income) as net_income
                    FROM income_data
                    WHERE username = %s
                    AND EXTRACT(YEAR FROM date) = %s
                    GROUP BY date_trunc('month', date)
                    ORDER BY month
                """, (st.session_state.username, year))
                return pd.DataFrame(cur.fetchall())
        except Exception as e:
            st.error(f"Error fetching monthly data: {str(e)}")
            return pd.DataFrame()

    def create_monthly_bar_chart(self, monthly_data):
        """Create monthly bar chart"""
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=monthly_data['month'].dt.strftime('%B'),  # Changed x to y for horizontal
            x=monthly_data['net_income'],               # Changed y to x for horizontal
            text=monthly_data['net_income'].apply(lambda x: f'Rp{x:,.0f}'),
            textposition='auto',
            orientation='h'  # Make bars horizontal
        ))
        
        fig.update_layout(
            title="Monthly Report",
            yaxis_title="Month",          # Swapped axis titles
            xaxis_title="Net Income (Rp)",
            height=500,
            showlegend=False,
            yaxis={'categoryorder':'total ascending'}  # Order bars by value
        )
        
        return fig

    def create_current_month_chart(self, comparison_data):
        """Create comparison bar chart for current month"""
        # Extract current and previous month columns
        current_month_col = comparison_data.columns[1]  # The current month column
        prev_month_col = comparison_data.columns[2]     # The previous month column
        
        fig = go.Figure()
        
        # Add current month bars
        fig.add_trace(go.Bar(
            y=comparison_data['Accounts'],  # Changed to y for horizontal
            x=comparison_data[current_month_col].apply(
                lambda x: float(x.replace('Rp', '').replace(',', ''))
            ),
            name=current_month_col,
            text=comparison_data[current_month_col],
            textposition='auto',
            orientation='h'  # Make bars horizontal
        ))
        
        # Add previous month bars
        fig.add_trace(go.Bar(
            y=comparison_data['Accounts'],  # Changed to y for horizontal
            x=comparison_data[prev_month_col].apply(
                lambda x: float(x.replace('Rp', '').replace(',', ''))
            ),
            name=prev_month_col,
            text=comparison_data[prev_month_col],
            textposition='auto',
            opacity=0.7,
            orientation='h'  # Make bars horizontal
        ))
        
        # Update layout
        fig.update_layout(
            title="Current Month vs Previous Month Comparison",
            yaxis_title="Store Accounts",        # Swapped axis titles
            xaxis_title="Net Income (Rp)",
            barmode='group',
            height=500,
            yaxis={'categoryorder':'total ascending'}  # Order bars by value
        )
        
        return fig

    def create_monthly_comparison_table(self, year, month):
        """Create monthly comparison table with safe calculations"""
        try:
            # Calculate previous month
            if month == 1:
                prev_month = 12
                prev_year = year - 1
            else:
                prev_month = month - 1
                prev_year = year

            with get_db_cursor() as cur:
                # First check if data exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM income_data
                        WHERE username = %s
                        AND EXTRACT(YEAR FROM date) = %s
                        AND EXTRACT(MONTH FROM date) = %s
                    )
                """, (st.session_state.username, year, month))
                
                has_data = cur.fetchone()['exists']
                
                if not has_data:
                    st.info(f"No data available for {calendar.month_name[month]} {year}")
                    return pd.DataFrame()

                # If data exists, proceed with comparison
                cur.execute("""
                    WITH selected_month_data AS (
                        SELECT 
                            store_account_id,
                            SUM(net_income) as selected_month_income
                        FROM income_data
                        WHERE username = %s
                        AND EXTRACT(YEAR FROM date) = %s
                        AND EXTRACT(MONTH FROM date) = %s
                        GROUP BY store_account_id
                    ),
                    prev_month_data AS (
                        SELECT 
                            store_account_id,
                            SUM(net_income) as prev_month_income
                        FROM income_data
                        WHERE username = %s
                        AND EXTRACT(YEAR FROM date) = %s
                        AND EXTRACT(MONTH FROM date) = %s
                        GROUP BY store_account_id
                    )
                    SELECT 
                        COALESCE(s.store_account_id, p.store_account_id) as "Accounts",
                        COALESCE(s.selected_month_income, 0) as selected_month_income,
                        COALESCE(p.prev_month_income, 0) as prev_month_income
                    FROM selected_month_data s
                    FULL OUTER JOIN prev_month_data p ON s.store_account_id = p.store_account_id
                    WHERE COALESCE(s.selected_month_income, 0) != 0 
                       OR COALESCE(p.prev_month_income, 0) != 0
                    ORDER BY "Accounts"
                """, (st.session_state.username, year, month,
                     st.session_state.username, prev_year, prev_month))
                
                result = cur.fetchall()
                if not result:
                    return pd.DataFrame()
                    
                df = pd.DataFrame(result)
                
                # Calculate differences safely
                df['Difference Rp'] = df['selected_month_income'] - df['prev_month_income']
                
                # Safe percentage calculation
                df['Difference %'] = df.apply(lambda row: 
                    0 if row['prev_month_income'] == 0
                    else (row['Difference Rp'] / row['prev_month_income'] * 100)
                    if row['prev_month_income'] != 0 else 0, axis=1)
                
                # Rename columns with month names
                df = df.rename(columns={
                    'selected_month_income': calendar.month_name[month],
                    'prev_month_income': calendar.month_name[prev_month]
                })
                
                # Format currency columns
                currency_cols = [calendar.month_name[month], 
                               calendar.month_name[prev_month], 
                               'Difference Rp']
                for col in currency_cols:
                    df[col] = df[col].apply(lambda x: f"Rp{x:,.0f}")
                df['Difference %'] = df['Difference %'].apply(lambda x: f"{x:,.2f}%")
                
                return df
                
        except Exception as e:
            st.info(f"No data available for {calendar.month_name[month]} {year}")
            return pd.DataFrame()
    
    def save_chart_for_pdf(self, fig):
        """Save plotly figure as bytes for PDF with optimized settings"""
        try:
            # Update chart layout for PDF
            fig.update_layout(
                # Make font bigger and clearer
                font=dict(
                    size=10,  # Adjust size: 9-11 points
                    family="Arial"
                ),
                # Adjust margins
                margin=dict(
                    l=50,    # Adjust margins: 40-60 points
                    r=50,    # Adjust margins: 40-60 points
                    t=50,    # Adjust margins: 40-60 points
                    b=50     # Adjust margins: 40-60 points
                ),
                # Position legend at bottom
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.3,  # Adjust position: -0.2 to -0.4
                    xanchor="center",
                    x=0.5
                ),
                # Ensure white background
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            # Convert plot to PNG bytes with high DPI
            img_bytes = fig.to_image(
                format="png",
                width=900,     # Adjust width: 800-1000 pixels
                height=500,    # Adjust height: 400-600 pixels
                scale=2        # Adjust scale: 2-3 (higher means better quality)
            )
            return BytesIO(img_bytes)
            
        except Exception as e:
            st.error(f"Error converting chart: {str(e)}")
            return None
    
    def generate_current_month_pdf(self, comparison_data, monthly_chart,
                                 visitors_data, orders_data, sales_data,
                                 daily_visitors, daily_orders, daily_sales,
                                 month_year):
        """Generate PDF for current month report including all data"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20,
            leftMargin=20,
            topMargin=30,
            bottomMargin=30
        )
        
        # Calculate available width
        available_width = doc.width + doc.rightMargin + doc.leftMargin
        
        story = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            spaceAfter=30
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceAfter=20
        )
        
        # Title
        story.append(Paragraph(f"Current Month Report - {month_year}", title_style))
        story.append(Spacer(1, 20))
        
        # Income section
        if monthly_chart is not None:
            story.append(Paragraph("Monthly Income Comparison", subtitle_style))
            chart_buffer = self.save_chart_for_pdf(monthly_chart)
            if chart_buffer:
                story.append(Image(chart_buffer, width=available_width, height=300))
        
            if comparison_data is not None and not comparison_data.empty:
                story.append(Spacer(1, 20))
                income_table = self.create_pdf_table(comparison_data)
                story.append(income_table)
        
        story.append(Spacer(1, 30))
        
        # Visitors section
        if visitors_data is not None and not visitors_data.empty:
            story.append(Paragraph("Monthly Visitors Comparison", subtitle_style))
            visitors_table = self.create_pdf_table(visitors_data)
            story.append(visitors_table)
            story.append(Spacer(1, 20))
            
            if daily_visitors is not None and not daily_visitors.empty:
                story.append(Paragraph("Visitors Today", subtitle_style))
                daily_visitors_table = self.create_pdf_table(daily_visitors)
                story.append(daily_visitors_table)
                story.append(Spacer(1, 30))
        
        # Orders section
        if orders_data is not None and not orders_data.empty:
            story.append(Paragraph("Monthly Orders Comparison", subtitle_style))
            orders_table = self.create_pdf_table(orders_data)
            story.append(orders_table)
            story.append(Spacer(1, 20))
            
            if daily_orders is not None and not daily_orders.empty:
                story.append(Paragraph("Orders Today", subtitle_style))
                daily_orders_table = self.create_pdf_table(daily_orders)
                story.append(daily_orders_table)
                story.append(Spacer(1, 30))
        
        # Sales section
        if sales_data is not None and not sales_data.empty:
            story.append(Paragraph("Monthly Sales Comparison", subtitle_style))
            sales_table = self.create_pdf_table(sales_data)
            story.append(sales_table)
            story.append(Spacer(1, 20))
            
            if daily_sales is not None and not daily_sales.empty:
                story.append(Paragraph("Sales Today", subtitle_style))
                daily_sales_table = self.create_pdf_table(daily_sales)
                story.append(daily_sales_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_current_month_pdf(self, comparison_data, monthly_chart,
                                 visitors_data, orders_data, sales_data,
                                 daily_visitors, daily_orders, daily_sales,
                                 month_year):
        """Generate PDF for current month report including all data"""
        buffer = BytesIO()
        
        # Page setup with narrow margins (all measurements in points; 1 inch = 72 points)
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,  # 210mm × 297mm
            rightMargin=36,      # 0.5 inch (36 points)  # Adjust margin: 36-72 points
            leftMargin=36,       # 0.5 inch
            topMargin=36,        # 0.5 inch
            bottomMargin=36      # 0.5 inch
        )
        
        # Calculate available width for content
        available_width = doc.width + doc.rightMargin + doc.leftMargin
        
        # Define styles
        styles = getSampleStyleSheet()
        
        # Main Title (H1) Style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',  # Using Helvetica as it's similar to Arial
            fontSize=16,
            spaceAfter=30,             # Adjust spacing: 20-40 points
            spaceBefore=10,            # Adjust spacing: 5-15 points
            leading=24,                # Line height (1.5 × fontSize)
            alignment=0                # 0=left, 1=center, 2=right
        )
        
        # Section Header (H2) Style
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceAfter=25,             # Adjust spacing: 15-30 points
            spaceBefore=15,            # Adjust spacing: 10-20 points
            leading=21,                # 1.5 × fontSize
            alignment=0
        )
        
        # Subsection Header (H3) Style
        subsection_style = ParagraphStyle(
            'SubsectionHeader',
            parent=styles['Heading3'],
            fontName='Helvetica-Bold',
            fontSize=12,
            spaceAfter=20,             # Adjust spacing: 10-25 points
            spaceBefore=10,            # Adjust spacing: 5-15 points
            leading=18,                # 1.5 × fontSize
            alignment=0
        )
        
        # Normal Text Style
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontName='Helvetica',      # Base font
            fontSize=11,
            leading=16.5,              # 1.5 × fontSize
            spaceBefore=6,             # Adjust spacing: 4-8 points
            spaceAfter=6               # Adjust spacing: 4-8 points
        )
        
        # Table Styles
        table_style = TableStyle([
            # Table header
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),      # Header font size
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 10),      # Adjust size: 9-11 points
            # Numeric column alignment
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),    # All number columns right-aligned
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),      # First column left-aligned
            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.black),
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.whitesmoke, colors.white]),
            # Total row style
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 10),     # Adjust size: 9-11 points
            ('BACKGROUND', (0, -1), (-1, -1), colors.grey),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.whitesmoke),
            # Cell padding
            ('TOPPADDING', (0, 0), (-1, -1), 6),     # Adjust padding: 4-8 points
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6)   # Adjust padding: 4-8 points
        ])

        # Story (content) initialization
        story = []
        
        # Title
        story.append(Paragraph(f"Current Month Report - {month_year}", title_style))
        story.append(Spacer(1, 20))  # Adjust spacing: 15-25 points
        
        # Income section
        if monthly_chart is not None:
            story.append(Paragraph("Monthly Income Comparison", section_style))
            chart_buffer = self.save_chart_for_pdf(monthly_chart)
            if chart_buffer:
                # Make chart full width with reasonable height
                story.append(Image(chart_buffer, width=available_width,
                                 height=200))  # Adjust height: 180-250 points
            
            if comparison_data is not None and not comparison_data.empty:
                story.append(Spacer(1, 15))  # Adjust spacing: 10-20 points
                story.append(Paragraph("Income Details", subsection_style))
                income_table = Table(comparison_data.values.tolist(), 
                                   repeatRows=1,  # Repeat header row on new pages
                                   colWidths=[available_width/len(comparison_data.columns)]*len(comparison_data.columns))
                income_table.setStyle(table_style)
                story.append(income_table)
        
        story.append(Spacer(1, 30))  # Adjust spacing: 25-35 points
        
        # Visitors section
        if visitors_data is not None and not visitors_data.empty:
            story.append(Paragraph("Monthly Visitors Comparison", section_style))
            visitors_table = Table(visitors_data.values.tolist(),
                                 repeatRows=1,
                                 colWidths=[available_width/len(visitors_data.columns)]*len(visitors_data.columns))
            visitors_table.setStyle(table_style)
            story.append(visitors_table)
            story.append(Spacer(1, 20))  # Adjust spacing: 15-25 points
            
            if daily_visitors is not None and not daily_visitors.empty:
                story.append(Paragraph("Visitors Today", subsection_style))
                daily_visitors_table = Table(daily_visitors.values.tolist(),
                                          repeatRows=1,
                                          colWidths=[available_width/len(daily_visitors.columns)]*len(daily_visitors.columns))
                daily_visitors_table.setStyle(table_style)
                story.append(daily_visitors_table)
            story.append(Spacer(1, 30))  # Adjust spacing: 25-35 points
        
        # Orders section
        if orders_data is not None and not orders_data.empty:
            story.append(Paragraph("Monthly Orders Comparison", section_style))
            orders_table = Table(orders_data.values.tolist(),
                               repeatRows=1,
                               colWidths=[available_width/len(orders_data.columns)]*len(orders_data.columns))
            orders_table.setStyle(table_style)
            story.append(orders_table)
            story.append(Spacer(1, 20))  # Adjust spacing: 15-25 points
            
            if daily_orders is not None and not daily_orders.empty:
                story.append(Paragraph("Orders Today", subsection_style))
                daily_orders_table = Table(daily_orders.values.tolist(),
                                        repeatRows=1,
                                        colWidths=[available_width/len(daily_orders.columns)]*len(daily_orders.columns))
                daily_orders_table.setStyle(table_style)
                story.append(daily_orders_table)
            story.append(Spacer(1, 30))  # Adjust spacing: 25-35 points
        
        # Sales section
        if sales_data is not None and not sales_data.empty:
            story.append(Paragraph("Monthly Sales Comparison", section_style))
            sales_table = Table(sales_data.values.tolist(),
                              repeatRows=1,
                              colWidths=[available_width/len(sales_data.columns)]*len(sales_data.columns))
            sales_table.setStyle(table_style)
            story.append(sales_table)
            story.append(Spacer(1, 20))  # Adjust spacing: 15-25 points
            
            if daily_sales is not None and not daily_sales.empty:
                story.append(Paragraph("Sales Today", subsection_style))
                daily_sales_table = Table(daily_sales.values.tolist(),
                                       repeatRows=1,
                                       colWidths=[available_width/len(daily_sales.columns)]*len(daily_sales.columns))
                daily_sales_table.setStyle(table_style)
                story.append(daily_sales_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_quarterly_report(self, year, quarter):
        """Generate quarterly report"""
        try:
            # Get quarterly data
            quarterly_data = self.get_all_quarterly_data(year)
            if quarterly_data.empty:
                st.warning("No data available for selected period.")
                return
            
            # Create and display bar chart
            fig = self.create_quarterly_bar_chart(quarterly_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Create and display quarterly comparison table
            st.subheader(f"Q{quarter} Income Report")
            quarterly_table = self.create_quarterly_comparison_table(year, quarter)
            st.dataframe(quarterly_table, use_container_width=True)
            
            
            # Generate PDF button
            #if st.button("Generate PDF Report"):
            #    pdf = self.generate_quarterly_pdf(
            #        quarterly_data,
            #        quarterly_table,
            #       fig,
            #        year,
            #        quarter
            #    )
            #    st.download_button(
            #        "Download PDF",
            #        data=pdf,
            #        file_name=f"quarterly_report_{year}_Q{quarter}.pdf",
            #        mime="application/pdf"
            #    )
                
        except Exception as e:
            st.error(f"Error generating quarterly report: {str(e)}")

    def get_all_quarterly_data(self, year):
        """Get all quarterly data for the year"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    WITH quarterly_data AS (
                        SELECT 
                            date,
                            net_income,
                            EXTRACT(QUARTER FROM date) as quarter
                        FROM income_data
                        WHERE username = %s
                        AND EXTRACT(YEAR FROM date) = %s
                    )
                    SELECT 
                        quarter,
                        SUM(net_income) as net_income
                    FROM quarterly_data
                    WHERE quarter <= (
                        CASE 
                            WHEN EXTRACT(YEAR FROM CURRENT_DATE) = %s 
                            THEN EXTRACT(QUARTER FROM CURRENT_DATE - INTERVAL '1 month')
                            ELSE 4 
                        END
                    )
                    GROUP BY quarter
                    ORDER BY quarter
                """, (st.session_state.username, year, year))
                return pd.DataFrame(cur.fetchall())
        except Exception as e:
            st.error(f"Error fetching quarterly data: {str(e)}")
            return pd.DataFrame()

    def create_quarterly_bar_chart(self, quarterly_data):
        """Create quarterly bar chart"""
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=[f'Q{int(q)}' for q in quarterly_data['quarter']],
            y=quarterly_data['net_income'],
            text=quarterly_data['net_income'].apply(lambda x: f'Rp{x:,.0f}'),
            textposition='auto',
        ))
        
        fig.update_layout(
            title="Quarter Report",
            xaxis_title="Quarter",
            yaxis_title="Net Income (Rp)",
            height=500,
            showlegend=False
        )
        
        return fig

    def create_quarterly_comparison_table(self, year, selected_quarter):
        """Create quarterly comparison table"""
        try:
            # Calculate previous quarter
            if selected_quarter == 1:
                prev_quarter = 4
                prev_year = year - 1
            else:
                prev_quarter = selected_quarter - 1
                prev_year = year

            with get_db_cursor() as cur:
                # Get data for selected quarter and previous quarter
                cur.execute("""
                    WITH selected_quarter_data AS (
                        SELECT 
                            store_account_id,
                            SUM(net_income) as selected_quarter_income
                        FROM income_data
                        WHERE username = %s
                        AND EXTRACT(YEAR FROM date) = %s
                        AND EXTRACT(QUARTER FROM date) = %s
                        GROUP BY store_account_id
                    ),
                    prev_quarter_data AS (
                        SELECT 
                            store_account_id,
                            SUM(net_income) as prev_quarter_income
                        FROM income_data
                        WHERE username = %s
                        AND EXTRACT(YEAR FROM date) = %s
                        AND EXTRACT(QUARTER FROM date) = %s
                        GROUP BY store_account_id
                    )
                    SELECT 
                        COALESCE(s.store_account_id, p.store_account_id) as "Accounts",
                        COALESCE(s.selected_quarter_income, 0) as selected_quarter_income,
                        COALESCE(p.prev_quarter_income, 0) as prev_quarter_income
                    FROM selected_quarter_data s
                    FULL OUTER JOIN prev_quarter_data p ON s.store_account_id = p.store_account_id
                    ORDER BY "Accounts"
                """, (st.session_state.username, year, selected_quarter,
                     st.session_state.username, prev_year, prev_quarter))
                
                result = cur.fetchall()
                if result:
                    df = pd.DataFrame(result)
                    
                    # Calculate differences
                    df['Difference Rp'] = df['selected_quarter_income'] - df['prev_quarter_income']
                    df['Difference %'] = (df['Difference Rp'] / df['prev_quarter_income'] * 100).round(2)
                    
                    # Add total row
                    total_row = pd.DataFrame({
                        'Accounts': ['Total'],
                        'selected_quarter_income': [df['selected_quarter_income'].sum()],
                        'prev_quarter_income': [df['prev_quarter_income'].sum()],
                        'Difference Rp': [df['Difference Rp'].sum()],
                        'Difference %': [(df['selected_quarter_income'].sum() - df['prev_quarter_income'].sum()) / 
                                       df['prev_quarter_income'].sum() * 100]
                    })
                    
                    df = pd.concat([df, total_row])
                    
                    # Rename columns with quarter names
                    df = df.rename(columns={
                        'selected_quarter_income': f'Q{selected_quarter} {year}',
                        'prev_quarter_income': f'Q{prev_quarter} {prev_year}'
                    })
                    
                    # Format currency columns
                    currency_cols = [f'Q{selected_quarter} {year}', 
                                   f'Q{prev_quarter} {prev_year}', 
                                   'Difference Rp']
                    for col in currency_cols:
                        df[col] = df[col].apply(lambda x: f"Rp{x:,.0f}")
                    df['Difference %'] = df['Difference %'].apply(lambda x: f"{x:,.2f}%")
                    
                    return df
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Error creating quarterly comparison table: {str(e)}")
            return pd.DataFrame()

    def generate_quarterly_pdf(self, quarterly_data, quarterly_table, fig, year, quarter):
        """Generate PDF for quarterly report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        # Prepare styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            spaceAfter=30
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceAfter=20
        )
        
        # Build story
        story = []
        
        # Title
        story.append(Paragraph(f"Quarterly Report - Q{quarter} {year}", title_style))
        story.append(Spacer(1, 20))
        
        # Chart
        with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
            fig.write_image(tmp.name, width=700, height=400)
            story.append(Image(tmp.name, width=500, height=300))
        
        story.append(Spacer(1, 20))
        
        # Quarterly comparison table
        story.append(Paragraph(f"Q{quarter} Income Report", subtitle_style))
        quarterly_comparison_table = self.create_pdf_table(quarterly_table)
        story.append(quarterly_comparison_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    def generate_quarterly_report(self, year, quarter):
        """Generate quarterly report"""
        try:
            # Get quarterly data
            quarterly_data = self.get_all_quarterly_data(year)
            if quarterly_data.empty:
                st.warning("No data available for selected period.")
                return
            
            # Create and display bar chart
            fig = self.create_quarterly_bar_chart(quarterly_data)
            st.plotly_chart(fig, use_container_width=True)
            
            # Create and display quarterly comparison table
            st.subheader(f"Q{quarter} Income Report")
            quarterly_table = self.create_quarterly_comparison_table(year, quarter)
            st.dataframe(quarterly_table, use_container_width=True)
            
            # Generate PDF button
            #if st.button("Generate PDF Report"):
            #    pdf = self.generate_quarterly_pdf(
            #        quarterly_data,
            #        quarterly_table,
            #        fig,
            #        year,
            #        quarter
            #    )
            #    st.download_button(
            #        "Download PDF",
            #        data=pdf,
            #        file_name=f"quarterly_report_{year}_Q{quarter}.pdf",
            #       mime="application/pdf"
            #   )
                
        except Exception as e:
            st.error(f"Error generating quarterly report: {str(e)}")

    def get_all_quarterly_data(self, year):
        """Get all quarterly data for the year"""
        try:
            with get_db_cursor() as cur:
                cur.execute("""
                    WITH quarterly_data AS (
                        SELECT 
                            date,
                            net_income,
                            EXTRACT(QUARTER FROM date) as quarter
                        FROM income_data
                        WHERE username = %s
                        AND EXTRACT(YEAR FROM date) = %s
                    )
                    SELECT 
                        quarter,
                        SUM(net_income) as net_income
                    FROM quarterly_data
                    WHERE quarter <= (
                        CASE 
                            WHEN EXTRACT(YEAR FROM CURRENT_DATE) = %s 
                            THEN EXTRACT(QUARTER FROM CURRENT_DATE - INTERVAL '1 month')
                            ELSE 4 
                        END
                    )
                    GROUP BY quarter
                    ORDER BY quarter
                """, (st.session_state.username, year, year))
                return pd.DataFrame(cur.fetchall())
        except Exception as e:
            st.error(f"Error fetching quarterly data: {str(e)}")
            return pd.DataFrame()

    def create_quarterly_bar_chart(self, quarterly_data):
        """Create quarterly bar chart"""
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=[f'Q{int(q)}' for q in quarterly_data['quarter']],
            y=quarterly_data['net_income'],
            text=quarterly_data['net_income'].apply(lambda x: f'Rp{x:,.0f}'),
            textposition='auto',
        ))
        
        fig.update_layout(
            title="Quarter Report",
            xaxis_title="Quarter",
            yaxis_title="Net Income (Rp)",
            height=500,
            showlegend=False
        )
        
        return fig

    def create_quarterly_comparison_table(self, year, selected_quarter):
        """Create quarterly comparison table"""
        try:
            # Calculate previous quarter
            if selected_quarter == 1:
                prev_quarter = 4
                prev_year = year - 1
            else:
                prev_quarter = selected_quarter - 1
                prev_year = year

            with get_db_cursor() as cur:
                # Get data for selected quarter and previous quarter
                cur.execute("""
                    WITH selected_quarter_data AS (
                        SELECT 
                            store_account_id,
                            SUM(net_income) as selected_quarter_income
                        FROM income_data
                        WHERE username = %s
                        AND EXTRACT(YEAR FROM date) = %s
                        AND EXTRACT(QUARTER FROM date) = %s
                        GROUP BY store_account_id
                    ),
                    prev_quarter_data AS (
                        SELECT 
                            store_account_id,
                            SUM(net_income) as prev_quarter_income
                        FROM income_data
                        WHERE username = %s
                        AND EXTRACT(YEAR FROM date) = %s
                        AND EXTRACT(QUARTER FROM date) = %s
                        GROUP BY store_account_id
                    )
                    SELECT 
                        COALESCE(s.store_account_id, p.store_account_id) as "Accounts",
                        COALESCE(s.selected_quarter_income, 0) as selected_quarter_income,
                        COALESCE(p.prev_quarter_income, 0) as prev_quarter_income
                    FROM selected_quarter_data s
                    FULL OUTER JOIN prev_quarter_data p ON s.store_account_id = p.store_account_id
                    ORDER BY "Accounts"
                """, (st.session_state.username, year, selected_quarter,
                     st.session_state.username, prev_year, prev_quarter))
                
                result = cur.fetchall()
                if result:
                    df = pd.DataFrame(result)
                    
                    # Calculate differences
                    df['Difference Rp'] = df['selected_quarter_income'] - df['prev_quarter_income']
                    df['Difference %'] = (df['Difference Rp'] / df['prev_quarter_income'] * 100).round(2)
                    
                    # Add total row
                    total_row = pd.DataFrame({
                        'Accounts': ['Total'],
                        'selected_quarter_income': [df['selected_quarter_income'].sum()],
                        'prev_quarter_income': [df['prev_quarter_income'].sum()],
                        'Difference Rp': [df['Difference Rp'].sum()],
                        'Difference %': [(df['selected_quarter_income'].sum() - df['prev_quarter_income'].sum()) / 
                                       df['prev_quarter_income'].sum() * 100]
                    })
                    
                    df = pd.concat([df, total_row])
                    
                    # Rename columns with quarter names
                    df = df.rename(columns={
                        'selected_quarter_income': f'Q{selected_quarter} {year}',
                        'prev_quarter_income': f'Q{prev_quarter} {prev_year}'
                    })
                    
                    # Format currency columns
                    currency_cols = [f'Q{selected_quarter} {year}', 
                                   f'Q{prev_quarter} {prev_year}', 
                                   'Difference Rp']
                    for col in currency_cols:
                        df[col] = df[col].apply(lambda x: f"Rp{x:,.0f}")
                    df['Difference %'] = df['Difference %'].apply(lambda x: f"{x:,.2f}%")
                    
                    return df
                return pd.DataFrame()
                
        except Exception as e:
            st.error(f"Error creating quarterly comparison table: {str(e)}")
            return pd.DataFrame()

    def generate_quarterly_pdf(self, quarterly_data, quarterly_table, fig, year, quarter):
        """Generate PDF for quarterly report"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        # Prepare styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=16,
            spaceAfter=30
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            spaceAfter=20
        )
        
        # Build story
        story = []
        
        # Title
        story.append(Paragraph(f"Quarterly Report - Q{quarter} {year}", title_style))
        story.append(Spacer(1, 20))
        
        # Chart
        with tempfile.NamedTemporaryFile(suffix='.png') as tmp:
            fig.write_image(tmp.name, width=700, height=400)
            story.append(Image(tmp.name, width=500, height=300))
        
        story.append(Spacer(1, 20))
        
        # Quarterly comparison table
        story.append(Paragraph(f"Q{quarter} Income Report", subtitle_style))
        quarterly_comparison_table = self.create_pdf_table(quarterly_table)
        story.append(quarterly_comparison_table)
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
