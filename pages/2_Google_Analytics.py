import streamlit as st
import pandas as pd
import plotly.express as px
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
import glob
import socket
from datetime import datetime, timedelta

# Try to import Google Analytics client
try:
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
except ImportError:
    st.error("""
    ⚠️ **Missing Package**: `google-analytics-data` is not installed.
    
    Please install it by running:
    ```bash
    pip install google-analytics-data
    ```
    """)
    st.stop()

# Google Analytics API configuration
GA_SCOPES = ['https://www.googleapis.com/auth/analytics.readonly']

def format_number(num):
    """Format numbers with K, M suffixes"""
    try:
        num = float(num)
        if num >= 1000000:
            return f"{num/1000000:.1f}M"
        elif num >= 1000:
            return f"{num/1000:.1f}K"
        return str(int(num))
    except:
        return "0"

def find_credentials_file():
    """Find OAuth credentials file (credentials.json or client_secret_*.json)"""
    # First check for credentials.json
    if os.path.exists('credentials.json'):
        return 'credentials.json'
    
    # Look for client_secret_*.json files
    client_secret_files = glob.glob('client_secret_*.json')
    if client_secret_files:
        return client_secret_files[0]  # Use the first one found
    
    return None

def is_port_available(port):
    """Check if a port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False

def find_available_port(start_port=8080, max_attempts=10):
    """Find an available port starting from start_port"""
    for i in range(max_attempts):
        port = start_port + i
        if is_port_available(port):
            return port
    return None

@st.cache_data
def load_ga_credentials():
    """Load or create Google Analytics API credentials"""
    creds = None
    token_file = 'token_ga.pickle'
    
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            creds_file = find_credentials_file()
            if creds_file:
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_file, GA_SCOPES)
                # Try port 8080 first (must match redirect URI in Google Cloud Console)
                # If port 8080 is in use, find an available port
                port = 8080
                if not is_port_available(port):
                    st.warning(f"Port {port} is already in use. Trying to find an available port...")
                    available_port = find_available_port(8080)
                    if available_port:
                        port = available_port
                        st.info(f"Using port {port} instead. Make sure to add `http://localhost:{port}/` to authorized redirect URIs in Google Cloud Console.")
                    else:
                        st.error("Could not find an available port. Please close other applications using ports 8080-8090.")
                        return None
                creds = flow.run_local_server(port=port, open_browser=True)
            else:
                return None
        
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def get_ga_client():
    """Get Google Analytics Data API client"""
    creds = load_ga_credentials()
    if creds:
        try:
            # Create client with OAuth credentials
            # The BetaAnalyticsDataClient accepts credentials parameter
            client = BetaAnalyticsDataClient(credentials=creds)
            return client
        except Exception as e:
            st.warning(f"Error creating GA client: {str(e)}")
            st.info("Make sure google-analytics-data package is installed: pip install google-analytics-data")
            return None
    return None

def list_properties(client):
    """List available GA4 properties"""
    try:
        # Note: This requires Admin API access. For now, we'll use property ID directly
        # You can get property ID from GA4 admin panel
        return []
    except Exception as e:
        st.warning(f"Could not list properties: {str(e)}")
        return []

def get_ga_report(client, property_id, start_date, end_date, metrics, dimensions=None):
    """Get report from Google Analytics Data API"""
    try:
        from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric
        
        request = RunReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[Metric(name=m) for m in metrics],
            dimensions=[Dimension(name=d) for d in (dimensions or [])]
        )
        
        response = client.run_report(request=request)
        return response
    except Exception as e:
        st.error(f"Error fetching GA data: {str(e)}")
        return None

def format_ga_response(response):
    """Convert GA API response to DataFrame"""
    if not response:
        return None
    
    # Extract dimension and metric headers
    dimension_headers = [h.name for h in response.dimension_headers]
    metric_headers = [h.name for h in response.metric_headers]
    all_headers = dimension_headers + metric_headers
    
    # Extract rows
    rows = []
    for row in response.rows:
        values = [d.value for d in row.dimension_values] + [m.value for m in row.metric_values]
        rows.append(values)
    
    df = pd.DataFrame(rows, columns=all_headers)
    
    # Convert metric columns to numeric
    for header in metric_headers:
        df[header] = pd.to_numeric(df[header], errors='coerce')
    
    return df

st.title("📊 Google Analytics Dashboard")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("Account: codeforgoodberkeley@gmail.com")
    
    st.warning("⚠️ Google Analytics requires OAuth authentication")
    st.info("""
    **Setup Instructions:**
    1. Go to [Google Cloud Console](https://console.cloud.google.com/)
    2. Enable **Google Analytics Data API**
    3. Create OAuth 2.0 credentials (Desktop app type)
    4. **IMPORTANT**: Add redirect URI in Google Cloud Console:
       - Go to Credentials → Your OAuth 2.0 Client ID
       - Under "Authorized redirect URIs", add BOTH:
         * `http://localhost:8080/` (with trailing slash)
         * `http://localhost:8080` (without trailing slash)
       - OR use: `http://localhost` (without port)
    5. Download credentials file
    6. Get your GA4 Property ID from Analytics admin panel
    """)
    
    # Get GA client
    ga_client = get_ga_client()
    
    if ga_client:
        st.success("✅ Authenticated via OAuth")
    else:
        st.warning("⚠️ Please authenticate")
        st.info("Place `credentials.json` in the project directory and refresh.")
        st.stop()
    
    st.divider()
    st.subheader("📋 Property Settings")
    
    property_id = st.text_input(
        "GA4 Property ID", 
        help="Find this in GA4 Admin → Property Settings (format: 123456789)",
        value=st.session_state.get('ga_property_id', '')
    )
    
    if property_id:
        st.session_state['ga_property_id'] = property_id
        st.success(f"✅ Using Property ID: {property_id}")
    else:
        st.error("⚠️ Please enter a Property ID")
        st.info("""
        **How to find Property ID:**
        1. Go to [Google Analytics](https://analytics.google.com/)
        2. Click Admin (gear icon)
        3. Select your property
        4. Go to Property Settings
        5. Copy the Property ID (numeric, e.g., 123456789)
        """)
        st.stop()
    
    st.divider()
    st.subheader("📅 Date Range")
    col1, col2 = st.columns(2)
    with col1:
        end_date = st.date_input("End Date", datetime.now().date())
    with col2:
        days_back = st.selectbox("Days Back", [7, 14, 30, 60, 90, 365], index=2)
    start_date = end_date - timedelta(days=days_back)
    st.caption(f"Analyzing: {start_date} to {end_date}")

if not ga_client or not property_id:
    st.error("Please authenticate and provide a Property ID.")
    st.stop()

try:
    # Overview metrics
    st.markdown("---")
    st.subheader("📈 Overview Metrics")
    
    with st.spinner("Fetching overview data..."):
        overview_response = get_ga_report(
            ga_client,
            property_id,
            start_date.strftime('%Y-%m-%d'),
            end_date.strftime('%Y-%m-%d'),
            metrics=['activeUsers', 'screenPageViews', 'sessions', 'averageSessionDuration'],
            dimensions=['date']
        )
    
    if overview_response:
        df_overview = format_ga_response(overview_response)
        
        if df_overview is not None and not df_overview.empty:
            # Calculate totals
            col1, col2, col3, col4 = st.columns(4)
            
            if 'activeUsers' in df_overview.columns:
                total_users = df_overview['activeUsers'].sum()
                with col1:
                    st.metric("Total Users", format_number(total_users))
            
            if 'screenPageViews' in df_overview.columns:
                total_views = df_overview['screenPageViews'].sum()
                with col2:
                    st.metric("Total Page Views", format_number(total_views))
            
            if 'sessions' in df_overview.columns:
                total_sessions = df_overview['sessions'].sum()
                with col3:
                    st.metric("Total Sessions", format_number(total_sessions))
            
            if 'averageSessionDuration' in df_overview.columns:
                avg_duration = df_overview['averageSessionDuration'].mean()
                minutes = avg_duration / 60
                with col4:
                    st.metric("Avg Session Duration", f"{minutes:.1f} min")
            
            # Charts
            st.markdown("---")
            st.subheader("📊 Trends Over Time")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if 'date' in df_overview.columns and 'activeUsers' in df_overview.columns:
                    df_overview['date'] = pd.to_datetime(df_overview['date'])
                    fig = px.line(df_overview, x='date', y='activeUsers', 
                                title='Daily Active Users', markers=True)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if 'date' in df_overview.columns and 'screenPageViews' in df_overview.columns:
                    df_overview['date'] = pd.to_datetime(df_overview['date'])
                    fig = px.line(df_overview, x='date', y='screenPageViews', 
                                title='Daily Page Views', markers=True)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            
            # Top pages
            st.markdown("---")
            st.subheader("🔝 Top Pages")
            
            with st.spinner("Fetching top pages..."):
                pages_response = get_ga_report(
                    ga_client,
                    property_id,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    metrics=['screenPageViews', 'activeUsers'],
                    dimensions=['pagePath']
                )
            
            if pages_response:
                df_pages = format_ga_response(pages_response)
                if df_pages is not None and not df_pages.empty:
                    df_pages = df_pages.nlargest(10, 'screenPageViews')
                    df_pages['pagePath'] = df_pages['pagePath'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
                    
                    fig = px.bar(df_pages, x='screenPageViews', y='pagePath', 
                               orientation='h', title='Top 10 Pages by Views')
                    fig.update_layout(height=500, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Display table
                    st.dataframe(df_pages, use_container_width=True)
            
            # Traffic sources
            st.markdown("---")
            st.subheader("🌐 Traffic Sources")
            
            with st.spinner("Fetching traffic sources..."):
                sources_response = get_ga_report(
                    ga_client,
                    property_id,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    metrics=['sessions', 'activeUsers'],
                    dimensions=['sessionSource']
                )
            
            if sources_response:
                df_sources = format_ga_response(sources_response)
                if df_sources is not None and not df_sources.empty:
                    df_sources = df_sources.nlargest(10, 'sessions')
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        fig = px.pie(df_sources, values='sessions', names='sessionSource', 
                                   title='Sessions by Source')
                        fig.update_layout(height=400)
                        st.plotly_chart(fig, use_container_width=True)
                    with col2:
                        fig = px.bar(df_sources, x='sessions', y='sessionSource', 
                                   orientation='h', title='Top Traffic Sources')
                        fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                        st.plotly_chart(fig, use_container_width=True)
            
            # Download data
            st.markdown("---")
            csv = df_overview.to_csv(index=False)
            st.download_button(
                label="📥 Download Overview Data as CSV",
                data=csv,
                file_name=f"ga_analytics_{property_id}_{start_date}_{end_date}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No data available for the selected date range.")
    else:
        st.error("Could not fetch analytics data. Please check your Property ID and permissions.")
        st.info("""
        **Troubleshooting:**
        1. Verify Property ID is correct
        2. Ensure you have Viewer or higher permissions
        3. Check that the property has data for the selected date range
        """)

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)
    st.info("""
    **Common Issues:**
    - Property ID format: Should be numeric only (e.g., 123456789)
    - Permissions: Need at least Viewer role in Google Analytics
    - API: Make sure Google Analytics Data API is enabled in Cloud Console
    """)

