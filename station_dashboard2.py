import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import folium_static
import os

# --- Constants for Filenames ---
LOCATION_FILE = "Location.xlsx"
DATA_FILE = "Data.xlsx"

# Page configuration
st.set_page_config(
    page_title="IWFM/Compass Monitoring",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="collapsed" # Sidebar hidden by default in this design
)

# --- CUSTOM CSS FOR NEW LAYOUT ---
st.markdown("""
<style>
    /* General App styling to reduce padding */
    .block-container {
        padding-top: 0rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    
    /* --- CUSTOM HEADER BAR STYLING --- */
    . custom-header-bar {
        background-color: #2c3e50; /* Dark Blue */
        color: white;
        padding: 10px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-left: -1rem;
        margin-right: -1rem;
        margin-top: -4rem; /* Pull bar to top over streamlit header space */
        margin-bottom: 1rem;
        font-family: sans-serif;
    }
    .header-left {
        font-size: 1.2rem;
        font-weight: bold;
        display: flex;
        align-items: center;
    }
    .header-center {
        display: flex;
        align-items: center;
        font-size: 0.9rem;
    }
    .header-right {
        display: flex;
        align-items: center;
        text-align: right;
        font-size: 0.9rem;
    }
    .user-info {
        margin-left: 10px;
        line-height: 1.2;
    }
    .user-name { font-weight: bold; }
    .user-role { font-size: 0.8rem; opacity: 0.8; }
    .header-icon { margin-right: 8px; font-size: 1.2rem;}

    /* --- MAIN TITLE --- */
    .main-title-custom {
        color: #009688; /* Teal/Green from image */
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }

    /* --- LEFT COLUMN STYLES --- */
    .list-header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #009688;
        margin-bottom: 10px;
    }
    .list-title {
        font-size: 1.5rem;
        font-weight: bold;
    }
    .list-icons {
        font-size: 1.2rem;
        cursor: pointer;
    }
    .list-subheaders {
        display: flex;
        justify-content: space-between;
        color: #7f8c8d;
        font-size: 0.9rem;
        padding-bottom: 5px;
        border-bottom: 1px solid #eee;
        margin-bottom: 10px;
    }
    .no-entities {
        text-align: center;
        color: #009688;
        font-size: 1.8rem;
        font-weight: bold;
        margin-top: 100px;
    }

    /* --- STATION LIST BUTTONS (Redesigning streamlit buttons) --- */
    /* Target buttons inside the left column specifically */
    [data-testid="column"]:nth-of-type(1) .stButton button {
        width: 100%;
        text-align: left;
        border: none;
        border-bottom: 1px solid #f0f0f0;
        background-color: transparent;
        color: #2c3e50;
        padding: 10px 5px;
        border-radius: 0;
        display: flex;
        justify-content: space-between;
    }
    [data-testid="column"]:nth-of-type(1) .stButton button:hover {
        background-color: #f9f9f9;
        color: #009688;
        border-color: #009688;
    }
    [data-testid="column"]:nth-of-type(1) .stButton button p {
        font-size: 1rem;
        font-weight: 500;
    }

    /* --- RIGHT COLUMN CONTAINER --- */
    .map-container-style {
        border: 1px solid #ddd;
        padding: 5px;
        background-color: white;
        height: 600px;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNCTIONS (Kept mostly the same) ---

@st.cache_data
def load_location_data(filepath):
    try:
        df = pd.read_excel(filepath)
        return df
    except Exception:
        return None

@st.cache_data
def load_data_file(filepath):
    try:
        xlsx = pd.ExcelFile(filepath)
        all_data = {}
        for sheet_name in xlsx.sheet_names:
            all_data[sheet_name] = pd.read_excel(xlsx, sheet_name=sheet_name)
        return all_data
    except Exception:
        return None

def get_station_icon(station_type):
    if pd.notna(station_type) and 'groundwater' in str(station_type).lower():
        return "📍"
    return "📌"

def create_map(stations_df):
    if stations_df is None or len(stations_df) == 0:
        # Return a default map if no data, matching image background color roughly
        m = folium.Map(location=[23.8, 90.4], zoom_start=7, tiles='cartodbpositron')
        return m
    
    center_lat = stations_df['Lat'].mean()
    center_lon = stations_df['Lon'].mean()
    m = folium.Map(location=[center_lat, center_lon], zoom_start=10, tiles='cartodbpositron')
    
    for _, row in stations_df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            popup_html = f"<b>{row.get('Station Name ', 'Unknown')}</b><br>Status: {row.get('Status', 'N/A')}"
            folium.Marker(
                location=[row['Lat'], row['Lon']],
                popup=folium.Popup(popup_html, max_width=200),
                tooltip=row.get('Station Name ', 'Unknown'),
                icon=folium.Icon(color='blue' if 'groundwater' in str(row.get('Type', '')).lower() else 'red')
            ).add_to(m)
    return m

def filter_data_by_days(df, days):
    if df is None or len(df) == 0 or 'Date' not in df.columns: return df
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    if len(df) == 0: return df
    latest_date = df['Date'].max()
    cutoff_date = latest_date - timedelta(days=days)
    return df[df['Date'] >= cutoff_date]

def create_time_series_chart(data, station_name, days):
    if data is None or len(data) == 0: return None
    numeric_cols = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
    if len(numeric_cols) == 0: return None
    
    fig = go.Figure()
    colors = ['#009688', '#f39c12', '#2ecc71', '#9b59b6']
    for idx, col in enumerate(numeric_cols):
        fig.add_trace(go.Scatter(
            x=data['Date'], y=data[col], mode='lines+markers', name=col,
            line=dict(color=colors[idx % len(colors)], width=2), marker=dict(size=4)
        ))
    
    fig.update_layout(
        title=f"Last {days} Days Data", xaxis_title="Date", yaxis_title="Value",
        hovermode='x unified', height=400, template='plotly_white',
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# --- MAIN APP ---
def main():
    # 1. INJECT CUSTOM HEADER HTML
    st.markdown("""
        <div class="custom-header-bar">
            <div class="header-left">
                <span style="margin-right: 10px;">🏛️</span> Home
            </div>
            <div class="header-center">
                <span class="header-icon">🕒</span> History - last 90 days 1 second
            </div>
            <div class="header-right">
                 <span class="header-icon">👤</span>
                 <div class="user-info">
                    <div class="user-name">Sara Nowreen</div>
                    <div class="user-role">Customer</div>
                 </div>
                 <span style="margin-left: 15px; cursor: pointer;">⋮</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. MAIN TITLE
    st.markdown('<div class="main-title-custom">Monitoring Stations, IWFM/ Compass</div>', unsafe_allow_html=True)

    # 3. LOAD DATA
    if 'stations_data' not in st.session_state: st.session_state.stations_data = None
    if 'data_df' not in st.session_state: st.session_state.data_df = None
    if 'selected_station' not in st.session_state: st.session_state.selected_station = None

    data_loaded = False
    if os.path.exists(LOCATION_FILE) and os.path.exists(DATA_FILE):
        if st.session_state.stations_data is None:
            st.session_state.stations_data = load_location_data(LOCATION_FILE)
            st.session_state.data_df = load_data_file(DATA_FILE)
        
        if st.session_state.stations_data is not None and len(st.session_state.stations_data) > 0:
            data_loaded = True

    # 4. TWO-COLUMN LAYOUT
    # Adjust ratios to match image (left col is narrower)
    left_col, right_col = st.columns([4, 8], gap="large")

    # --- LEFT COLUMN: STATION LIST ---
    with left_col:
        # Header area matching image
        st.markdown("""
            <div class="list-header-container">
                <div class="list-title">Station list</div>
                <div class="list-icons">🔍 ⛶</div>
            </div>
            <div class="list-subheaders">
                <span>Station Name ↑</span>
                <span>Device Location</span>
            </div>
        """, unsafe_allow_html=True)

        if data_loaded:
            # Display list of stations as clickable buttons styled like list items
            # Using a container with fixed height for scrolling if many stations
            with st.container(height=550, border=False):
                for idx, station in st.session_state.stations_data.iterrows():
                    s_name = station.get('Station Name ', 'Unknown')
                    # Create a button that acts as a list item select
                    if st.button(f"📍 {s_name}", key=f"btn_{idx}", use_container_width=True):
                        st.session_state.selected_station = station
                        st.rerun()
        else:
            # Show the "No entities found" message if no data exist
            st.markdown('<div class="no-entities">No entities found</div>', unsafe_allow_html=True)

    # --- RIGHT COLUMN: MAP OR DETAILS ---
    with right_col:
        # Add a subtle container style around right column content
        st.markdown('<div class="map-container-style">', unsafe_allow_html=True)
        
        if st.session_state.selected_station is None:
            # SHOW MAP VIEW (Default state matching image)
            map_data = st.session_state.stations_data if data_loaded else None
            station_map = create_map(map_data)
            folium_static(station_map, width="100%", height=590)
            
        else:
            # SHOW DETAILS VIEW (If a station is clicked in left column)
            station = st.session_state.selected_station
            
            # Header with Back Button
            c1, c2 = st.columns([1, 5])
            with c1:
                 if st.button("← Back", use_container_width=True):
                    st.session_state.selected_station = None
                    st.rerun()
            with c2:
                 st.subheader(f"📊 {station.get('Station Name ', 'Unknown')}")

            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("ID", station.get('Station ID', 'N/A'))
            m2.metric("Type", station.get('Type', 'N/A'))
            m3.metric("Status", station.get('Status', 'N/A'))
            st.markdown("---")

            # Chart Controls
            days = st.selectbox("Time Range", options=[30, 90, 365], index=1)

            # Chart Rendering
            if st.session_state.data_df:
                station_id = str(station.get('Station ID', '')).lower()
                matching_sheet = next((sheet for sheet in st.session_state.data_df.keys() if station_id in str(sheet).lower()), None)
                
                if matching_sheet:
                    data = st.session_state.data_df[matching_sheet].copy()
                    filtered_data = filter_data_by_days(data, days)
                    if len(filtered_data) > 0:
                        fig = create_time_series_chart(filtered_data, station.get('Station Name '), days)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info(f"No data in last {days} days.")
                else:
                    st.warning("No data sheet found for this station.")

        st.markdown('</div>', unsafe_allow_html=True) # End map-container-style

if __name__ == "__main__":
    main()
