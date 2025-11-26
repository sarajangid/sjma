import streamlit as st
import pandas as pd
import plotly.express as px
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import pickle
from datetime import datetime, timedelta

# YouTube API configuration
YOUTUBE_SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/yt-analytics.readonly'
]
YOUTUBE_DATA_API = 'youtube'
YOUTUBE_ANALYTICS_API = 'youtubeAnalytics'
API_VERSION = 'v3'

@st.cache_data
def load_youtube_credentials():
    """Load or create YouTube API credentials"""
    creds = None
    token_file = 'token_youtube.pickle'
    
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if os.path.exists('credentials.json'):
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', YOUTUBE_SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                return None
        
        with open(token_file, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

def get_youtube_services():
    """Build and return YouTube API services (Data and Analytics)"""
    creds = load_youtube_credentials()
    if creds:
        youtube_data = build(YOUTUBE_DATA_API, API_VERSION, credentials=creds)
        youtube_analytics = build(YOUTUBE_ANALYTICS_API, 'v2', credentials=creds)
        return youtube_data, youtube_analytics
    return None, None

def get_channel_id_from_handle(youtube, handle):
    """Get channel ID from handle (e.g., @channelname or channelname)"""
    try:
        # Remove @ if present
        handle = handle.replace('@', '').strip()
        
        # Try to get channel by custom URL/handle
        # First, try searching for the channel
        search_response = youtube.search().list(
            q=handle,
            type='channel',
            part='snippet',
            maxResults=5
        ).execute()
        
        # Look for exact match in channel title or custom URL
        for item in search_response.get('items', []):
            channel_id = item['id']['channelId']
            # Get full channel details to check custom URL
            channel_details = youtube.channels().list(
                part='snippet,id',
                id=channel_id
            ).execute()
            
            if channel_details.get('items'):
                channel = channel_details['items'][0]
                snippet = channel['snippet']
                # Check if handle matches custom URL or title
                custom_url = snippet.get('customUrl', '').lower().replace('@', '')
                title = snippet.get('title', '').lower()
                handle_lower = handle.lower()
                
                if handle_lower in custom_url or handle_lower in title:
                    return channel_id
        
        # If no exact match, return first result
        if search_response.get('items'):
            return search_response['items'][0]['id']['channelId']
        
        return None
    except Exception as e:
        st.warning(f"Could not find channel from handle: {str(e)}")
        return None

def get_channel_info(youtube, channel_id=None, use_oauth=False):
    """Get channel information"""
    try:
        if channel_id:
            request = youtube.channels().list(
                part='snippet,statistics,contentDetails',
                id=channel_id
            )
        elif use_oauth:
            request = youtube.channels().list(
                part='snippet,statistics,contentDetails',
                mine=True
            )
        else:
            return []
        response = request.execute()
        return response.get('items', [])
    except Exception as e:
        st.error(f"Error fetching channel info: {str(e)}")
        return []

def get_channel_videos(youtube, channel_id, max_results=50):
    """Get videos from a channel"""
    try:
        channels_response = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        ).execute()
        
        uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
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
        st.warning(f"Analytics API error: {str(e)}")
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

st.title("📺 YouTube Analytics")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("Account: codeforgoodberkeley@gmail.com")
    
    api_key = st.text_input("YouTube Data API Key (optional)", type="password", 
                           help="For basic data only. Analytics requires OAuth.")
    
    use_oauth = False
    if api_key:
        youtube_data = build(YOUTUBE_DATA_API, API_VERSION, developerKey=api_key)
        youtube_analytics = None
        use_oauth = False
        st.success("✅ Using API Key (Data API only)")
        st.warning("⚠️ Analytics API requires OAuth")
    else:
        youtube_data, youtube_analytics = get_youtube_services()
        if youtube_data:
            use_oauth = True
            if youtube_analytics:
                st.success("✅ Authenticated via OAuth (Full access)")
            else:
                st.success("✅ Authenticated (Data API only)")
        else:
            st.warning("⚠️ Please authenticate")
            st.info("""
            **Setup:**
            1. Enable YouTube Data API v3
            2. Enable YouTube Analytics API
            3. Create OAuth 2.0 credentials
            4. Download as `credentials.json`
            """)
            st.stop()
    
    st.divider()
    if use_oauth:
        channel_input = st.text_input("Channel Handle or ID (optional)", 
                                     help="Enter @channelname or channel ID. Leave empty to use your authenticated channel",
                                     placeholder="@channelname or UC...")
    else:
        channel_input = st.text_input("Channel Handle or ID (required)", 
                                     help="Enter @channelname or channel ID (e.g., @channelname or UC...)",
                                     value="",
                                     placeholder="@channelname or UC...")
    max_videos = st.slider("Max Videos to Fetch", 10, 200, 50)
    
    st.divider()
    st.subheader("📅 Date Range")
    col1, col2 = st.columns(2)
    with col1:
        end_date = st.date_input("End Date", datetime.now().date())
    with col2:
        days_back = st.selectbox("Days Back", [7, 14, 30, 60, 90, 365], index=2)
    start_date = end_date - timedelta(days=days_back)

if not youtube_data:
    st.error("Please authenticate or provide an API key.")
    st.stop()

try:
    # Process channel input - convert handle to ID if needed
    channel_id_input = None
    if channel_input:
        # Check if it looks like a channel ID (starts with UC) or is a handle
        if channel_input.startswith('UC') and len(channel_input) == 24:
            # Looks like a channel ID
            channel_id_input = channel_input
        else:
            # Treat as handle, try to get channel ID
            with st.spinner("Looking up channel ID..."):
                channel_id_input = get_channel_id_from_handle(youtube_data, channel_input)
            if channel_id_input:
                st.success(f"✅ Found channel ID: {channel_id_input}")
            else:
                st.error(f"⚠️ Could not find channel for: {channel_input}")
                st.info("Please try a different handle or use a channel ID directly (starts with UC...)")
                st.stop()
    
    if not use_oauth and not channel_id_input:
        st.error("⚠️ Please provide a Channel Handle or ID when using API key.")
        st.info("💡 Enter a channel handle (e.g., @channelname) or channel ID (e.g., UC...)")
        st.stop()
    
    channels = get_channel_info(youtube_data, channel_id=channel_id_input if channel_id_input else None, use_oauth=use_oauth)
    
    if not channels:
        st.error("No channel found. Please check your Channel ID or authentication.")
        st.stop()
    
    channel = channels[0]
    channel_id = channel['id']
    channel_title = channel['snippet']['title']
    stats = channel.get('statistics', {})
    
    # Display channel header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(channel['snippet']['thumbnails']['high']['url'], width=200)
        st.markdown(f"### {channel_title}")
    
    # Key metrics
    st.markdown("---")
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
    
    # Analytics API data
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
            column_names = [h['name'] for h in analytics_data['columnHeaders']]
            df_analytics = pd.DataFrame(analytics_data['rows'], columns=column_names)
            
            column_mapping = {}
            for col in column_names:
                if col == 'day':
                    column_mapping[col] = 'Date'
                else:
                    column_mapping[col] = col.replace('_', ' ').title()
            df_analytics = df_analytics.rename(columns=column_mapping)
            
            col1, col2, col3, col4, col5 = st.columns(5)
            if 'Views' in df_analytics.columns:
                with col1:
                    st.metric("Period Views", format_number(df_analytics['Views'].sum()))
            
            watch_col = next((col for col in df_analytics.columns if 'watch' in col.lower() or 'minute' in col.lower()), None)
            if watch_col:
                with col2:
                    st.metric("Watch Time", format_duration(df_analytics[watch_col].sum()))
            
            subs_col = next((col for col in df_analytics.columns if 'subscriber' in col.lower()), None)
            if subs_col:
                with col3:
                    st.metric("Subscribers Gained", format_number(df_analytics[subs_col].sum()))
            
            if 'Likes' in df_analytics.columns:
                with col4:
                    st.metric("Likes", format_number(df_analytics['Likes'].sum()))
            if 'Comments' in df_analytics.columns:
                with col5:
                    st.metric("Comments", format_number(df_analytics['Comments'].sum()))
            
            col1, col2 = st.columns(2)
            with col1:
                if 'Date' in df_analytics.columns and 'Views' in df_analytics.columns:
                    df_analytics['Date'] = pd.to_datetime(df_analytics['Date'])
                    fig = px.line(df_analytics, x='Date', y='Views', title='Daily Views', markers=True)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
            with col2:
                if 'Date' in df_analytics.columns and watch_col:
                    df_analytics['Date'] = pd.to_datetime(df_analytics['Date'])
                    fig = px.line(df_analytics, x='Date', y=watch_col, title='Daily Watch Time', markers=True)
                    fig.update_layout(height=400)
                    st.plotly_chart(fig, use_container_width=True)
    
    # Videos
    st.markdown("---")
    st.subheader("🎥 Recent Videos")
    
    with st.spinner("Fetching videos..."):
        videos = get_channel_videos(youtube_data, channel_id, max_results=max_videos)
    
    if videos:
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
            })
        
        df = pd.DataFrame(video_data)
        
        col1, col2 = st.columns(2)
        with col1:
            df_sorted = df.sort_values('Published')
            fig = px.line(df_sorted, x='Published', y='Views', title='Video Views Over Time', markers=True)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            df_top = df.nlargest(10, 'Views')
            df_top['Title_Short'] = df_top['Title'].apply(lambda x: x[:50] + '...' if len(x) > 50 else x)
            fig = px.bar(df_top, x='Views', y='Title_Short', orientation='h', title='Top 10 Videos')
            fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        
        search_term = st.text_input("🔍 Search videos", "")
        df_filtered = df[df['Title'].str.contains(search_term, case=False, na=False)] if search_term else df
        
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
                st.divider()
        
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Video Data as CSV",
            data=csv,
            file_name=f"youtube_analytics_{channel_id}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No videos found.")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    st.exception(e)

