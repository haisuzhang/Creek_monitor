# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input, no_update
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import fsspec, os, glob, re
from pathlib import Path

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME") # Store username in env vars
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Get token from Render env vars
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")  # Get token from Render env vars

### Incorporate data
# recursive copy all files from the Creek_monitor repository;
destination = Path.cwd()/"data"
destination.mkdir(exist_ok=True, parents=True)
fs = fsspec.filesystem("github", org="haisuzhang", repo="Creek_monitor",username=GITHUB_USERNAME,token=GITHUB_TOKEN)
fs.get(fs.glob("data/*"), destination.as_posix(), recursive=True)

# Incorporate data
df = pd.read_csv('data/data_manual_cleaned.csv')

#Read site locations
site_loc = pd.read_csv('data/Site_loc.csv')

pio.renderers.default = "browser"  # optional
pio.templates.default = "plotly"

pio.templates["plotly"].layout.mapbox.accesstoken = MAPBOX_TOKEN


# #Import data and do initial cleaning

#Keep useful columns
df = df[['sample_date','site','tot_coli_conc','ecoli_conc']]

#Convert to lower case
df['site'] = df['site'].str.lower()
site_loc['site'] = site_loc['site'].str.lower()

#Create pattern for matching
pattern = '|'.join(site_loc['site'].tolist())
df['site'] = df['site'].str.extract(f'({pattern})', expand=False)

#Further clean
df = df[~df['site'].isnull()]
#Delete the > .
df['tot_coli_conc'] = df['tot_coli_conc'].str.replace(r'[>]', '', regex=True)
df['ecoli_conc'] = df['ecoli_conc'].str.replace(r'[>]', '', regex=True)
df['tot_coli_conc'] = pd.to_numeric(df['tot_coli_conc'])
df['ecoli_conc'] = pd.to_numeric(df['ecoli_conc'])

#Assign the most recent reading to each site.
df_recent = df.sort_values(['site','sample_date']).groupby('site',as_index = False).last()

#Join with the location info
site = pd.merge(site_loc,df_recent,left_on = 'site',right_on = 'site',how = 'left')

#Calculate center point
center_lat = site["lat"].mean()
center_lon = site["lon"].mean()

# Initialize the app
app = Dash()

server = app.server

# App layout
app.layout = [html.Div(
    html.H1("My Dashboard", style={'textAlign': 'center', 'color': '#003366'})
    ),
html.Div([
    dcc.RadioItems(options=[{'label':'Total Coli concentrations','value':'tot_coli_conc'},
                            {'label':'Ecoli concentrations','value':'ecoli_conc'}], 
                    value='tot_coli_conc', id='measurement'),
    dcc.Dropdown(id='sampling_sites',
                 options=df['site'].unique(),
                 value=df['site'].unique()[1]),
]),
html.Div([
    html.Div([
    dcc.Graph(figure={}, id='map')], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'}),
    html.Div([
    dcc.Graph(figure={}, id='barchart')], style={'width': '48%', 'display': 'inline-block', 'padding': '10px'})
])    
    
]

# Add controls to build the interaction
@callback(
    Output(component_id='map', component_property='figure'),
    Output(component_id='barchart', component_property='figure'),
    Input(component_id='measurement', component_property='value'),
    Input(component_id='sampling_sites', component_property='value')
)
def update_graph(col_chosen,site_chosen):

    #Modify the barchart
    bar_dat = df[df['site'] == site_chosen]
    fig2 = px.bar(bar_dat, x='sample_date', y=col_chosen, title = 'Concentrations')
    
    #Modify the map
    styled_site = site.copy()
    styled_site['color'] = styled_site['site'].apply(lambda x: 'red' if x == site_chosen else 'blue')
    styled_site['size'] = styled_site['site'].apply(lambda x: 20 if x == site_chosen else 10)
    # styled_site['symbol'] = styled_site['site'].apply(lambda x: 'star' if x == site_chosen else 'circle')
    
    fig1 = go.Figure(go.Scattermapbox(
        lat=site["lat"],
        lon=site["lon"],
        mode='markers',
        text=site["site"],  # hover label
        customdata=site[["tot_coli_conc", "ecoli_conc"]],
        hovertemplate=(
            "<b>%{text}</b><br>" +
            "Total Coli: %{customdata[0]}<br>" +
            "E.coli: %{customdata[1]}<br>" +
            "<extra></extra>"
        ),
        hoverlabel=dict(
        bgcolor='white',  # Background color of hover box
        font_size=16,
        font_family='Rockwell'),
        
        marker=go.scattermapbox.Marker(
            size=styled_site["size"],
            color=styled_site["color"],
            opacity=1
            # symbol=styled_site["symbol"]
            # symbol = 'star'
        )
))

# Layout for the map
    fig1.update_layout(
    mapbox=dict(
        accesstoken=MAPBOX_TOKEN,
        style="streets",  # or 'light-v10', 'satellite-v9', etc.
        center={"lat": center_lat, "lon": center_lon},
        zoom=12
    ),
    margin={"r": 0, "t": 30, "l": 0, "b": 0},
    title="XY Point Map"
)

    return fig1,fig2

@callback(
    Output('sampling_sites', 'value'),
    Input('map', 'clickData')
)
def map_click(click_value):
    print("clickData received:", click_value)  # 🔍 See exactly what's coming in
    if click_value is None:
        return no_update

    site_clicked = click_value['points'][0].get('text')
    print("site clicked:", site_clicked)
    return site_clicked

# Run the app
if __name__ == '__main__':
    app.run(host= '0.0.0.0', debug=True) # for render deployment
