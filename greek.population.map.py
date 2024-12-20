import streamlit as st
import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from streamlit.components.v1 import html

# Path to the shapefile
shapefile_path = "NUTS_RG_01M_2024_3035.shp/NUTS_RG_01M_2024_3035.shp"

def main():
    # Title and Introduction
    st.title("🌍 Greece NUTS 3 Administrative Map")
    st.markdown(
        """
        Explore the **NUTS 3 administrative regions of Greece** on a modern, interactive map. 
        Hover over a region to highlight it and click markers to learn more about each area!
        """
    )

    # Load the shapefile
    try:
        gdf = gpd.read_file(shapefile_path)
    except Exception as e:
        st.error(f"Failed to load the shapefile: {e}")
        return

    # Filter the GeoDataFrame for Greece (CNTR_CODE == 'EL') and NUTS 3 level
    greece_nuts3_gdf = gdf[(gdf['CNTR_CODE'] == 'EL') & (gdf['LEVL_CODE'] == 3)]

    # Ensure the dataset is not empty
    if greece_nuts3_gdf.empty:
        st.error("No data found for Greece's NUTS 3 regions in the provided shapefile.")
        return

    # Create an Interactive Folium Map
    try:
        # Initialize the map
        m = folium.Map(
            location=[38.5742, 23.8],  
            zoom_start=6.3,
            min_zoom=6,
            max_zoom=10,
            tiles=None
        )

        # Add GeoJSON layer with hover effects
        def highlight_function(feature):
            return {
                'fillColor': '#ffff00',
                'color': 'black',
                'weight': 2,
                'dashArray': '5, 5',
                'fillOpacity': 0.7,
            }

        folium.GeoJson(
            greece_nuts3_gdf,
            style_function=lambda feature: {
                "fillColor": "#3186cc",
                "color": "#000000",
                "weight": 1.5,
                "fillOpacity": 0.5,
            },
            highlight_function=highlight_function,
            tooltip=folium.GeoJsonTooltip(
                fields=["NUTS_NAME"],
                aliases=["Region:"],
                localize=True,
                sticky=True,
                direction="top",
                opacity=0.9,
                permanent=False,
            ),
        ).add_to(m)

        # Add marker clustering for centroids
        marker_cluster = MarkerCluster()
        for _, row in greece_nuts3_gdf.iterrows():
            folium.Marker(
                location=[row.geometry.centroid.y, row.geometry.centroid.x],
                popup=f"<b>Region:</b> {row['NUTS_NAME']}<br>"
                      f"<b>Code:</b> {row['NUTS_ID']}",
                icon=folium.Icon(color="blue", icon="info-sign"),
            ).add_to(marker_cluster)
        marker_cluster.add_to(m)

        # Inject CSS for a light opaque blue background and distinct leaflet elements
        css = """
        <style>
            .leaflet-container {
                background: linear-gradient(180deg, rgba(173, 216, 230, 1) 0%, rgba(135, 206, 235, 1) 100%);
            }
            .leaflet-tile {
                opacity: 0.7;
            }
        </style>
        """
        m.get_root().html.add_child(folium.Element(css))

        # Add Legend
        legend_html = """
        <div id="legend" style="
            position: fixed;
            bottom: 10px;
            left: 10px;
            width: 250px;
            background-color: white;
            border: 2px solid black;
            padding: 10px;
            font-size: 14px;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
            z-index: 9999;
            display: block;">
            <strong>Legend</strong>
            <ul style="list-style-type: none; padding: 0;">
                <li><span style="background-color: #3186cc; padding: 5px; margin-right: 10px; display: inline-block;"></span>NUTS 3 Regions</li>
                <li><span style="background-color: black; padding: 5px; margin-right: 10px; display: inline-block;"></span>Borders</li>
            </ul>
            <button id="close-legend" style="margin-top: 10px;">Close</button>
        </div>
        <button id="open-legend" style="
            position: fixed;
            bottom: 10px;
            left: 10px;
            display: none;
            z-index: 9999;">
            Show Legend
        </button>
        <script>
        // Close legend after 3 seconds
        setTimeout(() => {
            document.getElementById('legend').style.display = 'none';
            document.getElementById('open-legend').style.display = 'block';
        }, 3000);

        // Toggle legend visibility
        document.getElementById('close-legend').onclick = function() {
            document.getElementById('legend').style.display = 'none';
            document.getElementById('open-legend').style.display = 'block';
        };
        document.getElementById('open-legend').onclick = function() {
            document.getElementById('legend').style.display = 'block';
            document.getElementById('open-legend').style.display = 'none';
        };
        </script>
        """
        m.get_root().html.add_child(folium.Element(legend_html))

        # Save the map to an HTML file
        map_html = "greece_map_with_legend.html"
        m.save(map_html)

        # Load and display the map in Streamlit
        with open(map_html, "r") as f:
            iframe_html = f.read()
        html(iframe_html, height=600)
    except Exception as e:
        st.error(f"Error generating the map: {e}")

if __name__ == "__main__":
    main()
