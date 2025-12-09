import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import folium_static
import os

# --- FILE CONFIGURATION ---
LOCATION_FILE = "Location1.xlsx"
DATA_FILE = "Data.xlsx"
# --- END FILE CONFIGURATION ---

st.set_page_config(
    page_title="Station Monitoring Dashboard",
    page_icon="🌊",
    layout="wide",
    # Sidebar is no longer needed
)

# Custom CSS
st.markdown("""
<style>
    .main {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    .station-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1px;
        border-radius: 1px;
        margin-bottom: 1px;
        border-left: 1px solid #3498db;
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
        margin-top: 0rem !important;
        padding-top: 0rem !important;
    }
    div[data-testid="stMetric"] {
        text-align: center; 
    }

    /* **************************************************
    📌 KEY CHANGES FOR GAP REDUCTION (Station Locations & Station List)
    **************************************************
    */
    /* Target the map title (h3) and reduce top margin significantly */
    h3 {
        margin-top: 0.5rem !important; /* Reduced from 1rem to 0.5rem */
        margin-bottom: 0.5rem !important;
    }
    
    /* Target the Station List header (which is an h2 rendered by st.header) 
       and reduce its top margin dramatically. The div structure is complex, 
       but we can target the h2 style. */
    h2 {
        margin-top: 0.5rem !important; /* Reduce gap before Station List header */
        margin-bottom: 0.5rem !important;
    }

    /* Target the parent container of the list for tighter packing */
    div[data-testid="stVerticalBlock"] > div > div:nth-child(1) {
        gap: 0.5rem; /* Reduces default Streamlit block spacing */
    }

    /* Make the station list scrollable in the 40% column */
    .station-list-container {
        max-height: 80vh; 
        overflow-y: auto;
        padding-right: 15px;
        padding-left: 5px; 
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
        
        # Cleanup column names
        df.columns = df.columns.str.strip()
        
        # Required columns (Station Name, Adress, Lat, Lon, Status)
        required_cols = ['Station Name', 'Adress', 'Lat', 'Lon', 'Status']
        
        # Check if all required columns are present after cleanup
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns in {filepath}: {', '.join(missing_cols)}")
            return None

        # Return only the required columns
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
    
    # Calculate center of map
    center_lat = stations_df['Lat'].mean()
    center_lon = stations_df['Lon'].mean()
    
    # Create map with decreased zoom (zoomed out)
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=7, 
        tiles='OpenStreetMap'
    )
    
    # Add markers
    for idx, row in stations_df.iterrows():
        if pd.notna(row['Lat']) and pd.notna(row['Lon']):
            # Use status to determine marker color
            status = row.get('Status', 'Unknown')
            icon_color = 'green' if status.lower() == 'active' else 'red'
            
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

def render_station_list():
    """Renders the station list in the 40% column."""
    st.header("🏢 Station List") # Renders as <h2>, targeted by new CSS
    st.markdown("<div class='station-list-container'>", unsafe_allow_html=True)
    
    if st.session_state.stations_data is not None:
        for idx, station in st.session_state.stations_data.iterrows():
            station_name = station.get('Station Name', 'Unknown')
            adress = station.get('Adress', 'N/A')
            status = station.get('Status', 'Unknown')
            icon = get_station_icon(status)
            
            # Button uses Station Name
            if st.button(
                f"{icon} {station_name}",
                key=f"station_{idx}",
                use_container_width=True
            ):
                st.session_state.selected_station = station
                st.rerun() # Rerun to switch to detail view
            
            # Caption for Address
            st.caption(f"Adress: {adress}")
            
            # Status Badge
            if status.lower() == 'active':
                st.markdown('<span class="status-badge-active">Active</span>', unsafe_allow_html=True)
            elif status.lower() == 'dead':
                st.markdown('<span class="status-badge-dead">Dead</span>', unsafe_allow_html=True)
            
            st.markdown("---")
            
    st.markdown("</div>", unsafe_allow_html=True)


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
                st.error("Failed to read required data files or missing columns. Check console for details.")
                st.stop()
        else:
            st.error(f"""
            ⚠️ Data files not found!
            Please ensure required Excel files are uploaded:
            1. `{LOCATION_FILE}` (Must contain: Station Name, Adress, Lat, Lon, Status)
            2. `{DATA_FILE}` (Data content)
            """)
            st.stop()
    # --- AUTOMATIC DATA LOADING END ---

    # 📌 NEW LAYOUT: 60% Map/Details (Left) and 40% Station List (Right)
    col_main_content, col_station_list = st.columns([6, 4]) 

    # --- 40% COLUMN: Station List ---
    with col_station_list:
        render_station_list()
        
    # --- 60% COLUMN: Map or Details ---
    with col_main_content:
        
        if st.session_state.selected_station is None:            
            # --- INITIAL VIEW (Map and Metrics) ---
            
            # Metrics (Adjusted to fit the 60% column)
            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric("Total Stations", len(st.session_state.stations_data))
            with col_m2:
                if 'Status' in st.session_state.stations_data.columns:
                    active_count = len(st.session_state.stations_data[
                        st.session_state.stations_data['Status'].astype(str).str.lower() == 'active'
                    ])
                    st.metric("Active Stations", active_count)
                else:
                    st.metric("Active Stations", "N/A")
            with col_m3:
                st.metric("Dashboard Date", datetime.now().strftime("%Y-%m-%d"))
            
            st.markdown("---")
            
            # Map Header (h3, targeted by new CSS)
            st.markdown("<h3 style='text-align: center;'>📍 Station Locations</h3>", unsafe_allow_html=True)
            
            # Map Rendering
            station_map = create_map(st.session_state.stations_data)
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
            
            # Station details metrics (5 columns adjusted to fill 60% width)
            col_d1, col_d2, col_d3, col_d4, col_d5 = st.columns([2, 2, 1, 1, 1])
            
            with col_d1:
                st.metric("Station Name", station.get('Station Name', 'N/A'))
            with col_d2:
                st.metric("Adress", station.get('Adress', 'N/A'))
            with col_d3:
                st.metric("Latitude", f"{station.get('Lat', 'N/A'):.4f}" if pd.notna(station.get('Lat')) else 'N/A')
            with col_d4:
                st.metric("Longitude", f"{station.get('Lon', 'N/A'):.4f}" if pd.notna(station.get('Lon')) else 'N/A')
            with col_d5:
                st.metric("Status", station.get('Status', 'N/A'))

            st.markdown("---")
            
            st.info("Data visualization and raw table views are currently hidden per request.")

if __name__ == "__main__":
    main()


