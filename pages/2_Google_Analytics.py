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
import time
import subprocess
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

def clear_ga_credentials():
    """Clear Google Analytics OAuth credentials"""
    token_file = 'token_ga.pickle'
    if os.path.exists(token_file):
        try:
            os.remove(token_file)
            return True
        except:
            return False
    return False

def kill_port(port):
    """Kill any process using the specified port"""
    try:
        # Find process using the port
        result = subprocess.run(
            ['lsof', '-ti', f':{port}'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                try:
                    subprocess.run(['kill', '-9', pid], check=False)
                except:
                    pass
            return True
    except:
        pass
    return False

def is_port_available(port):
    """Check if a port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return True
        except OSError:
            return False

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
                # Always use port 8080 - kill any process using it first
                port = 8080
                if not is_port_available(port):
                    st.info("Port 8080 is in use. Freeing it up...")
                    kill_port(port)
                    # Wait a moment for the port to be released
                    time.sleep(1)
                
                # Verify port is now available
                if not is_port_available(port):
                    st.error("Could not free up port 8080. Please manually close any applications using it.")
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
       - Under "Authorized redirect URIs", add: `http://localhost:8080/`
    5. **Add Test Users** (if app is in Testing mode):
       - Go to OAuth consent screen
       - Scroll to "Test users" section
       - Click "+ ADD USERS"
       - Add email addresses of users who need access
    6. Download credentials file
    7. Get your GA4 Property ID from Analytics admin panel
    """)
    with st.expander("🔐 **2FA / Authentication Issues?**", expanded=False):
        st.markdown("""
        **If you're having 2FA issues:**
        - 2FA should work with OAuth - complete the 2FA challenge when prompted
        - Make sure you're using the correct Google account
        - If the app is in "Testing" mode, you MUST add test users in OAuth consent screen
        - Test users must use the exact email address that has access to the Google Analytics property
        
        **To add test users:**
        1. Go to [Google Cloud Console](https://console.cloud.google.com/)
        2. Navigate to **APIs & Services** → **OAuth consent screen**
        3. Scroll down to **Test users** section
        4. Click **+ ADD USERS**
        5. Add the email addresses of people who need to use the app
        6. They must use the same email to authenticate
        
        **Important:** 
        - Test users must have at least **Viewer** role in Google Analytics for the property
        - The email used for OAuth must match the email that has access to the property
        - If the app is published, test users aren't needed, but the app must go through verification.
        """)
    
    # Logout button
    token_file = 'token_ga.pickle'
    if os.path.exists(token_file):
        st.divider()
        if st.button("🚪 Logout / Clear Credentials", use_container_width=True, type="secondary"):
            if clear_ga_credentials():
                st.success("✅ Credentials cleared! Please refresh the page.")
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("Failed to clear credentials")
        st.caption("Use this to sign in with a different account")
        st.divider()
    
    # Get GA client
    ga_client = get_ga_client()
    
    if ga_client:
        st.success("✅ Authenticated via OAuth")
        st.info("**OAuth Status:** Connected to Google Analytics Data API")
    else:
        st.warning("⚠️ Please authenticate")
        st.info("Place your `client_secret_*.json` or `credentials.json` file in the project directory and refresh.")
        st.info("""
        **Having authentication issues?**
        - Make sure you're added as a test user if the app is in Testing mode
        - Use the exact email address that has access to the Google Analytics property
        - Complete 2FA if prompted - it should work with OAuth
        """)
        st.stop()
    
    st.divider()
    st.subheader("📋 Property Settings")
    
    property_id = st.text_input(
        "GA4 Property ID", 
        help="Find this in GA4 Admin → Property Settings (format: 123456789)",
        value=st.session_state.get('ga_property_id', '313983920'),
        placeholder="Enter Property ID (e.g., 123456789)"
    )
    
    if property_id:
        # Validate property ID format (should be numeric)
        if property_id.isdigit():
            st.session_state['ga_property_id'] = property_id
            st.success(f"✅ Using Property ID: {property_id}")
        else:
            st.error("⚠️ Property ID must be numeric (e.g., 123456789)")
            st.stop()
    else:
        st.warning("⚠️ **Property ID Required**")
        st.info("""
        **How to find Property ID:**
        1. Go to [Google Analytics](https://analytics.google.com/)
        2. Click **Admin** (gear icon) in the bottom left
        3. Select your **property** from the dropdown
        4. Click **Property Settings**
        5. Copy the **Property ID** (numeric, e.g., 123456789)
        
        **Note:** You need at least **Viewer** role in Google Analytics to access data.
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
        st.warning("""
        **403 Forbidden Error - Insufficient Permissions**
        
        **Possible reasons:**
        1. ⚠️ You don't have Viewer (or higher) role for this property
        2. ⚠️ The Property ID is incorrect
        3. ⚠️ The authenticated account doesn't have access to this property
        
        **Solutions:**
        - Click "🚪 Logout / Clear Credentials" above to sign in with a different account
        - Make sure the account you sign in with has at least **Viewer** role in Google Analytics
        - Verify the Property ID is correct in GA4 Admin → Property Settings
        - Ask the property owner to grant you Viewer access
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

