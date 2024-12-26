import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import os

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
# 3) Translation Dictionary
###############################################################################
translations = {
    "en": {
        "language_selector": "Select Language / Επιλέξτε Γλώσσα",
        "english": "English",
        "greek": "Ελληνικά",
        "header": "Greek Data Maps (NUTS3)",
        "filters": "Filters",
        "select_year": "Select Year",
        "select_sex": "Select Sex",
        "select_age": "Select Age Group",
        "select_color_scale": "Select Color Scale",
        "choropleth_map": "Choropleth Map",
        "bar_chart": "Bar Chart (NUTS3 Regions)",
        "footer": """
        <hr/>
        <p style='text-align:center; color:grey; font-size:0.9rem;'>
        Developed by IMOP • A streamlined, modern approach to NUTS3 data visualization
        </p>
        """,
        "error_loading_shapefile": "❌ Error loading shapefile: {}",
        "error_loading_excel": "❌ Error loading Excel data: {}",
        "success_message": "Please use the sidebar to filter the data as you please",
        "no_excel_files": "⚠️ No .xlsx files found in folder: {}",
        "failed_read_excel": "⚠️ Failed to read {}: {}",
        "value": "Value",
        "value_label": "Value",  # For colorbar title
        "sex_female": "Female",
        "sex_male": "Male",
        "sex_total": "Total",
        "region": "Region (NUTS3)",
        "tooltip_value": "Value",
        "tooltip_region": "Region",
        "bar_chart_title": "NUTS3 Bar Chart - Year={year}, Sex={sex}, Age={age}",
        "color_scale_title": "Value",
        "sex_unknown": "Unknown",  # Added for unexpected categories
    },
    "el": {  # Greek translations
        "language_selector": "Επιλέξτε Γλώσσα / Select Language",
        "english": "English",
        "greek": "Ελληνικά",
        "header": "Χάρτες Δεδομένων Ελλάδας (NUTS3)",
        "filters": "Φίλτρα",
        "select_year": "Επιλέξτε Έτος",
        "select_sex": "Επιλέξτε Φύλο",
        "select_age": "Επιλέξτε Ομάδα Ηλικίας",
        "select_color_scale": "Επιλέξτε Κλίμακα Χρωμάτων",
        "choropleth_map": "Χρωματικός Χάρτης",
        "bar_chart": "Διάγραμμα Μπάρων (Περιοχές NUTS3)",
        "footer": """
        <hr/>
        <p style='text-align:center; color:grey; font-size:0.9rem;'>
        Αναπτύχθηκε από την IMOP • Μια απλοποιημένη, σύγχρονη προσέγγιση για την οπτικοποίηση δεδομένων NUTS3
        </p>
        """,
        "error_loading_shapefile": "❌ Σφάλμα κατά τη φόρτωση του shapefile: {}",
        "error_loading_excel": "❌ Σφάλμα κατά τη φόρτωση των δεδομένων Excel: {}",
        "success_message": "Παρακαλώ χρησιμοποιήστε τη γραβάτα για να φιλτράρετε τα δεδομένα όπως επιθυμείτε",
        "no_excel_files": "⚠️ Δεν βρέθηκαν αρχεία .xlsx στον φάκελο: {}",
        "failed_read_excel": "⚠️ Αποτυχία ανάγνωσης του {}: {}",
        "value": "Τιμή",
        "value_label": "Τιμή",  # For colorbar title
        "sex_female": "Θηλυκό",
        "sex_male": "Αρσενικό",
        "sex_total": "Σύνολο",
        "region": "Περιοχή (NUTS3)",
        "tooltip_value": "Τιμή",
        "tooltip_region": "Περιοχή",
        "bar_chart_title": "Διάγραμμα Μπάρων NUTS3 - Έτος={year}, Φύλο={sex}, Ηλικία={age}",
        "color_scale_title": "Τιμή",
        "sex_unknown": "Άγνωστο",  # Added for unexpected categories
    }
}

###############################################################################
# 4) Language Selection
###############################################################################
# Add language selector in the sidebar
language = st.sidebar.selectbox(
    "",
    options=[translations["en"]["english"], translations["el"]["greek"]],
    index=0,
    key="language_selector"
)

# Map selection to language code
lang_code = "en" if language == translations["en"]["english"] else "el"

# Function to retrieve translated text
def tr(key, **kwargs):
    text = translations[lang_code].get(key, "")
    if kwargs:
        return text.format(**kwargs)
    return text

###############################################################################
# 5) Config Paths & Columns
###############################################################################
SHAPEFILE_PATH = "NUTS_RG_01M_2024_3035.shp/NUTS_RG_01M_2024_3035.shp"  # Update this path as needed
EXCEL_FOLDER   = "output_nuts3_excels"  # Update this path as needed

SHAPEFILE_KEY  = "NUTS_ID"
EXCEL_KEY      = "NUTS_ID"
YEAR_COL       = "YEAR"
SEX_COL        = "SEX"
AGE_COL        = "age"  # User can pick from all age groups
VALUE_COL      = "VALUE"

NUTS_LEVEL_COL = "LEVL_CODE"
NUTS3_LEVEL    = 3

###############################################################################
# 6) Caching Functions
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

@st.cache_data(show_spinner=True)
def load_shapefile(shp_path):
    gdf_all = gpd.read_file(shp_path)
    
    # Debug: Display shapefile columns
    st.write("Shapefile Columns:", gdf_all.columns.tolist())
    
    if NUTS_LEVEL_COL not in gdf_all.columns:
        raise ValueError(tr("error_loading_shapefile", error=f"Shapefile missing '{NUTS_LEVEL_COL}' column."))
    
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
        raise ValueError(tr("error_loading_shapefile", error=f"NUTS3 shapefile missing '{SHAPEFILE_KEY}' column."))
    
    # Create 'hover_name' column within gdf_nuts3
    gdf_nuts3["hover_name"] = gdf_nuts3.apply(combine_nuts_names, axis=1)
    
    # Debug: Display 'hover_name' creation
    st.write("gdf_nuts3 with 'hover_name':")
    st.write(gdf_nuts3[['NUTS_ID', 'hover_name']].head())
    
    return gdf_nuts3

@st.cache_data(show_spinner=True)
def load_all_excels(folder_path):
    all_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".xlsx")]
    if not all_files:
        raise FileNotFoundError(tr("no_excel_files", folder_path=folder_path))
    
    df_list = []
    for fname in all_files:
        fpath = os.path.join(folder_path, fname)
        # Force engine='openpyxl'
        try:
            df_temp = pd.read_excel(fpath, engine="openpyxl")
            df_list.append(df_temp)
        except Exception as e:
            st.warning(tr("failed_read_excel", file=fname, error=e))
    
    if not df_list:
        raise ValueError(tr("error_loading_excel", error="No valid Excel files were loaded."))
    
    df_combined = pd.concat(df_list, ignore_index=True)
    
    # Basic checks
    for col in [EXCEL_KEY, YEAR_COL, SEX_COL, VALUE_COL]:
        if col not in df_combined.columns:
            raise ValueError(tr("error_loading_excel", error=f"Combined DataFrame missing column '{col}'."))
    
    # Make sure 'VALUE' is numeric
    df_combined[VALUE_COL] = pd.to_numeric(df_combined[VALUE_COL], errors="coerce")
    
    # Debug: Display combined DataFrame columns
    st.write("Combined Excel Data Columns:", df_combined.columns.tolist())
    st.write("Combined Excel Data Sample:")
    st.write(df_combined.head())
    
    return df_combined

###############################################################################
# 7) Load Data
###############################################################################
st.header(tr("header"))

try:
    gdf_nuts3 = load_shapefile(SHAPEFILE_PATH)
   
except Exception as e:
    st.error(tr("error_loading_shapefile", error=e))
    st.stop()

try:
    df_all = load_all_excels(EXCEL_FOLDER)
    st.success(tr("success_message"))

except Exception as e:
    st.error(tr("error_loading_excel", error=e))
    st.stop()

###############################################################################
# 8) Sidebar Filters
###############################################################################
st.sidebar.header(tr("filters"))

# 8.1) Year Slider
years_available = sorted(df_all[YEAR_COL].dropna().unique())
min_year = int(min(years_available))
max_year = int(max(years_available))

selected_year = st.sidebar.slider(
    tr("select_year"),
    min_value=min_year,
    max_value=max_year,
    value=min_year,
    step=1
)

# 8.2) Sex Dropdown
# Assuming the 'SEX' column has values like 'F', 'M', 'T'
sexes_available = sorted(df_all[SEX_COL].dropna().unique())

# Define a mapping for sex translations
sex_translation_map = {
    "F": tr("sex_female"),
    "M": tr("sex_male"),
    "T": tr("sex_total")
}

# Translate sex options, handling unexpected values gracefully
translated_sexes = [sex_translation_map.get(sex, tr("sex_unknown")) for sex in sexes_available]

# Create a mapping from translated label to original value
sex_mapping = {translated: original for translated, original in zip(translated_sexes, sexes_available)}

# Select the translated sex label
selected_sex_display = st.sidebar.selectbox(tr("select_sex"), options=translated_sexes)

# Get the original sex value for filtering
selected_sex = sex_mapping[selected_sex_display]

# 8.3) Age Group Dropdown
ages_available = sorted(df_all[AGE_COL].dropna().unique())
# If age groups need translation, handle here. Assuming age groups are numerical or standardized strings.
selected_age = st.sidebar.selectbox(tr("select_age"), options=ages_available)

# 8.4) Color Scale Selection
color_scales = ["Viridis", "Tealrose", "Inferno", "Turbo", "Plasma", "Cividis"]
selected_color_scale = st.sidebar.selectbox(
    tr("select_color_scale"),
    options=color_scales,
    index=0
)

###############################################################################
# 9) Filter Data
###############################################################################
df_filtered = df_all[
    (df_all[YEAR_COL] == selected_year) &
    (df_all[SEX_COL] == selected_sex) &
    (df_all[AGE_COL] == selected_age)
]

# Debug: Display filtered data
st.write("Filtered Data Sample:")
st.write(df_filtered.head())

###############################################################################
# 10) Merge with Shapefile
###############################################################################
merged_gdf = gdf_nuts3.merge(
    df_filtered,
    how="left",
    left_on=SHAPEFILE_KEY,
    right_on=EXCEL_KEY
)

# Debug: Display merged_gdf
st.write("merged_gdf for Choropleth Map:")
st.write(merged_gdf[['NUTS_ID', 'hover_name', 'VALUE']].head())

###############################################################################
# 11) Prepare Choropleth Map Data
###############################################################################
# Prepare 'custom_data' for choropleth map
merged_gdf["custom_data"] = merged_gdf.apply(lambda row: [row["hover_name"], row[VALUE_COL]], axis=1)

# Debug: Display custom_data
st.write("Choropleth Map Custom Data:")
st.write(merged_gdf[['NUTS_ID', 'custom_data']].head())

###############################################################################
# 12) Choropleth Map
###############################################################################
st.subheader(tr("choropleth_map"))

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

# Create labels mapping for Plotly
labels_map = {
    VALUE_COL: tr("value_label"),
    SHAPEFILE_KEY: tr("region"),
}

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
    custom_data=["hover_name", VALUE_COL],
    labels=labels_map
)

# Define hovertemplate with translated labels
hovertemplate_map = (
    f"{tr('region')}: %{{customdata[0]}}<br>"
    f"{tr('value_label')}: %{{customdata[1]}}<extra></extra>"
)

fig_map.update_traces(
    hovertemplate=hovertemplate_map
)

fig_map.update_layout(
    margin=dict(r=0, t=0, l=0, b=0),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    coloraxis_colorbar=dict(
        title=tr("value_label"),
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
# 13) Bar Chart (NUTS3 Regions)
###############################################################################
st.subheader(tr("bar_chart"))

# Filter df_filtered to include only relevant NUTS3 regions
df_bar = df_filtered[df_filtered[EXCEL_KEY].isin(gdf_nuts3[SHAPEFILE_KEY])].copy()
df_bar = df_bar.dropna(subset=[VALUE_COL])
df_bar[VALUE_COL] = pd.to_numeric(df_bar[VALUE_COL], errors="coerce")

# Merge 'hover_name' from gdf_nuts3 into df_bar based on NUTS_ID
df_bar = df_bar.merge(
    gdf_nuts3[[SHAPEFILE_KEY, "hover_name"]],
    on=EXCEL_KEY,
    how="left"
)

# Debug: Display df_bar after merge
st.write("df_bar after merging with 'hover_name':")
st.write(df_bar[['NUTS_ID', 'hover_name', 'VALUE']].head())

# Prepare 'custom_data' for hovertemplate
df_bar["custom_data"] = df_bar.apply(lambda row: [row["hover_name"], row[VALUE_COL]], axis=1)

# Debug: Display custom_data in df_bar
st.write("Bar Chart Custom Data:")
st.write(df_bar[['NUTS_ID', 'custom_data']].head())

# Translate sex for title
translated_sex_title = tr("sex_female") if selected_sex == "F" else tr("sex_male") if selected_sex == "M" else tr("sex_total")

# Create bar chart with custom_data and hovertemplate
fig_bar = px.bar(
    df_bar,
    x=EXCEL_KEY,
    y=VALUE_COL,
    color=VALUE_COL,
    color_continuous_scale=selected_color_scale,  # from sidebar
    range_color=(val_min, val_max),
    custom_data=["hover_name", VALUE_COL],
    labels={
        EXCEL_KEY: tr("region"),
        VALUE_COL: tr("value"),
    },
    title=tr("bar_chart_title", year=selected_year, sex=translated_sex_title, age=selected_age)
)

# Define hovertemplate for bar chart
hovertemplate_bar = (
    f"{tr('region')}: %{{customdata[0]}}<br>"
    f"{tr('value_label')}: %{{customdata[1]}}<extra></extra>"
)

fig_bar.update_traces(
    hovertemplate=hovertemplate_bar
)

fig_bar.update_layout(
    xaxis={"categoryorder": "total descending"},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(r=20, t=80, l=0, b=0),
    coloraxis_colorbar=dict(
        title=tr("value_label"),
        orientation="v",
        thickness=15,
        len=0.4
    )
)

st.plotly_chart(fig_bar, use_container_width=True)

###############################################################################
# 14) Footer
###############################################################################
st.markdown(tr("footer"), unsafe_allow_html=True)
