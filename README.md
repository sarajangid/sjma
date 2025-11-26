# Analytics Dashboard 📊

A comprehensive multi-page Streamlit application for analyzing YouTube and Google Analytics data.

## Features

### 📺 YouTube Analytics
- 📈 Channel statistics (subscribers, views, video count)
- 🎥 Video analytics with views, likes, and comments
- 📊 Advanced analytics with watch time and engagement metrics
- 🔍 Search and filter videos
- 📥 Export data as CSV
- 🎨 Interactive charts and visualizations

### 📊 Google Analytics
- 👥 User and session analytics
- 📄 Page views and top pages analysis
- 🌐 Traffic source breakdown
- ⏱️ Session duration and engagement metrics
- 📈 Time-series trends and visualizations
- 📥 Export data as CSV

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If you get "command not found: streamlit", make sure you've installed the dependencies above. You may also need to use `python -m streamlit run app.py` instead.

### 2. API Setup

#### YouTube API Setup

You have two authentication options:

#### Option A: API Key (Basic Data Only)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable the **YouTube Data API v3**
4. Go to "Credentials" → "Create Credentials" → "API Key"
5. Copy your API key
6. Use it in the app's sidebar when running
7. **Note**: API Key only provides basic channel/video data. For advanced analytics, use OAuth.

#### Option B: OAuth 2.0 (Full Features - Recommended)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **BOTH**:
   - **YouTube Data API v3**
   - **YouTube Analytics API** ⭐ (Required for advanced analytics)
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
5. Choose "Desktop app" as application type
6. Download the credentials file and save it as `credentials.json` in this directory
7. The app will handle OAuth flow automatically on first run
8. **Important**: You must authenticate with the channel owner account to access Analytics API data

#### Google Analytics API Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **Google Analytics Data API**
4. Go to "Credentials" → "Create Credentials" → "OAuth client ID"
5. Choose "Desktop app" as application type
6. Download the credentials file and save it as `credentials.json` in this directory
7. **Important**: You need at least **Viewer** role in Google Analytics for the property you want to analyze
8. Get your GA4 Property ID from Google Analytics Admin → Property Settings

### 3. Run the App

```bash
python3 -m streamlit run app.py
```

Or:
```bash
streamlit run app.py
```

The app will open in your default web browser with a multi-page navigation in the sidebar.

## Usage

### YouTube Analytics Page
1. **Authenticate**: Enter your API key in the sidebar OR place `credentials.json` for OAuth
2. **Select Channel**: Enter a channel ID (or leave empty to use your authenticated channel)
3. **Configure**: Adjust the number of videos to fetch and date range
4. **Explore**: View statistics, charts, and video details
5. **Export**: Download data as CSV if needed

### Google Analytics Page
1. **Authenticate**: Place `credentials.json` for OAuth (required)
2. **Enter Property ID**: Get this from GA4 Admin → Property Settings (numeric ID)
3. **Select Date Range**: Choose your analysis period
4. **Explore**: View traffic, user behavior, and page performance
5. **Export**: Download data as CSV if needed

## Account

This app is configured for: **codeforgoodberkeley@gmail.com**

## Required Permissions

### Google Analytics
- **Minimum**: Viewer role in Google Analytics
- **API**: Google Analytics Data API must be enabled
- **Authentication**: OAuth 2.0 required (API key not supported)

### YouTube
- **Data API**: API key or OAuth (API key for basic data, OAuth for full access)
- **Analytics API**: OAuth required, must be channel owner
- **APIs**: YouTube Data API v3 and YouTube Analytics API

## Notes

- The app uses caching to improve performance
- OAuth tokens are stored separately:
  - `token_youtube.pickle` for YouTube
  - `token_ga.pickle` for Google Analytics
- Make sure credentials and token files are in `.gitignore`
- Multi-page navigation is automatically available via Streamlit's pages feature

