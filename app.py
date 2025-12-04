import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="Meta Insights Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Use Streamlit's cache to avoid reloading and re-processing data on every rerun
@st.cache_data
def load_and_process_data(uploaded_file, platform_name):
    """
    Loads, cleans, and preprocesses the uploaded CSV data based on platform-specific column names.
    """
    if uploaded_file is None:
        return None

    try:
        df = pd.read_csv(uploaded_file)
        
        # Define the standardized columns we need
        standard_cols = ['Date', 'Post Type', 'Reach', 'Impressions', 'Likes', 'Comments', 'Shares', 'Engagement']
        df_processed = pd.DataFrame()
        
        # --- Platform-Specific Column Mapping & Processing ---
        if platform_name == 'Facebook':
            column_mapping = {
                # Date/Time Column (using 'Publish time' as it's the most specific)
                'Publish time': 'Date',
                # Key Metrics
                'Reach': 'Reach',
                '3-second video views': 'Impressions', # Using 3s views as a proxy for Impressions count
                'Reactions': 'Likes',
                'Comments': 'Comments',
                'Shares': 'Shares',
                'Reactions, Comments and Shares': 'Engagement',
            }
            
            # 1. Map columns
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df_processed[new_col] = df[old_col]
            
            # 2. Add 'Post Type' (Assuming all are 'Video' based on the provided data)
            df_processed['Post Type'] = 'Video'
            
            # 3. Handle missing 'Impressions' (if 3-second views aren't present)
            if 'Impressions' not in df_processed.columns:
                 # Fallback, although '3-second video views' is usually present in this export
                df_processed['Impressions'] = df_processed['Reach'] 

        elif platform_name == 'Instagram':
            # Assuming a standard Instagram export (you'll need to update this if your IG file is different)
            column_mapping = {
                'Date': 'Date', 
                'Media Type': 'Post Type',
                'Reach': 'Reach',
                'Impressions': 'Impressions',
                'Likes': 'Likes',
                'Comments': 'Comments',
                'Shares': 'Shares',
            }
            
            # 1. Map columns (using heuristic logic from original script for IG)
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df_processed[new_col] = df[old_col]
        
        # --- Common Processing Steps ---
        
        # 4. Fill in any missing standard columns with a value of 0 (for calculations)
        for col in standard_cols:
            if col not in df_processed.columns:
                # Fill missing data columns with 0
                df_processed[col] = 0

        # 5. Date Conversion
        df_processed['Date'] = pd.to_datetime(df_processed['Date'], errors='coerce')
        df_processed = df_processed.dropna(subset=['Date']) 
        
        # 6. Calculate Derived Metrics (Engagement = sum of interactions if not provided directly)
        if df_processed['Engagement'].sum() == 0 and 'Likes' in df_processed.columns:
             # If 'Reactions, Comments and Shares' (Engagement) was missing or 0
             df_processed['Engagement'] = df_processed['Likes'] + df_processed['Comments'] + df_processed['Shares']
             # Ensure numeric types for summation
             df_processed['Engagement'] = pd.to_numeric(df_processed['Engagement'], errors='coerce').fillna(0)
             
        # 7. Add Platform Identifier
        df_processed['Platform'] = platform_name
        
        # 8. Clean Post Type (Standardize case and fill NaNs)
        df_processed['Post Type'] = df_processed['Post Type'].astype(str).fillna('Other').str.title()
        
        # Select only the finalized standard columns
        df_processed = df_processed[standard_cols + ['Platform']]
        
        return df_processed
    
    except Exception as e:
        st.error(f"Error processing {platform_name} data. Please check if it's a valid CSV file. Details: {e}")
        return None

# --- 2. LAYOUT AND FILE UPLOAD ---
st.title("Facebook & Instagram Performance Dashboard 📊")
st.markdown("Upload your Facebook and Instagram post data CSV files below for a consolidated view.")

# Sidebar for file uploads
st.sidebar.header("1. Upload Data Files")

# File Uploader for Facebook
fb_file = st.sidebar.file_uploader(
    "Upload Facebook Posts CSV (using 'Publish time' for Date)", 
    type=['csv'], 
    key='fb_uploader'
)

# File Uploader for Instagram
ig_file = st.sidebar.file_uploader(
    "Upload Instagram Posts CSV (must have 'Date', 'Reach', 'Impressions', 'Media Type' columns)", 
    type=['csv'], 
    key='ig_uploader'
)

# Process data
fb_df = load_and_process_data(fb_file, 'Facebook')
ig_df = load_and_process_data(ig_file, 'Instagram')

# --- 3. DATA COMBINATION AND MAIN DISPLAY ---

if fb_df is None and ig_df is None:
    st.info("Please upload at least one CSV file to start the analysis.")
else:
    # Combine dataframes
    all_data = pd.DataFrame()
    if fb_df is not None:
        all_data = pd.concat([all_data, fb_df], ignore_index=True)
    if ig_df is not None:
        all_data = pd.concat([all_data, ig_df], ignore_index=True)

    # Sidebar filter for date range
    st.sidebar.header("2. Date Range Filter")
    if not all_data.empty:
        # Calculate min/max date only from the available data
        min_date = all_data['Date'].min().date()
        max_date = all_data['Date'].max().date()
        
        # Add a check to ensure min_date is not NaT (Not a Time)
        if pd.isna(min_date):
            st.warning("Could not process date column. Check your CSV format.")
        else:
            date_range = st.sidebar.date_input(
                "Select date range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date = pd.to_datetime(date_range[0])
                end_date = pd.to_datetime(date_range[1])
                all_data = all_data[
                    (all_data['Date'] >= start_date) & 
                    (all_data['Date'] <= end_date)
                ]
    
    
    if all_data.empty:
        st.warning("No data available for the selected date range.")
    else:
        # --- 4. CORE METRICS (KPIs) ---
        st.header("1. Overview Metrics")
        
        # Ensure metrics are numeric before summing
        total_reach = all_data['Reach'].astype(float).sum()
        total_impressions = all_data['Impressions'].astype(float).sum()
        total_engagement = all_data['Engagement'].astype(float).sum()
        total_posts = all_data.shape[0]
        
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total Reach", f"{total_reach:,.0f}")
        col2.metric("Total Impressions", f"{total_impressions:,.0f}")
        col3.metric("Total Engagement", f"{total_engagement:,.0f}")
        col4.metric("Total Posts", f"{total_posts:,}")

        # --- 5. VISUALIZATIONS ---

        st.header("2. Trend Analysis (Engagement & Reach Over Time)")
        
        # Aggregate data by day
        daily_df = all_data.groupby(all_data['Date'].dt.date).agg({
            'Engagement': 'sum',
            'Reach': 'sum'
        }).reset_index()
        daily_df.rename(columns={'Date': 'Day'}, inplace=True)
        
        # Plot time series
        fig_trend = px.line(
            daily_df, 
            x='Day', 
            y=['Engagement', 'Reach'], 
            title='Daily Engagement and Reach Trends',
            template='plotly_white'
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # Engagement by Platform and Post Type
        st.header("3. Performance by Platform and Content Type")
        
        tab1, tab2 = st.tabs(["Content Type Performance", "Platform Comparison"])

        with tab1:
            # Group by Post Type
            type_df = all_data.groupby('Post Type').agg({
                'Engagement': 'sum',
                'Reach': 'sum',
                'Impressions': 'sum'
            }).reset_index().sort_values(by='Engagement', ascending=False)
            
            fig_type = px.bar(
                type_df, 
                x='Post Type', 
                y='Engagement', 
                color='Post Type', 
                title='Total Engagement by Content Type',
                template='plotly_white'
            )
            fig_type.update_layout(xaxis={'categoryorder':'total descending'})
            st.plotly_chart(fig_type, use_container_width=True)
            st.dataframe(type_df, use_container_width=True, hide_index=True)


        with tab2:
            # Group by Platform
            platform_df = all_data.groupby('Platform').agg({
                'Engagement': 'sum',
                'Reach': 'sum',
                'Impressions': 'sum',
                'Likes': 'sum',
                'Comments': 'sum',
                'Shares': 'sum',
                'Date': 'count' # Count posts
            }).rename(columns={'Date': 'Post Count'}).reset_index()
            
            # Melt for a cleaner comparison chart
            melted_df = platform_df.melt(
                id_vars='Platform', 
                value_vars=['Reach', 'Impressions', 'Engagement'],
                var_name='Metric', 
                value_name='Total Value'
            )
            
            fig_platform = px.bar(
                melted_df,
                x='Platform',
                y='Total Value',
                color='Metric',
                barmode='group',
                title='Total Key Metrics by Platform',
                template='plotly_white'
            )
            st.plotly_chart(fig_platform, use_container_width=True)
            st.dataframe(platform_df, use_container_width=True, hide_index=True)


# --- 6. INSTRUCTIONS / DATA EXPECTATION ---
st.sidebar.header("3. Data Expectation")
st.sidebar.markdown("""
**Facebook:**
* **Date:** Uses `"Publish time"` (e.g., `11/24/2025 11:00`).
* **Reach/Impressions:** Uses `"Reach"` and `"3-second video views"` (as a proxy for Impressions).
* **Engagement:** Uses `"Reactions"`, `"Comments"`, and `"Shares"`.
* **Post Type:** Defaulted to 'Video' for now.

**Instagram:**
* The Instagram file is assumed to follow a standard export with columns like `Date`, `Media Type`, `Reach`, `Impressions`, and interaction columns. If your Instagram file is different, please share its header row!
""")

st.sidebar.code("To run this app:\npip install streamlit pandas plotly\nstreamlit run social_dashboard.py")