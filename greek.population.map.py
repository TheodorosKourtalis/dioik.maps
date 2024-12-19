import streamlit as st
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from streamlit.components.v1 import html
import pandas as pd
import os

# Path to the shapefile
shapefile_path = "NUTS_RG_60M_2024_3035.shp"

# Path to your Excel file
excel_path = "A1602_SAM08_TB_DC_00_2021_01_F_GR.xls"  # Update this path as needed

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
        st.success("Shapefile loaded successfully!")
    except Exception as e:
        st.error(f"Failed to load the shapefile: {e}")
        return

    # Filter the GeoDataFrame for Greece (CNTR_CODE == 'EL') and NUTS 3 level
    if 'CNTR_CODE' not in gdf.columns or 'LEVL_CODE' not in gdf.columns:
        st.error("Shapefile does not contain required 'CNTR_CODE' or 'LEVL_CODE' columns.")
        return

    greece_nuts3_gdf = gdf[(gdf['CNTR_CODE'] == 'EL') & (gdf['LEVL_CODE'] == 3)]

    # Ensure the dataset is not empty
    if greece_nuts3_gdf.empty:
        st.error("No data found for Greece's NUTS 3 regions in the provided shapefile.")
        return

    # Display a preview of the GeoDataFrame
    st.subheader("Shapefile Data Preview")
    st.dataframe(greece_nuts3_gdf.head())

    # Determine the engine based on file extension
    file_extension = os.path.splitext(excel_path)[1].lower()
    
    if file_extension == '.xlsx':
        engine = 'openpyxl'
    elif file_extension == '.xls':
        engine = 'xlrd'
    else:
        st.error("Unsupported file format. Please upload an .xls or .xlsx file.")
        return

    # Load the Excel data with the appropriate engine and correct header
    try:
        # Specify header=2 to skip the first two rows (titles/merged cells)
        df = pd.read_excel(excel_path, engine=engine, header=2)
        st.success("Excel data loaded successfully!")
    except Exception as e:
        st.error(f"Failed to load the Excel file: {e}")
        return

    # Display a preview of the Excel data
    st.subheader("Excel Data Preview")
    st.dataframe(df.head())

    # Display actual column names to verify
    st.subheader("Excel Data Columns")
    st.write(df.columns.tolist())

    # Rename columns for easier handling
    df = df.rename(columns={
        "Γεωγραφικός Κωδικός (NUTS1+NUTS2+10ψήφιος)": "GEO_CODE",
        "Περιγραφή": "Description",
        "Μόνιμος": "Permanent",
        "Αστικότητα (1=Αστικά, 2=Αγροτικά)": "Urbanization",
        "Ορεινότητα (Π=Πεδινά, Η=Ημιορεινά, Ο=Ορεινά)": "Mountainous",
        "Έκταση (τχ)": "Area"
    })

    # Check if the required columns exist after renaming
    required_columns = ["GEO_CODE", "Description", "Permanent", "Urbanization", "Mountainous", "Area"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"Excel file is missing one or more required columns: {missing_columns}")
        return
    else:
        st.success("All required columns are present in the Excel data.")

    # Convert 'GEO_CODE' to string to ensure proper merging
    df['GEO_CODE'] = df['GEO_CODE'].astype(str)

    # Handle number formats (replace '.' and ',' accordingly)
    # Assuming that '.' is thousands separator and ',' is decimal separator
    # Remove '.' and replace ',' with '.' for proper float conversion
    numeric_columns = ['Permanent', 'Area']
    for col in numeric_columns:
        df[col] = df[col].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False).astype(float)

    # Handle categorical columns if necessary
    # For 'Urbanization' and 'Permanent', ensure they are categorical
    df['Urbanization'] = pd.to_numeric(df['Urbanization'], errors='coerce').astype('Int64')
    df['Mountainous'] = df['Mountainous'].astype(str)
    df['Permanent'] = pd.to_numeric(df['Permanent'], errors='coerce').astype('Int64')

    # Check if 'NUTS_ID' exists in GeoDataFrame
    if 'NUTS_ID' not in greece_nuts3_gdf.columns:
        st.error("The GeoDataFrame does not contain a 'NUTS_ID' column.")
        return

    # Merge the GeoDataFrame with the Excel data
    merged_gdf = greece_nuts3_gdf.merge(df, left_on='NUTS_ID', right_on='GEO_CODE', how='left')

    # Check for missing data after merge
    missing_data = merged_gdf[merged_gdf['Description'].isna()]
    if not missing_data.empty:
        st.warning("Some regions in the shapefile do not have corresponding data in the Excel file.")

    # Choose the column for choropleth
    choropleth_options = {
        "Αστικότητα (1=Αστικά, 2=Αγροτικά)": "Urbanization",
        "Ορεινότητα (Π=Πεδινά, Η=Ημιορεινά, Ο=Ορεινά)": "Mountainous",
        "Έκταση (τχ)": "Area",
        "Μόνιμος": "Permanent"
    }

    selected_option = st.selectbox(
        "Select a variable for the Choropleth Map:",
        options=list(choropleth_options.keys()),
        index=list(choropleth_options.keys()).index("Έκταση (τχ)")
    )

    choropleth_column = choropleth_options[selected_option]

    # Handle categorical data if necessary
    if choropleth_column in ["Urbanization", "Mountainous", "Permanent"]:
        # Define a color mapping, including a default for missing data
        if choropleth_column == "Urbanization":
            color_mapping = {"1": "blue", "2": "green", "NaN": "lightgray"}
            legend_dict = {"1": "Urban", "2": "Rural", "NaN": "No Data"}
        elif choropleth_column == "Mountainous":
            color_mapping = {"Π": "yellow", "Η": "orange", "Ο": "red", "nan": "lightgray"}
            legend_dict = {"Π": "Plain", "Η": "Semi-mountainous", "Ο": "Mountainous", "nan": "No Data"}
        elif choropleth_column == "Permanent":
            # Assuming 'Permanent' is binary: 1=Permanent, 0=Non-Permanent
            color_mapping = {"1": "purple", "0": "gray", "NaN": "lightgray"}
            legend_dict = {"1": "Permanent", "0": "Non-Permanent", "NaN": "No Data"}

        # Map colors, handling NaN values
        merged_gdf['color'] = merged_gdf[choropleth_column].astype(str).map(color_mapping).fillna('lightgray')
    else:
        # For numerical data like 'Area'
        color_mapping = None  # Let folium choose the color scale
        legend_dict = None

    # Create an Interactive Folium Map
    try:
        # Initialize the map
        m = folium.Map(
            location=[38.5742, 23.8],  
            zoom_start=6.3,
            min_zoom=6,
            max_zoom=10,
            tiles='cartodbpositron'  # Using a base tile for better visualization
        )

        # Define the style function for choropleth
        if color_mapping:
            # For categorical data
            def style_function(feature):
                return {
                    'fillColor': feature['properties'].get('color', 'lightgray'),
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.7,
                }
        else:
            # For numerical data
            def style_function(feature):
                return {
                    'fillColor': '#3186cc',
                    'color': '#000000',
                    'weight': 1,
                    'fillOpacity': 0.5,
                }

        # Add GeoJSON layer with hover effects and choropleth
        folium.GeoJson(
            merged_gdf,
            style_function=style_function,
            highlight_function=lambda x: {
                'fillColor': '#ffff00',
                'color': 'black',
                'weight': 2,
                'dashArray': '5, 5',
                'fillOpacity': 0.7,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["NUTS_NAME", "Description", choropleth_column],
                aliases=["Region:", "Description:", selected_option],
                localize=True,
                sticky=True,
                direction="top",
                opacity=0.9,
                permanent=False,
            ),
        ).add_to(m)

        # Add Choropleth Layer for Numerical Data
        if not color_mapping:
            folium.Choropleth(
                geo_data=merged_gdf,
                data=merged_gdf,
                columns=["NUTS_ID", choropleth_column],
                key_on="feature.properties.NUTS_ID",
                fill_color="YlOrRd",
                fill_opacity=0.7,
                line_opacity=0.2,
                legend_name=selected_option,
            ).add_to(m)

        # Add Legend for Categorical Data
        if legend_dict:
            legend_html = f"""
            <div id="legend" style="
                position: fixed;
                bottom: 10px;
                left: 10px;
                width: 220px;
                background-color: white;
                border: 2px solid black;
                padding: 10px;
                font-size: 14px;
                box-shadow: 2px 2px 6px rgba(0,0,0,0.3);
                z-index: 9999;
                display: block;">
                <strong>Legend</strong>
                <ul style="list-style-type: none; padding: 0;">
            """
            for key, label in legend_dict.items():
                legend_html += f'<li><span style="background-color: {color_mapping.get(key, "lightgray")}; padding: 5px; margin-right: 10px; display: inline-block;"></span>{label}</li>'
            legend_html += """
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
            // Close legend after 10 seconds
            setTimeout(() => {
                document.getElementById('legend').style.display = 'none';
                document.getElementById('open-legend').style.display = 'block';
            }, 10000);

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

        # Add marker clustering for centroids
        marker_cluster = MarkerCluster()
        for _, row in merged_gdf.iterrows():
            if row.geometry.is_empty or pd.isna(row.geometry):
                continue  # Skip if geometry is empty or NaN
            centroid = row.geometry.centroid
            folium.Marker(
                location=[centroid.y, centroid.x],
                popup=folium.Popup(
                    f"<b>Region:</b> {row['NUTS_NAME']}<br>"
                    f"<b>Code:</b> {row['NUTS_ID']}<br>"
                    f"<b>{selected_option}:</b> {row.get(choropleth_column, 'N/A')}",
                    max_width=300
                ),
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

        # Save the map to an HTML file
        map_html = "greece_map_with_choropleth.html"
        m.save(map_html)

        # Load and display the map in Streamlit
        if os.path.exists(map_html):
            with open(map_html, "r", encoding='utf-8') as f:
                iframe_html = f.read()
            html(iframe_html, height=600)
        else:
            st.error("Map HTML file was not created successfully.")

    except Exception as e:
        st.error(f"Error generating the map: {e}")

if __name__ == "__main__":
    main()
