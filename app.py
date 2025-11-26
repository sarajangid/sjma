import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
from datetime import datetime, timedelta

# YouTube API configuration
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/yt-analytics.readonly'
]
YOUTUBE_DATA_API = 'youtube'
YOUTUBE_ANALYTICS_API = 'youtubeAnalytics'
API_VERSION = 'v3'

# Page configuration
st.set_page_config(
    page_title="YouTube Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #FF0000;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #FF0000;
    }
    .stMetric {
        background-color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def load_credentials():
    """Load or create YouTube API credentials"""
    creds = None
    token_file = 'token.pickle'
    
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                return None
        
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def get_youtube_services():
    """Build and return YouTube API services (Data and Analytics)"""
    creds = load_credentials()
    if creds:
        youtube_data = build(YOUTUBE_DATA_API, API_VERSION, credentials=creds)
        youtube_analytics = build(YOUTUBE_ANALYTICS_API, 'v2', credentials=creds)
        return youtube_data, youtube_analytics
    return None, None

def get_channel_info(youtube, channel_id=None, use_oauth=False):
    """Get channel information"""
    try:
        if channel_id:
            request = youtube.channels().list(
                part='snippet,statistics,contentDetails',
                id=channel_id
            )
        elif use_oauth:
            # Only use mine=True if we have OAuth credentials
            request = youtube.channels().list(
                part='snippet,statistics,contentDetails',
                mine=True
            )
        else:
            # API key without channel_id - can't proceed
            return []
        response = request.execute()
        return response.get('items', [])
    except Exception as e:
        st.error(f"Error fetching channel info: {str(e)}")
        return []

def get_channel_videos(youtube, channel_id, max_results=50):
    """Get videos from a channel"""
    try:
        # First, get the uploads playlist ID
        channels_response = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()
        
        uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get videos from the uploads playlist
        videos = []
        next_page_token = None
        
        while len(videos) < max_results:
            playlist_response = youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=uploads_playlist_id,
                maxResults=min(50, max_results - len(videos)),
                pageToken=next_page_token
            ).execute()
            
            videos.extend(playlist_response.get('items', []))
            next_page_token = playlist_response.get('nextPageToken')
            
            if not next_page_token:
                break
        
        # Get detailed statistics for each video
        video_ids = [video['contentDetails']['videoId'] for video in videos]
        video_details = []
        
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            videos_response = youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(batch)
            ).execute()
            video_details.extend(videos_response.get('items', []))
        
        return video_details
    except Exception as e:
        st.error(f"Error fetching videos: {str(e)}")
        return []

def get_analytics_data(youtube_analytics, channel_id, start_date, end_date, metrics='views,estimatedMinutesWatched,subscribersGained,likes,comments', dimensions='day'):
    """Get analytics data from YouTube Analytics API"""
    try:
        response = youtube_analytics.reports().query(
            ids=f'channel=={channel_id}',
            startDate=start_date,
            endDate=end_date,
            metrics=metrics,
            dimensions=dimensions
        ).execute()
        return response
    except Exception as e:
        st.warning(f"Analytics API error (may need channel owner access): {str(e)}")
        return None

def get_video_analytics(youtube_analytics, channel_id, video_id, start_date, end_date):
    """Get analytics for a specific video"""
    try:
        response = youtube_analytics.reports().query(
            ids=f'channel=={channel_id}',
            filters=f'video=={video_id}',
            startDate=start_date,
            endDate=end_date,
            metrics='views,estimatedMinutesWatched,likes,comments,shares,subscribersGained'
        ).execute()
        return response
    except Exception as e:
        return None

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

def format_duration(minutes):
    """Format minutes to hours and minutes"""
    try:
        hours = int(minutes // 60)
        mins = int(minutes % 60)
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    except:
        return "0m"

def main():
    st.markdown('<p class="main-header">📊 YouTube Analytics Dashboard</p>', unsafe_allow_html=True)
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        st.info("Account: codeforgoodberkeley@gmail.com")
        
        # API Key option (alternative to OAuth) - Note: Analytics API requires OAuth
        api_key = st.text_input("YouTube Data API Key (optional)", type="password", 
                               help="For basic data only. Analytics requires OAuth.")
        
        use_oauth = False
        if api_key:
            youtube_data = build(YOUTUBE_DATA_API, API_VERSION, developerKey=api_key)
            youtube_analytics = None
            use_oauth = False
            st.success("✅ Using API Key (Data API only)")
            st.warning("⚠️ Analytics API requires OAuth authentication")
            st.info("💡 **Note**: With API key, you must provide a Channel ID below")
        else:
            youtube_data, youtube_analytics = get_youtube_services()
            if youtube_data:
                use_oauth = True
                if youtube_analytics:
                    st.success("✅ Authenticated via OAuth (Full access)")
                else:
                    st.success("✅ Authenticated (Data API only)")
                    st.warning("⚠️ Analytics API may require additional permissions")
            else:
                st.warning("⚠️ Please authenticate")
                st.info("""
                **Setup Instructions:**
                1. Go to [Google Cloud Console](https://console.cloud.google.com/)
                2. Create a project and enable:
                   - YouTube Data API v3
                   - YouTube Analytics API
                3. Create OAuth 2.0 credentials (Desktop app)
                4. Download as `credentials.json`
                5. Place `credentials.json` in this directory
                """)
                return
        
        st.divider()
        if use_oauth:
            channel_id_input = st.text_input("Channel ID (leave empty for your channel)", 
                                            help="Enter a YouTube channel ID to analyze, or leave empty to use your authenticated channel")
        else:
            channel_id_input = st.text_input("Channel ID (required)", 
                                            help="Enter a YouTube channel ID to analyze (required when using API key)",
                                            value="")
            if not channel_id_input:
                st.error("⚠️ Channel ID is required when using API key authentication")
        max_videos = st.slider("Max Videos to Fetch", 10, 200, 50)
        
        # Date range for analytics
        st.divider()
        st.subheader("📅 Analytics Date Range")
        col1, col2 = st.columns(2)
        with col1:
            end_date = st.date_input("End Date", datetime.now().date())
        with col2:
            days_back = st.selectbox("Days Back", [7, 14, 30, 60, 90, 365], index=2)
        start_date = end_date - timedelta(days=days_back)
        st.caption(f"Analyzing: {start_date} to {end_date}")
    
    if not youtube_data:
        st.error("Please authenticate or provide an API key to continue.")
        return
    
    # Main content
    try:
        # Get channel information
        # Check if we need channel_id (required for API key, optional for OAuth)
        if not use_oauth and not channel_id_input:
            st.error("⚠️ Please provide a Channel ID when using API key authentication.")
            st.info("""
            💡 **How to find a Channel ID:**
            1. Go to the YouTube channel's page
            2. Click "About" tab
            3. Scroll down - the Channel ID is shown there (starts with "UC...")
            4. Or use a channel username/handle (e.g., @channelname) - we can look it up
            """)
            # Try to help user find channel ID
            username_input = st.text_input("Or enter channel username/handle (e.g., @channelname or channelname)", 
                                          help="We'll try to find the channel ID for you")
            if username_input:
                # Remove @ if present
                username = username_input.replace('@', '').strip()
                try:
                    # Try to get channel by username
                    search_response = youtube_data.search().list(
                        q=username,
                        type='channel',
                        part='snippet',
                        maxResults=1
                    ).execute()
                    if search_response.get('items'):
                        found_channel_id = search_response['items'][0]['id']['channelId']
                        st.success(f"✅ Found channel ID: `{found_channel_id}`")
                        st.info(f"Copy this ID and paste it in the Channel ID field above")
                except Exception as e:
                    st.warning(f"Could not find channel: {str(e)}")
            return
        
        channels = get_channel_info(youtube_data, channel_id=channel_id_input if channel_id_input else None, use_oauth=use_oauth)
        
        if not channels:
            if not channel_id_input and not use_oauth:
                st.error("No channel found. Please provide a Channel ID when using API key.")
            else:
                st.error("No channel found. Please check your channel ID or authentication.")
            return
        
        channel = channels[0]
        channel_id = channel['id']
        channel_title = channel['snippet']['title']
        channel_description = channel['snippet'].get('description', 'No description')
        stats = channel.get('statistics', {})
        
        # Display channel header
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(channel['snippet']['thumbnails']['high']['url'], width=200)
            st.markdown(f"### {channel_title}")
            st.caption(channel_description[:200] + "..." if len(channel_description) > 200 else channel_description)
        
        # Key metrics
        st.markdown("---")
        st.subheader("📈 Channel Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Subscribers", format_number(stats.get('subscriberCount', 0)))
        with col2:
            st.metric("Total Videos", format_number(stats.get('videoCount', 0)))
        with col3:
            st.metric("Total Views", format_number(stats.get('viewCount', 0)))
        with col4:
            avg_views = int(stats.get('viewCount', 0)) / max(int(stats.get('videoCount', 1)), 1)
            st.metric("Avg Views/Video", format_number(int(avg_views)))
        
        # Analytics API data (if available)
        if youtube_analytics:
            st.markdown("---")
            st.subheader("📊 Advanced Analytics")
            
            with st.spinner("Fetching analytics data..."):
                analytics_data = get_analytics_data(
                    youtube_analytics, 
                    channel_id,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d'),
                    metrics='views,estimatedMinutesWatched,subscribersGained,likes,comments,shares',
                    dimensions='day'
                )
            
            if analytics_data and 'rows' in analytics_data:
                # Process analytics data - extract column names from headers
                column_names = [h['name'] for h in analytics_data['columnHeaders']]
                df_analytics = pd.DataFrame(
                    analytics_data['rows'],
                    columns=column_names
                )
                
                # Rename columns for better display
                column_mapping = {}
                for col in column_names:
                    if col == 'day':
                        column_mapping[col] = 'Date'
                    else:
                        column_mapping[col] = col.replace('_', ' ').title()
                df_analytics = df_analytics.rename(columns=column_mapping)
                
                # Calculate totals
                col1, col2, col3, col4, col5 = st.columns(5)
                if 'Views' in df_analytics.columns:
                    total_views = df_analytics['Views'].sum()
                    with col1:
                        st.metric("Period Views", format_number(total_views))
                
                # Check for watch time column (could be various formats)
                watch_col = None
                for col in df_analytics.columns:
                    if 'watch' in col.lower() or 'minute' in col.lower():
                        watch_col = col
                        break
                
                if watch_col:
                    total_watch_time = df_analytics[watch_col].sum()
                    with col2:
                        st.metric("Watch Time", format_duration(total_watch_time))
                
                # Check for subscribers column
                subs_col = None
                for col in df_analytics.columns:
                    if 'subscriber' in col.lower():
                        subs_col = col
                        break
                
                if subs_col:
                    total_subs = df_analytics[subs_col].sum()
                    with col3:
                        st.metric("Subscribers Gained", format_number(total_subs))
                
                if 'Likes' in df_analytics.columns:
                    total_likes = df_analytics['Likes'].sum()
                    with col4:
                        st.metric("Likes", format_number(total_likes))
                
                if 'Comments' in df_analytics.columns:
                    total_comments = df_analytics['Comments'].sum()
                    with col5:
                        st.metric("Comments", format_number(total_comments))
                
                # Analytics charts
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'Date' in df_analytics.columns and 'Views' in df_analytics.columns:
                        df_analytics['Date'] = pd.to_datetime(df_analytics['Date'])
                        fig_views = px.line(df_analytics, x='Date', y='Views',
                                          title='Daily Views Over Time',
                                          markers=True)
                        fig_views.update_layout(height=400)
                        st.plotly_chart(fig_views, use_container_width=True)
                
                with col2:
                    if 'Date' in df_analytics.columns and watch_col:
                        df_analytics['Date'] = pd.to_datetime(df_analytics['Date'])
                        fig_watch = px.line(df_analytics, x='Date', y=watch_col,
                                          title='Daily Watch Time (Minutes)',
                                          markers=True)
                        fig_watch.update_layout(height=400)
                        st.plotly_chart(fig_watch, use_container_width=True)
                
                # Download analytics data
                csv_analytics = df_analytics.to_csv(index=False)
                st.download_button(
                    label="📥 Download Analytics Data as CSV",
                    data=csv_analytics,
                    file_name=f"youtube_analytics_{channel_id}_{start_date}_{end_date}.csv",
                    mime="text/csv"
                )
            else:
                st.info("Analytics data not available. Make sure you're authenticated as the channel owner.")
        
        # Fetch and display videos
        st.markdown("---")
        st.subheader("🎥 Recent Videos")
        
        with st.spinner("Fetching video data..."):
            videos = get_channel_videos(youtube_data, channel_id, max_results=max_videos)
        
        if videos:
            # Prepare video data for display
            video_data = []
            for video in videos:
                snippet = video['snippet']
                statistics = video.get('statistics', {})
                video_data.append({
                    'Title': snippet['title'],
                    'Published': snippet['publishedAt'][:10],
                    'Views': int(statistics.get('viewCount', 0)),
                    'Likes': int(statistics.get('likeCount', 0)),
                    'Comments': int(statistics.get('commentCount', 0)),
                    'Video ID': video['id'],
                    'Thumbnail': snippet['thumbnails']['medium']['url'],
                    'Description': snippet.get('description', '')[:100] + "..."
                })
            
            df = pd.DataFrame(video_data)
            
            # Display video statistics
            col1, col2 = st.columns(2)
            
            with col1:
                # Views over time
                df_sorted = df.sort_values('Published')
                fig_views = px.line(df_sorted, x='Published', y='Views', 
                                   title='Video Views Over Time',
                                   markers=True)
                fig_views.update_layout(height=400)
                st.plotly_chart(fig_views, use_container_width=True)
            
            with col2:
                # Top videos by views
                df_top = df.nlargest(10, 'Views')
                # Truncate long titles for display
                df_top['Title_Short'] = df_top['Title'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
                fig_top = px.bar(df_top, x='Views', y='Title_Short', 
                               orientation='h',
                               title='Top 10 Videos by Views')
                fig_top.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
                st.plotly_chart(fig_top, use_container_width=True)
            
            # Video table with thumbnails
            st.markdown("### Video Details")
            
            # Search/filter
            search_term = st.text_input("🔍 Search videos", "")
            if search_term:
                df_filtered = df[df['Title'].str.contains(search_term, case=False, na=False)]
            else:
                df_filtered = df
            
            # Display videos in a nice grid
            for idx, row in df_filtered.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.image(row['Thumbnail'], use_container_width=True)
                    with col2:
                        st.markdown(f"### [{row['Title']}](https://www.youtube.com/watch?v={row['Video ID']})")
                        st.caption(f"Published: {row['Published']}")
                        col_views, col_likes, col_comments = st.columns(3)
                        with col_views:
                            st.metric("Views", format_number(row['Views']))
                        with col_likes:
                            st.metric("Likes", format_number(row['Likes']))
                        with col_comments:
                            st.metric("Comments", format_number(row['Comments']))
                        
                        # Show video analytics if available
                        if youtube_analytics:
                            video_analytics = get_video_analytics(
                                youtube_analytics,
                                channel_id,
                                row['Video ID'],
                                start_date.strftime('%Y-%m-%d'),
                                end_date.strftime('%Y-%m-%d')
                            )
                            if video_analytics and 'rows' in video_analytics and len(video_analytics['rows']) > 0:
                                row_data = video_analytics['rows'][0]
                                headers = [h['name'] for h in video_analytics['columnHeaders']]
                                analytics_dict = dict(zip(headers, row_data))
                                
                                if 'estimatedMinutesWatched' in analytics_dict:
                                    watch_time = analytics_dict['estimatedMinutesWatched']
                                    st.caption(f"📺 Watch Time (period): {format_duration(watch_time)}")
                    st.divider()
            
            # Download data option
            st.markdown("---")
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download Video Data as CSV",
                data=csv,
                file_name=f"youtube_analytics_{channel_id}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No videos found for this channel.")
    
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.exception(e)

if __name__ == "__main__":
    main()

