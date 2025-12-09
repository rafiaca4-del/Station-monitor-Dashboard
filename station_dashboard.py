import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import folium_static
import os

# --- FILE CONFIGURATION ---
LOCATION_FILE = "Location1.xlsx"
DATA_FILE = "Data.xlsx" # Still referenced, but its data is not displayed per original request
# --- END FILE CONFIGURATION ---

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
    /* 📌 CSS CHANGE 1: Reduce top gap (above st.title) */
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

    /* 📌 CSS CHANGE 2: Reduce gap above h3 (Station Locations) and center metric values */
    h3 {
        margin-top: 1rem !important; /* Reduced space after the separator */
        margin-bottom: 0.5rem !important;
    }
    div[data-testid="stMetric"] {
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
        # Load the data
        df = pd.read_excel(filepath)
        
        # --- ENFORCING REQUIRED COLUMNS AND CLEANUP ---
        # Ensure only the required columns exist (case-insensitive column matching is complex, 
        # so we assume exact column names as stated in the prompt for simplicity).
        required_cols = ['Station Name', 'Adress', 'Lat', 'Lon', 'Status']
        
        # We need to handle the extra space in 'Station Name ' from the original code. 
        # For simplicity, we assume the user's requested column name ('Station Name') 
        # is the new standard, but we include a check just in case.
        
        # Try to clean up column names if they have trailing spaces (like in original code)
        df.columns = df.columns.str.strip()
        
        # Check if all required columns are present after cleanup
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns in {filepath}: {', '.join(missing_cols)}")
            return None

        # Return only the required columns
        return df[required_cols]
        # --- END ENFORCING REQUIRED COLUMNS AND CLEANUP ---
        
    except Exception as e:
        st.error(f"Error loading location data from {filepath}: {e}")
        return None

@st.cache_data
def load_data_file(filepath):
    """Load all sheets from data Excel file path (kept for consistency, but unused in detail view)"""
    try:
        xlsx = pd.ExcelFile(filepath)
        all_data = {}
        for sheet_name in xlsx.sheet_names:
            all_data[sheet_name] = pd.read_excel(xlsx, sheet_name=sheet_name)
        return all_data
    except Exception as e:
        # It's okay if this fails if the user hasn't provided it, but the main app relies on both files existing.
        return None

# Simplified icon function
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
                <b>Address:</b> {row.get('Adress', 'N/A')}<br>
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

# Main App
def main():
    st.title("🌊 Observation Station Monitor")

    # --- AUTOMATIC DATA LOADING START ---
    # Ensure both files are present and loaded
    if st.session_state.stations_data is None or st.session_state.data_df is None:
        if os.path.exists(LOCATION_FILE) and os.path.exists(DATA_FILE):
            with st.spinner(f"Reading data from repository ({LOCATION_FILE} & {DATA_FILE})..."):
                # Load location data
                st.session_state.stations_data = load_location_data(LOCATION_FILE)
                
                # Load data file (even if its contents are unused)
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

    
    # Sidebar - Station List Only
    with st.sidebar:
        if st.session_state.stations_data is not None:
            st.header("🏢 Station List")
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
                
                # Caption for Address
                st.caption(f"Adress: {adress}")
                
                # Status Badge
                if status.lower() == 'active':
                    st.markdown('<span class="status-badge-active">Active</span>', unsafe_allow_html=True)
                elif status.lower() == 'dead':
                    st.markdown('<span class="status-badge-dead">Dead</span>', unsafe_allow_html=True)
                
                st.markdown("---")

    
    # Main Content Area
    if st.session_state.stations_data is not None:
        
        # Show map or detail view
        if st.session_state.selected_station is None:            
            
            # 📌 METRICS: Centered Metrics Section using columns [1, 3, 1]
            col_left_spacer, col_metrics, col_right_spacer = st.columns([1, 3, 1])

            with col_metrics:
                # Metrics columns are nested inside the centered block
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
            
            # 📌 HEADER: Centered and smaller Header (using h3)
            st.markdown("<h3 style='text-align: center;'>📍 Station Locations</h3>", unsafe_allow_html=True)
            
            # 📌 MAP: Full Width Map (No surrounding columns needed)
            station_map = create_map(st.session_state.stations_data)
            if station_map:
                # Setting width=None allows folium_static to expand to the full width of its container
                folium_static(station_map, width=None, height=600)
        
        else:
            # Detail View 
            station = st.session_state.selected_station
            
            if st.button("← Back to Map"):
                st.session_state.selected_station = None
                st.rerun()
            
            st.header(f"📊 {station.get('Station Name', 'Unknown Station')}")
            
            # Station details metrics (now 5 columns)
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("Station Name", station.get('Station Name', 'N/A'))
            with col2:
                st.metric("Adress", station.get('Adress', 'N/A'))
            with col3:
                st.metric("Latitude", f"{station.get('Lat', 'N/A'):.4f}" if pd.notna(station.get('Lat')) else 'N/A')
            with col4:
                st.metric("Longitude", f"{station.get('Lon', 'N/A'):.4f}" if pd.notna(station.get('Lon')) else 'N/A')
            with col5:
                st.metric("Status", station.get('Status', 'N/A'))

            st.markdown("---")
            
            st.info("Data visualization and raw table views are currently hidden per request.")

if __name__ == "__main__":
    main()



