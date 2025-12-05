import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import folium
from streamlit_folium import folium_static

# Page configuration
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
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
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
def load_location_data(file):
    """Load location/station data from Excel file"""
    try:
        df = pd.read_excel(file)
        return df
    except Exception as e:
        st.error(f"Error loading location data: {e}")
        return None

@st.cache_data
def load_data_file(file):
    """Load all sheets from data Excel file"""
    try:
        xlsx = pd.ExcelFile(file)
        all_data = {}
        for sheet_name in xlsx.sheet_names:
            all_data[sheet_name] = pd.read_excel(xlsx, sheet_name=sheet_name)
        return all_data
    except Exception as e:
        st.error(f"Error loading data file: {e}")
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
    
    # Create map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
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

def filter_data_by_days(df, days):
    """Filter dataframe to last N days"""
    if df is None or len(df) == 0:
        return df
    
    if 'Date' not in df.columns:
        return df
    
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    df = df.dropna(subset=['Date'])
    
    if len(df) == 0:
        return df
    
    cutoff_date = datetime.now() - timedelta(days=days)
    return df[df['Date'] >= cutoff_date]

def create_time_series_chart(data, station_name, days):
    """Create interactive time series chart"""
    if data is None or len(data) == 0:
        return None
    
    # Get numeric columns (excluding Date)
    numeric_cols = data.select_dtypes(include=['float64', 'int64']).columns.tolist()
    
    if len(numeric_cols) == 0:
        return None
    
    fig = go.Figure()
    
    colors = ['#3498db', '#e74c3c', '#2ecc71', '#9b59b6']
    
    for idx, col in enumerate(numeric_cols):
        fig.add_trace(go.Scatter(
            x=data['Date'],
            y=data[col],
            mode='lines+markers',
            name=col,
            line=dict(color=colors[idx % len(colors)], width=2),
            marker=dict(size=4)
        ))
    
    fig.update_layout(
        title=f"{station_name} — Last {days} Days",
        xaxis_title="Date",
        yaxis_title="Measurement Value",
        hovermode='x unified',
        height=500,
        template='plotly_white',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

# Main App
def main():
    st.title("🌊 Observation Station Monitor")
    
    # Sidebar - File Upload and Station List
    with st.sidebar:
        st.header("📁 Data Upload")
        
        location_file = st.file_uploader(
            "Upload Location.xlsx",
            type=['xlsx'],
            help="Upload the Excel file containing station locations"
        )
        
        data_file = st.file_uploader(
            "Upload Data.xlsx",
            type=['xlsx'],
            help="Upload the Excel file containing station data"
        )
        
        if location_file and data_file:
            # Load data
            if st.session_state.stations_data is None:
                with st.spinner("Loading location data..."):
                    st.session_state.stations_data = load_location_data(location_file)
            
            if st.session_state.data_df is None:
                with st.spinner("Loading station data..."):
                    st.session_state.data_df = load_data_file(data_file)
            
            if st.session_state.stations_data is not None:
                st.success(f"✓ Loaded {len(st.session_state.stations_data)} stations")
                
                st.markdown("---")
                st.header("🏢 Station List")
                
                # Station list
                for idx, station in st.session_state.stations_data.iterrows():
                    station_name = station.get('Station Name ', 'Unknown')
                    station_id = station.get('Station ID', 'N/A')
                    station_type = station.get('Type', 'N/A')
                    status = station.get('Status', 'Unknown')
                    icon = get_station_icon(station_type)
                    
                    # Create button for each station
                    if st.button(
                        f"{icon} {station_name}",
                        key=f"station_{idx}",
                        use_container_width=True
                    ):
                        st.session_state.selected_station = station
                    
                    # Show mini info
                    st.caption(f"ID: {station_id} | Type: {station_type}")
                    
                    # Status badge
                    if status.lower() == 'active':
                        st.markdown(
                            '<span class="status-badge-active">Active</span>',
                            unsafe_allow_html=True
                        )
                    elif status.lower() == 'dead':
                        st.markdown(
                            '<span class="status-badge-dead">Dead</span>',
                            unsafe_allow_html=True
                        )
                    
                    st.markdown("---")
        else:
            st.info("👆 Please upload both Location.xlsx and Data.xlsx files to begin")
    
    # Main Content Area
    if st.session_state.stations_data is not None:
        
        # Show map or detail view
        if st.session_state.selected_station is None:
            # Map View
            st.header("📍 Station Locations")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Stations", len(st.session_state.stations_data))
            with col2:
                active_count = len(st.session_state.stations_data[
                    st.session_state.stations_data['Status'].str.lower() == 'active'
                ])
                st.metric("Active Stations", active_count)
            with col3:
                st.metric("Last Updated", datetime.now().strftime("%Y-%m-%d %H:%M"))
            
            st.markdown("---")
            
            # Create and display map
            station_map = create_map(st.session_state.stations_data)
            if station_map:
                folium_static(station_map, width=1200, height=600)
        
        else:
            # Detail View
            station = st.session_state.selected_station
            
            # Back button
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
            
            # Time range selector
            col1, col2 = st.columns([1, 4])
            with col1:
                days = st.selectbox(
                    "Time Range",
                    options=[7, 30, 90, 120, 365],
                    format_func=lambda x: f"Last {x} Days",
                    index=2  # Default to 90 days
                )
            
            # Load and display chart
            if st.session_state.data_df:
                station_id = str(station.get('Station ID', '')).lower()
                
                # Find matching sheet
                matching_sheet = None
                for sheet_name in st.session_state.data_df.keys():
                    if station_id in sheet_name.lower():
                        matching_sheet = sheet_name
                        break
                
                if matching_sheet:
                    data = st.session_state.data_df[matching_sheet].copy()
                    
                    # Filter by time range
                    filtered_data = filter_data_by_days(data, days)
                    
                    if len(filtered_data) > 0:
                        # Create chart
                        fig = create_time_series_chart(
                            filtered_data,
                            station.get('Station Name ', 'Unknown'),
                            days
                        )
                        
                        if fig:
                            st.plotly_chart(fig, use_container_width=True)
                        else:
                            st.warning("No numeric data available to plot")
                        
                        # Show data table
                        with st.expander("📋 View Raw Data"):
                            st.dataframe(filtered_data, use_container_width=True)
                    else:
                        st.warning(f"No data available for the last {days} days")
                else:
                    st.error(f"No data sheet found for station ID: {station.get('Station ID', 'N/A')}")
            else:
                st.error("Data file not loaded")
    
    else:
        # Welcome screen
        st.info("""
        ### Welcome to the Station Monitoring Dashboard!
        
        Please upload the following files in the sidebar:
        1. **Location.xlsx** - Contains station information and coordinates
        2. **Data.xlsx** - Contains time series data for each station
        
        Once uploaded, you'll be able to:
        - 🗺️ View all stations on an interactive map
        - 📊 Analyze time series data for each station
        - 📈 Filter data by different time ranges
        - 📍 View detailed station information
        """)

if __name__ == "__main__":
    main()