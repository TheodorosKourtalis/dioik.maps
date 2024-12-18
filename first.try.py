# choropleth_map.py

import pandas as pd
import plotly.express as px
import streamlit as st

# Define the data
data = {
    'State': ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado',
              'Connecticut', 'Delaware', 'Florida', 'Georgia', 'Hawaii', 'Idaho',
              'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana',
              'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota',
              'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
              'New Hampshire', 'New Jersey', 'New Mexico', 'New York',
              'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon',
              'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota',
              'Tennessee', 'Texas', 'Utah', 'Vermont', 'Virginia', 'Washington',
              'West Virginia', 'Wisconsin', 'Wyoming'],
    'State_Code': ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO',
                   'CT', 'DE', 'FL', 'GA', 'HI', 'ID',
                   'IL', 'IN', 'IA', 'KS', 'KY', 'LA',
                   'ME', 'MD', 'MA', 'MI', 'MN',
                   'MS', 'MO', 'MT', 'NE', 'NV',
                   'NH', 'NJ', 'NM', 'NY',
                   'NC', 'ND', 'OH', 'OK', 'OR',
                   'PA', 'RI', 'SC', 'SD',
                   'TN', 'TX', 'UT', 'VT', 'VA', 'WA',
                   'WV', 'WI', 'WY'],
    'Population': [5024279, 733391, 7151502, 3011524, 39538223, 5773714,
                   3605944, 989948, 21538187, 10711908, 1455271, 1839106,
                   12812508, 6785528, 3190369, 2937880, 4505836, 4657757,
                   1362359, 6177224, 7029917, 10077331, 5706494,
                   2961279, 6154913, 1084225, 1961504, 3104614,
                   1377529, 9288994, 2117522, 20201249,
                   10439388, 779094, 11799448, 3959353, 4237256,
                   13002700, 1097379, 5118425, 886667,
                   6910840, 29145505, 3271616, 643077, 8631393, 7705281,
                   1793716, 5893718, 576851],
}

# Create DataFrame
df = pd.DataFrame(data)

# Streamlit App Configuration
st.set_page_config(page_title="USA Choropleth Map - Population by State", layout="wide")

# App Title
st.title("Choropleth Map of USA - Population by State")

# Create the choropleth map using Plotly Express
fig = px.choropleth(
    df,
    locations='State_Code',           # DataFrame column with state codes
    locationmode="USA-states",        # Set to USA states
    scope="usa",                      # Limit map scope to USA
    color='Population',               # DataFrame column to color-code
    hover_name='State',               # Column to display on hover
    color_continuous_scale="Viridis",  # Color scale
    labels={'Population': 'Population'},  # Label for color bar
    title='Population by US State'
)

# Update layout for better appearance
fig.update_layout(
    title_text='Choropleth Map of USA - Population by State',
    geo=dict(
        lakecolor='rgb(255, 255, 255)'
    )
)

# Display the Plotly figure in Streamlit
st.plotly_chart(fig, use_container_width=True)