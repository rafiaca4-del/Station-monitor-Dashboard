import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import folium_static
import os
import numpy as np 

# --- FILE CONFIGURATION ---
LOCATION_FILE = "station information.xlsx" # UPDATED FILE NAME
DATA_FILE = "Data.xlsx"
# --- END FILE CONFIGURATION ---

st.set_page_config(
    page_title="Station Monitoring Dashboard",
    page_icon="🌊",
    layout="wide",
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .station-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 10px;
        border-radius: 8px;
        margin-bottom: 8px;
        border-left: 4px solid #3498db;
        cursor: pointer;
    }
    .station-card:hover {
        transform: translateX(5px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }
    .status-badge-active {
        background-color: #4caf50;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
    }
    .status-badge-dead {
        background-color: #9D2C3E;
        color: white;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.75em;
        font-weight: bold;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.2rem;
    }
    
    /* Global Streamlit UI Cleanup */
    .stApp > header {
        display: none; 
    }
    div.block-container {
        padding-top: 2.5rem; 
        padding-bottom: 0rem;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    h1 {
        text-align: center; /* Center the title */
        margin-top: 0rem !important;
        padding-top: 0rem !important;
        padding-bottom: 1rem; 
    }
    div[data-testid="stMetric"] {
        text-align: center; 
    }

    /* KEY CHANGES FOR GAP REDUCTION */
    h3 {
        margin-top: 0.5rem !important; 
        margin-bottom: 0.5rem !important;
    }
    h2 {
        margin-top: 0.5rem !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Make the station list scrollable in the 1/3 columns */
    .station-list-container {
        max-height: 80vh; 
        overflow-y: auto;
        padding-right: 10px;
        padding-left: 5px; 
    }
    /* Reduce internal spacing within the list columns */
    div[data-testid="stVerticalBlock"] {
        gap: 0.5rem; 
    }
    
    /* Center the Station List Title */
    .list-title-container {
        text-align: center;
        width: 100%;
        margin-top: 0.5rem; 
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_station' not in st.session_state:
    st.session_state.selected_station = None
if 'stations_data' not in st.session_state:
    st.session_state.stations_data = None
if 'data_df' not in st.session_state:
    st.session_state.data_df = None

@st.cache_data
def load_location_data(filepath):
    """Load location/station data from local Excel file path"""
    try:
        df = pd.read_excel(filepath)
        df.columns = df.columns.str.strip()
        
        # 📌 UPDATED REQUIRED COLUMNS
        required_cols = ['Station Name', 'Adress', 'Lat', 'Lon', 'Status', 'Type', 'Starting date', 'Last updated']
        
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns in {filepath}: {', '.join(missing_cols)}")
            return None

        return df[required_cols]
        
    except Exception as e:
        st.error(f"Error loading location data from {filepath}: {e}")
        return None

@st.cache_data
def load_data_file(filepath):
    """Load all sheets from data Excel file path (kept for consistency)"""
    try:
        xlsx = pd.ExcelFile(filepath)
        all_data = {}
        for sheet_name in xlsx.sheet_names:
            all_data[sheet_name] = pd.read_excel(xlsx, sheet_name=sheet_name)
        return all_data
    except Exception as e:
        return None

def get_station_icon(status):
    """Return emoji icon based on status"""
    if pd.notna(status) and 'active' in str(status).lower():
        return "🟢"
    return "🔴"

def create_map(stations_df):
    """Create a folium map with station markers, using only available data"""
    if stations_df is None or len(stations_df) == 0:
        return None
    
    center_lat = stations_df['Lat'].mean()
    center_lon = stations_df['Lon'].mean()
    
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7, 
        tiles='OpenStreetMap'
    )
    
    for idx, row in stations_df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            status = row.get('Status', 'Unknown')
            icon_color = 'green' if status.lower() == 'active' else 'red'
            
            # Note: Using 'Adress' here, matching the new column name
            popup_html = f"""
            <div style="font-family: Arial; width: 200px;">
                <h4>{row.get('Station Name', 'Unknown')}</h4>
                <b>Adress:</b> {row.get('Adress', 'N/A')}<br>
                <b>Status:</b> {status}<br>
            </div>
            """
            
            folium.Marker(
                location=[row['Lat'], row['Lon']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=row.get('Station Name', 'Unknown'),
                icon=folium.Icon(color=icon_color)
            ).add_to(m)
    
    return m

def render_list_column(df_slice, column):
    """Renders a slice of the station list into a given Streamlit column."""
    with column:
        st.markdown("<div class='station-list-container'>", unsafe_allow_html=True)
        for idx, station in df_slice.iterrows():
            station_name = station.get('Station Name', 'Unknown')
            adress = station.get('Adress', 'N/A')
            status = station.get('Status', 'Unknown')
            icon = get_station_icon(status)
            
            if st.button(
                f"{icon} {station_name}",
                key=f"station_{idx}",
                use_container_width=True
            ):
                st.session_state.selected_station = station
                st.rerun() 
            
            st.caption(f"Adress: {adress}")
            
            if status.lower() == 'active':
                st.markdown('<span class="status-badge-active">Active</span>', unsafe_allow_html=True)
            elif status.lower() == 'dead':
                st.markdown('<span class="status-badge-dead">Dead</span>', unsafe_allow_html=True)
            
            st.markdown("---")
            
        st.markdown("</div>", unsafe_allow_html=True)


# Main App
def main():
    
    # 📌 MOVED/CENTERED TITLE
    st.title("🌊 Observation Station Monitor")

    # --- AUTOMATIC DATA LOADING START ---
    if st.session_state.stations_data is None or st.session_state.data_df is None:
        if os.path.exists(LOCATION_FILE) and os.path.exists(DATA_FILE):
            with st.spinner(f"Reading data from repository ({LOCATION_FILE} & {DATA_FILE})..."):
                st.session_state.stations_data = load_location_data(LOCATION_FILE)
                st.session_state.data_df = load_data_file(DATA_FILE) 
            
            if st.session_state.stations_data is None or st.session_state.data_df is None:
                st.error("Failed to read required data files or missing columns. Check console for details.")
                st.stop()
        else:
            st.error(f"""
            ⚠️ Data files not found!
            Please ensure required Excel files are uploaded:
            1. `{LOCATION_FILE}` (Must contain: Station Name, Adress, Lat, Lon, Status, Type, Starting date, Last updated)
            2. `{DATA_FILE}` (Data content)
            """)
            st.stop()
    # --- AUTOMATIC DATA LOADING END ---
    
    stations_df = st.session_state.stations_data
    
    # -------------------------------------------------------------
    # 📌 STEP 1: Main 50/50 split for Header Alignment
    # -------------------------------------------------------------
    col_map_header_spacer, col_list_header = st.columns([3, 3]) # 50% / 50%
    
    # Render the Station List Header
    with col_list_header:
         st.markdown('<div class="list-title-container"><h2>🏢 Station List</h2></div>', unsafe_allow_html=True)


    # -------------------------------------------------------------
    # 📌 STEP 2: Main 50/16.67/16.67/16.67 content split
    # -------------------------------------------------------------
    col_main_content, col_list_1, col_list_2, col_list_3 = st.columns([3, 1, 1, 1]) 


    # --- 50% COLUMNS: Split Station List Content ---
    if stations_df is not None:
        
        # Calculate the split points
        total_stations = len(stations_df)
        split_point_1 = total_stations // 3
        split_point_2 = 2 * (total_stations // 3)
        
        # Split the DataFrame into three parts
        df_part_1 = stations_df.iloc[:split_point_1]
        df_part_2 = stations_df.iloc[split_point_1:split_point_2]
        df_part_3 = stations_df.iloc[split_point_2:]

        # Render the three parts in their respective columns
        render_list_column(df_part_1, col_list_1)
        render_list_column(df_part_2, col_list_2)
        render_list_column(df_part_3, col_list_3)


    # --- 50% COLUMN: Map or Details ---
    with col_main_content:
        
        if st.session_state.selected_station is None:            
            # --- INITIAL VIEW (Map and Metrics) ---
            
            # Metrics (Adjusted to fit the 50% column)
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Total Stations", len(stations_df) if stations_df is not None else 0)
            with col_m2:
                active_count = 0
                if stations_df is not None and 'Status' in stations_df.columns:
                    active_count = len(stations_df[stations_df['Status'].astype(str).str.lower() == 'active'])
                st.metric("Active Stations", active_count)
            with col_m3:
                st.metric("Dashboard Date", datetime.now().strftime("%Y-%m-%d"))
            
            st.markdown("---")
            
            # Map Header
            st.markdown("<h3 style='text-align: center;'>📍 Station Locations</h3>", unsafe_allow_html=True)
            
            # Map Rendering
            station_map = create_map(stations_df)
            if station_map:
                folium_static(station_map, width=None, height=600)
        
        else:
            # --- DETAIL VIEW (Station Info) ---
            station = st.session_state.selected_station
            
            # Back button
            if st.button("← Back to Map View"):
                st.session_state.selected_station = None
                st.rerun() 
            
            st.header(f"📊 {station.get('Station Name', 'Unknown Station')}")
            
            # 📌 UPDATED METRICS LAYOUT (4 Columns for 8 Metrics)
            col_d1, col_d2, col_d3, col_d4 = st.columns(4)
            
            # Row 1 (Name, Adress, Lat, Starting date)
            with col_d1:
                st.metric("Station Name", station.get('Station Name', 'N/A'))
            with col_d2:
                st.metric("Adress", station.get('Adress', 'N/A'))
            with col_d3:
                st.metric("Latitude", f"{station.get('Lat', 'N/A'):.4f}" if pd.notna(station.get('Lat')) else 'N/A')
            with col_d4:
                st.metric("Starting Date", station.get('Starting date', 'N/A'))

            # Horizontal separator (using markdown)
            st.markdown("---")

            # Row 2 (Type, Status, Lon, Last updated)
            col_d5, col_d6, col_d7, col_d8 = st.columns(4)
            with col_d5:
                st.metric("Type", station.get('Type', 'N/A'))
            with col_d6:
                st.metric("Status", station.get('Status', 'N/A'))
            with col_d7:
                st.metric("Longitude", f"{station.get('Lon', 'N/A'):.4f}" if pd.notna(station.get('Lon')) else 'N/A')
            with col_d8:
                st.metric("Last Updated", station.get('Last updated', 'N/A'))
            
            st.markdown("---")
            
            st.info("Data visualization and raw table views are currently hidden per request.")

if __name__ == "__main__":
    main()

