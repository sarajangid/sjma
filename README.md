# YouTube Analytics Dashboard 📊

A beautiful Streamlit application to fetch and analyze YouTube channel data using the YouTube Data API v3.

## Features

- 📈 Channel statistics (subscribers, views, video count)
- 🎥 Video analytics with views, likes, and comments
- 📊 Interactive charts and visualizations
- 🔍 Search and filter videos
- 📥 Export data as CSV
- 🎨 Modern, clean UI

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: If you get "command not found: streamlit", make sure you've installed the dependencies above. You may also need to use `python -m streamlit run app.py` instead.

### 2. YouTube API Setup

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

### 3. Run the App

```bash
streamlit run app.py
```

The app will open in your default web browser.

## Usage

1. **Authenticate**: Enter your API key in the sidebar OR place `credentials.json` for OAuth
2. **Select Channel**: Enter a channel ID (or leave empty to use your authenticated channel)
3. **Configure**: Adjust the number of videos to fetch
4. **Explore**: View statistics, charts, and video details
5. **Export**: Download data as CSV if needed

## Account

This app is configured for: **codeforgoodberkeley@gmail.com**

## Notes

- The app uses caching to improve performance
- OAuth tokens are stored in `token.pickle` (automatically created)
- Make sure to add `token.pickle` to `.gitignore` if committing to version control

