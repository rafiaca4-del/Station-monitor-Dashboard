import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import folium_static
import os
LOCATION_FILE = "Location.xlsx"
DATA_FILE = "Data.xlsx"

st.set_page_config(
    page_title="Station Monitoring Dashboard",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stSidebar {
        background-color: white;
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
    /* Style to help center the metric numbers */
    .stMetric {
        text-align: center; 
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
        return df
    except Exception as e:
        st.error(f"Error loading location data from {filepath}: {e}")
        return None

@st.cache_data
def load_data_file(filepath):
    """Load all sheets from data Excel file path"""
    try:
        xlsx = pd.ExcelFile(filepath)
        all_data = {}
        for sheet_name in xlsx.sheet_names:
            all_data[sheet_name] = pd.read_excel(xlsx, sheet_name=sheet_name)
        return all_data
    except Exception as e:
        st.error(f"Error loading data file from {filepath}: {e}")
        return None

def get_station_icon(station_type):
    """Return emoji icon based on station type"""
    if pd.notna(station_type) and 'groundwater' in str(station_type).lower():
        return "📍"
    return "📌"

def create_map(stations_df):
    """Create a folium map with station markers"""
    if stations_df is None or len(stations_df) == 0:
        return None
    
    # Calculate center of map
    center_lat = stations_df['Lat'].mean()
    center_lon = stations_df['Lon'].mean()
    
    # Create map with decreased zoom (zoomed out)
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7,  # ZOOM ADJUSTMENT: Zoomed out for better overview
        tiles='OpenStreetMap'
    )
    
    # Add markers
    for idx, row in stations_df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            icon = get_station_icon(row.get('Type', ''))
            
            popup_html = f"""
            <div style="font-family: Arial; width: 200px;">
                <h4>{row.get('Station Name ', 'Unknown')}</h4>
                <b>ID:</b> {row.get('Station ID', 'N/A')}<br>
                <b>Type:</b> {row.get('Type', 'N/A')}<br>
                <b>Status:</b> {row.get('Status', 'Unknown')}<br>
            </div>
            """
            
            folium.Marker(
                location=[row['Lat'], row['Lon']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=row.get('Station Name ', 'Unknown'),
                icon=folium.Icon(color='blue' if 'groundwater' in str(row.get('Type', '')).lower() else 'red')
            ).add_to(m)
    
    return m

# Main App
def main():
    st.title("🌊 Observation Station Monitor")

    # --- AUTOMATIC DATA LOADING START ---
    if st.session_state.stations_data is None or st.session_state.data_df is None:
        if os.path.exists(LOCATION_FILE) and os.path.exists(DATA_FILE):
            with st.spinner(f"Reading data from repository ({LOCATION_FILE} & {DATA_FILE})..."):
                st.session_state.stations_data = load_location_data(LOCATION_FILE)
                st.session_state.data_df = load_data_file(DATA_FILE) 
                
            if st.session_state.stations_data is None or st.session_state.data_df is None:
                st.error("Failed to read data files even though they exist.")
                st.stop()
        else:
            st.error(f"""
            ⚠️ Data files not found!
            Please ensure required Excel files are uploaded:
            1. `{LOCATION_FILE}`
            2. `{DATA_FILE}`
            """)
            st.stop()
    # --- AUTOMATIC DATA LOADING END ---

    
    # Sidebar - Station List Only
    with st.sidebar:
        if st.session_state.stations_data is not None:
            st.header("🏢 Station List")
            for idx, station in st.session_state.stations_data.iterrows():
                station_name = station.get('Station Name ', 'Unknown')
                station_type = station.get('Type', 'N/A')
                status = station.get('Status', 'Unknown')
                icon = get_station_icon(station_type)
                
                if st.button(
                    f"{icon} {station_name}",
                    key=f"station_{idx}",
                    use_container_width=True
                ):
                    st.session_state.selected_station = station
                
                st.caption(f"ID: {station.get('Station ID', 'N/A')} | Type: {station_type}")
                
                if status.lower() == 'active':
                    st.markdown('<span class="status-badge-active">Active</span>', unsafe_allow_html=True)
                elif status.lower() == 'dead':
                    st.markdown('<span class="status-badge-dead">Dead</span>', unsafe_allow_html=True)
                
                st.markdown("---")

    
    # Main Content Area
    if st.session_state.stations_data is not None:
        
        # Show map or detail view
        if st.session_state.selected_station is None:    
            # 📌 CHANGE 2: Center the metrics by using a wider column for centering (1 part left, 3 parts metrics, 1 part right)
            col_left_spacer, col_metrics, col_right_spacer = st.columns([1, 3, 1])
 col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Stations", len(st.session_state.stations_data))
            with col2:
                if 'Status' in st.session_state.stations_data.columns:
                    active_count = len(st.session_state.stations_data[
                        st.session_state.stations_data['Status'].astype(str).str.lower() == 'active'
                    ])
                    st.metric("Active Stations", active_count)
                else:
                    st.metric("Active Stations", "N/A")
            with col3:
                st.metric("Dashboard Date", datetime.now().strftime("%Y-%m-%d"))
            
            st.markdown("---")
            # 📌 CHANGE 1: Center the main header and make it smaller (using H3)
            st.markdown("<h3 style='text-align: center;'>📍 Station Locations</h3>", unsafe_allow_html=True)
            # 📌 CHANGE 3: Make the map full width
            # Create and display map - This is now full width as it's not restricted by columns
            station_map = create_map(st.session_state.stations_data)
            if station_map:
                # Setting width=None allows folium_static to expand to the full width of its container
                folium_static(station_map, width=None, height=600)
        
        else:
            # Detail View (No changes here, as per previous request to hide charts/data)
            station = st.session_state.selected_station
            
            if st.button("← Back to Map"):
                st.session_state.selected_station = None
                st.rerun()
            
            st.header(f"📊 {station.get('Station Name ', 'Unknown Station')}")
            
            # Station details
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                st.metric("Station ID", station.get('Station ID', 'N/A'))
            with col2:
                st.metric("Type", station.get('Type', 'N/A'))
            with col3:
                st.metric("Latitude", f"{station.get('Lat', 'N/A'):.4f}" if pd.notna(station.get('Lat')) else 'N/A')
            with col4:
                st.metric("Longitude", f"{station.get('Lon', 'N/A'):.4f}" if pd.notna(station.get('Lon')) else 'N/A')
            with col5:
                st.metric("Status", station.get('Status', 'N/A'))
            with col6:
                st.metric("Last Update", station.get('Last Update', 'N/A'))

            st.markdown("---")
            
            st.info("Data visualization and raw table views are currently hidden per request.")

if __name__ == "__main__":
    main()


