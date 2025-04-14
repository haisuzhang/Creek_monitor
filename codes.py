#!/usr/bin/env python
# coding: utf-8

# In[1]:


# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input, no_update
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


# Incorporate data
df = pd.read_csv('data_manual_cleaned.csv')

#Read site locations
site_loc = pd.read_csv('Site_loc.csv')


# In[2]:


import plotly.io as pio
pio.renderers.default = "browser"  # optional
pio.templates.default = "plotly"

mapbox_token = "pk.eyJ1IjoiaGFpc3V6aGFuZyIsImEiOiJjbTlibWk4ZGUwaGhpMnFvY3Vrc3M2Y2gzIn0.caNs4q2Nu75ue-K_YyU9Eg"
pio.templates["plotly"].layout.mapbox.accesstoken = mapbox_token


# #Import data and do initial cleaning

# In[3]:


#Keep useful columns
df = df[['sample_date','site','tot_coli_conc','ecoli_conc']]

#Convert to lower case
df['site'] = df['site'].str.lower()
site_loc['site'] = site_loc['site'].str.lower()

#Create pattern for matching
pattern = '|'.join(site_loc['site'].tolist())
df['site'] = df['site'].str.extract(f'({pattern})', expand=False)




# In[4]:


#Further clean
df = df[~df['site'].isnull()]
#Delete the > .
df['tot_coli_conc'] = df['tot_coli_conc'].str.replace(r'[>]', '', regex=True)
df['ecoli_conc'] = df['ecoli_conc'].str.replace(r'[>]', '', regex=True)
df['tot_coli_conc'] = pd.to_numeric(df['tot_coli_conc'])
df['ecoli_conc'] = pd.to_numeric(df['ecoli_conc'])


# In[5]:


#Assign the most recent reading to each site.
df_recent = df.sort_values(['site','sample_date']).groupby('site',as_index = False).last()

#Join with the location info
site = pd.merge(site_loc,df_recent,left_on = 'site',right_on = 'site',how = 'left')



# In[6]:


#Calculate center point
center_lat = site["lat"].mean()
center_lon = site["lon"].mean()


# In[ ]:


# Initialize the app
app = Dash()

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
        accesstoken=mapbox_token,
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
    app.run(debug=True, port=8051)


# In[8]:


help(go.scattermapbox)

