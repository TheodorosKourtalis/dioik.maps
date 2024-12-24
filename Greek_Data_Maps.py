import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import os
import io

###############################################################################
# 1) Minimal Extra CSS (still white theme, just nicer headings & footers)
###############################################################################
EXTRA_CSS = """
<style>
/* Light styling for subheaders */
h2, h3, h4, h5 {
    color: #333333;
    margin-top: 1rem;
    margin-bottom: 0.5rem;
}
hr {
    border: none;
    border-top: 1px solid #cccccc;
    margin: 2rem 0 1rem;
}
p {
    line-height: 1.6;
}
</style>
"""

###############################################################################
# 2) Basic setup
###############################################################################
st.set_page_config(layout="wide")
st.markdown(EXTRA_CSS, unsafe_allow_html=True)  # Inject the subtle style tweaks

###############################################################################
# 3) Config Paths & Columns
###############################################################################
SHAPEFILE_PATH = "NUTS_RG_01M_2024_3035.shp/NUTS_RG_01M_2024_3035.shp"
EXCEL_FOLDER   = "output_nuts3_excels"

SHAPEFILE_KEY  = "NUTS_ID"
EXCEL_KEY      = "NUTS_ID"
YEAR_COL       = "YEAR"
SEX_COL        = "SEX"
AGE_COL        = "age"  # User can pick from all age groups
VALUE_COL      = "VALUE"

NUTS_LEVEL_COL = "LEVL_CODE"
NUTS3_LEVEL    = 3

###############################################################################
# 4) Caching Functions
###############################################################################
@st.cache_data(show_spinner=True)
def load_shapefile(shp_path):
    gdf_all = gpd.read_file(shp_path)
    if NUTS_LEVEL_COL not in gdf_all.columns:
        raise ValueError(f"Shapefile missing '{NUTS_LEVEL_COL}' column.")

    # Reproject if needed
    if gdf_all.crs and gdf_all.crs.to_epsg() != 4326:
        gdf_all = gdf_all.to_crs(epsg=4326)

    # Filter to NUTS3
    gdf_nuts3 = gdf_all[gdf_all[NUTS_LEVEL_COL] == NUTS3_LEVEL].copy()

    # Simplify geometry for speed
    gdf_nuts3["geometry"] = gdf_nuts3.geometry.simplify(
        tolerance=0.02, preserve_topology=True
    )

    if SHAPEFILE_KEY not in gdf_nuts3.columns:
        raise ValueError(f"NUTS3 shapefile missing '{SHAPEFILE_KEY}' column.")

    return gdf_nuts3

@st.cache_data(show_spinner=True)
def load_all_excels(folder_path):
    all_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".xlsx")]
    if not all_files:
        raise FileNotFoundError(f"No .xlsx files found in folder: {folder_path}")

    df_list = []
    for fname in all_files:
        fpath = os.path.join(folder_path, fname)
        # Force engine='openpyxl'
        try:
            df_temp = pd.read_excel(fpath, engine="openpyxl")
            df_list.append(df_temp)
        except Exception as e:
            st.warning(f"⚠️ Failed to read {fname}: {e}")

    if not df_list:
        raise ValueError("No valid Excel files were loaded.")

    df_combined = pd.concat(df_list, ignore_index=True)

    # Basic checks
    for col in [EXCEL_KEY, YEAR_COL, SEX_COL, VALUE_COL]:
        if col not in df_combined.columns:
            raise ValueError(f"Combined DataFrame missing column '{col}'.")

    # Make sure 'VALUE' is numeric
    df_combined[VALUE_COL] = pd.to_numeric(df_combined[VALUE_COL], errors="coerce")

    return df_combined

###############################################################################
# 5) Load Data
###############################################################################
st.header("Greek Data Maps (NUTS3)")

try:
    gdf_nuts3 = load_shapefile(SHAPEFILE_PATH)
   
except Exception as e:
    st.error(f"❌ Error loading shapefile: {e}")
    st.stop()

try:
    df_all = load_all_excels(EXCEL_FOLDER)
   
except Exception as e:
    st.error(f"❌ Error loading Excel data: {e}")
    st.stop()

###############################################################################
# 6) Sidebar Filters
###############################################################################
st.sidebar.header("Filters")

# 6.1) Year Slider
years_available = sorted(df_all[YEAR_COL].dropna().unique())
min_year = int(min(years_available))
max_year = int(max(years_available))

selected_year = st.sidebar.slider(
    "Select Year",
    min_value=min_year,
    max_value=max_year,
    value=min_year,
    step=1
)

# 6.2) Sex Dropdown
sexes_available = sorted(df_all[SEX_COL].dropna().unique())
selected_sex = st.sidebar.selectbox("Select Sex", options=sexes_available)

# 6.3) Age Group Dropdown
ages_available = sorted(df_all[AGE_COL].dropna().unique())
selected_age = st.sidebar.selectbox("Select Age Group", options=ages_available)

# **Add** a color scale selection for variety
color_scales = ["Viridis", "Tealrose", "Inferno", "Turbo", "Plasma", "Cividis"]
selected_color_scale = st.sidebar.selectbox(
    "Select Color Scale",
    options=color_scales,
    index=0
)

###############################################################################
# 7) Filter Data
###############################################################################
df_filtered = df_all[
    (df_all[YEAR_COL] == selected_year) &
    (df_all[SEX_COL] == selected_sex) &
    (df_all[AGE_COL] == selected_age)
]


###############################################################################
# 8) Merge with Shapefile
###############################################################################
merged_gdf = gdf_nuts3.merge(
    df_filtered,
    how="left",
    left_on=SHAPEFILE_KEY,
    right_on=EXCEL_KEY
)

###############################################################################
# 9) Combine NUTS Level Names for Hover
###############################################################################
def combine_nuts_names(row):
    """
    Combine NUTS_Level_1, NUTS_Level_2, NUTS_Level_3 into one string,
    skipping duplicates.
    """
    items = [
        str(row.get("NUTS_Level_1", "")).strip(),
        str(row.get("NUTS_Level_2", "")).strip(),
        str(row.get("NUTS_Level_3", "")).strip()
    ]
    # Remove blanks and NaNs
    items = [x for x in items if x and pd.notna(x)]

    # Remove duplicates, preserve order
    used = []
    for it in items:
        if it not in used:
            used.append(it)

    return " - ".join(used)

# Create 'hover_name' column
merged_gdf["hover_name"] = merged_gdf.apply(combine_nuts_names, axis=1)

###############################################################################


###############################################################################
# 11) Choropleth Map
###############################################################################
st.subheader("Choropleth Map")

vals = merged_gdf[VALUE_COL].dropna()
val_min = vals.min() if len(vals) else 0
val_max = vals.max() if len(vals) else 1

# Expand color range if no variation
if val_min == val_max:
    val_min -= 1e-3
    val_max += 1e-3
elif (val_max - val_min) < 1e-3:
    mid = (val_min + val_max) / 2
    val_min = mid - 0.5
    val_max = mid + 0.5

fig_map = px.choropleth_mapbox(
    merged_gdf,
    geojson=merged_gdf.__geo_interface__,
    locations=merged_gdf.index,
    color=VALUE_COL,
    color_continuous_scale=selected_color_scale,  # from sidebar
    range_color=(val_min, val_max),
    mapbox_style="carto-positron",  # fixed
    center={"lat": 39.0742, "lon": 21.8243},
    zoom=6,
    hover_name="hover_name",
    hover_data={
        VALUE_COL: True,
        SHAPEFILE_KEY: False
    }
)
fig_map.update_layout(
    margin=dict(r=0, t=0, l=0, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    coloraxis_colorbar=dict(
        title=VALUE_COL,
        orientation="h",
        yanchor="bottom",
        xanchor="left",
        x=0,
        y=-0.25,
        thickness=20,
        len=0.4,
        bgcolor="rgba(0,0,0,0)",       # Transparent background
        bordercolor="rgba(0,0,0,0)"    # Transparent border
    )
)

st.plotly_chart(fig_map, use_container_width=True)

###############################################################################
# 12) Bar Chart (NUTS3 Regions)
###############################################################################
st.subheader("Bar Chart (NUTS3 Regions)")

df_bar = df_filtered[df_filtered[EXCEL_KEY].isin(gdf_nuts3[SHAPEFILE_KEY])].copy()
df_bar = df_bar.dropna(subset=[VALUE_COL])
df_bar[VALUE_COL] = pd.to_numeric(df_bar[VALUE_COL], errors="coerce")

fig_bar = px.bar(
    df_bar,
    x=EXCEL_KEY,
    y=VALUE_COL,
    color=VALUE_COL,
    color_continuous_scale=selected_color_scale,  # from sidebar
    range_color=(val_min, val_max),
    labels={EXCEL_KEY: "Region (NUTS3)", VALUE_COL: "Value"},
    title=f"NUTS3 Bar Chart - Year={selected_year}, Sex={selected_sex}, Age={selected_age}"
)
fig_bar.update_layout(
    xaxis={"categoryorder": "total descending"},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(r=20, t=80, l=0, b=0),
    coloraxis_colorbar=dict(
        orientation="v",
        thickness=15,
        len=0.4
    )
)

st.plotly_chart(fig_bar, use_container_width=True)

###############################################################################

###############################################################################

###############################################################################
# 15) Footer
###############################################################################
st.markdown("""
<hr/>
<p style='text-align:center; color:grey; font-size:0.9rem;'>
Developed by IMOP • A streamlined, modern approach to NUTS3 data visualization
</p>
""", unsafe_allow_html=True)

