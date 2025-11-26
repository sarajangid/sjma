import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Analytics Dashboard",
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
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #FF0000, #4285F4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">📊 Analytics Dashboard</p>', unsafe_allow_html=True)

st.markdown("""
## Welcome to the Analytics Dashboard! 🎉

This multi-page dashboard provides comprehensive analytics for:

### 📺 YouTube Analytics
- Channel statistics and metrics
- Video performance analytics
- Advanced engagement metrics
- Watch time and subscriber growth

### 📊 Google Analytics
- Website traffic and user behavior
- Page views and session data
- Traffic sources analysis
- Top performing pages

---

**Navigate using the sidebar** to access different analytics pages.

**Account**: codeforgoodberkeley@gmail.com
""")

st.info("""
💡 **Getting Started:**
1. Use the sidebar to navigate to YouTube or Google Analytics
2. Authenticate with OAuth or use API keys where supported
3. Select your date ranges and explore the data!
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📺 YouTube Analytics
    - Channel performance metrics
    - Video analytics and insights
    - Engagement tracking
    - Watch time analysis
    
    **→ Use the sidebar navigation to access YouTube Analytics**
    """)

with col2:
    st.markdown("""
    ### 📊 Google Analytics
    - Website traffic analysis
    - User behavior insights
    - Traffic source breakdown
    - Page performance metrics
    
    **→ Use the sidebar navigation to access Google Analytics**
    """)

st.markdown("---")
st.markdown("""
### 📋 Required Permissions

**For Google Analytics:**
- **Viewer role** or higher in Google Analytics
- Google Analytics Data API enabled in Cloud Console
- OAuth 2.0 authentication required

**For YouTube:**
- YouTube Data API v3 (API key or OAuth)
- YouTube Analytics API (OAuth only, requires channel owner access)
""")

