# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input, no_update
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import fsspec, os, glob, re
from pathlib import Path

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")  # Store username in env vars
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Get token from Render env vars
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")  # Get token from Render env vars

### Incorporate data
# recursive copy all files from the Creek_monitor repository;
destination = Path.cwd() / "data"
destination.mkdir(exist_ok=True, parents=True)
fs = fsspec.filesystem(
    "github",
    org="haisuzhang",
    repo="Creek_monitor",
    username=GITHUB_USERNAME,
    token=GITHUB_TOKEN,
)
fs.get(fs.glob("data/*"), destination.as_posix(), recursive=True)

# Incorporate data
df = pd.read_csv("data/Updated results.csv", skiprows=2)

# Read site locations
site_loc = pd.read_csv("data/Site_loc.csv")

pio.renderers.default = "browser"  # optional
pio.templates.default = "plotly"

pio.templates["plotly"].layout.mapbox.accesstoken = MAPBOX_TOKEN


# #Import data and do initial cleaning

# Keep useful columns
df = df[["Date", "site", "tot_coli_conc", "ecoli_conc", "ph", "tubidity"]]

# Convert to lower case
df["site"] = df["site"].str.lower()
site_loc["site"] = site_loc["site"].str.lower()

# Create pattern for matching
pattern = "|".join(site_loc["site"].tolist())
df["site"] = df["site"].str.extract(f"({pattern})", expand=False)


# In[8]:


# Further clean
df = df[~df["site"].isnull()]
# Delete the > .
df["tot_coli_conc"] = df["tot_coli_conc"].str.replace(r"[>]", "", regex=True)
df["ecoli_conc"] = df["ecoli_conc"].str.replace(r"[>]", "", regex=True)
df["tot_coli_conc"] = pd.to_numeric(df["tot_coli_conc"])
df["ecoli_conc"] = pd.to_numeric(df["ecoli_conc"])


# In[10]:


# Assign the most recent reading to each site.
df_recent = df.sort_values(["site", "Date"]).groupby("site", as_index=False).last()

# Join with the location info
site = pd.merge(site_loc, df_recent, left_on="site", right_on="site", how="left")


# In[11]:


# Calculate center point
center_lat = site["lat"].mean()
center_lon = site["lon"].mean()


# In[18]:


# Create a df for measurements their labels.
col_labels = pd.DataFrame(
    {
        "colname": ["ecoli_conc", "ph", "tubidity"],
        "labels": ["E.coli concentrations", "PH", "Tubidity"],
    }
)


# In[ ]:


# Initialize the app
app = Dash()

# App layout
app.layout = [
    html.Div(
        html.H1(
            "Creek Monitoring Data Dashboard",
            style={"textAlign": "center", "color": "#003366"},
        )
    ),
    html.Div(
        [
            dcc.RadioItems(
                options=[
                    # {'label':'Total Coli concentrations','value':'tot_coli_conc'},
                    {"label": "E.coli concentrations", "value": "ecoli_conc"},
                    {"label": "PH", "value": "ph"},
                    {"label": "Tubidity", "value": "tubidity"},
                ],
                value="ecoli_conc",
                id="measurement",
            ),
            dcc.Dropdown(
                id="sampling_sites",
                options=df["site"].unique(),
                value=df["site"].unique()[1],
            ),
        ]
    ),
    html.Div(
        [
            html.Div(
                [dcc.Graph(figure={}, id="map")],
                style={"width": "48%", "display": "inline-block", "padding": "10px"},
            ),
            html.Div(
                [dcc.Graph(figure={}, id="barchart")],
                style={"width": "48%", "display": "inline-block", "padding": "10px"},
            ),
        ]
    ),
]


# Add controls to build the interaction
@callback(
    Output(component_id="map", component_property="figure"),
    Output(component_id="barchart", component_property="figure"),
    Input(component_id="measurement", component_property="value"),
    Input(component_id="sampling_sites", component_property="value"),
)
def update_graph(col_chosen, site_chosen):

    # Modify the barchart
    bar_dat = df[df["site"] == site_chosen]
    bar_labels = col_labels.loc[col_labels["colname"] == col_chosen, "labels"].values[0]
    fig2 = px.bar(
        bar_dat,
        x="Date",
        y=col_chosen,
        title=f"{bar_labels}",
        labels={col_chosen: bar_labels},
    )

    # Modify the map
    styled_site = site.copy()
    styled_site["color"] = styled_site["site"].apply(
        lambda x: "red" if x == site_chosen else "blue"
    )
    styled_site["size"] = styled_site["site"].apply(
        lambda x: 20 if x == site_chosen else 10
    )
    # styled_site['symbol'] = styled_site['site'].apply(lambda x: 'star' if x == site_chosen else 'circle')

    fig1 = go.Figure(
        go.Scattermapbox(
            lat=site["lat"],
            lon=site["lon"],
            mode="markers",
            text=site["site"],  # hover label
            customdata=site[["ecoli_conc", "ph", "tubidity", "Date"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                + "Most recent results:<br>"
                + "Date: %{customdata[3]}<br>"
                + "E.coli: %{customdata[0]}<br>"
                + "PH: %{customdata[1]}<br>"
                + "Tubidity: %{customdata[2]}<br>"
                + "<extra></extra>"
            ),
            hoverlabel=dict(
                bgcolor="white",  # Background color of hover box
                font_size=16,
                font_family="Arial",
            ),
            marker=go.scattermapbox.Marker(
                size=styled_site["size"],
                color=styled_site["color"],
                opacity=1,
                # symbol=styled_site["symbol"]
                # symbol = 'star'
            ),
        )
    )

    # Layout for the map
    fig1.update_layout(
        mapbox=dict(
            accesstoken=MAPBOX_TOKEN,
            style="streets",  # or 'light-v10', 'satellite-v9', etc.
            center={"lat": center_lat, "lon": center_lon},
            zoom=12,
        ),
        margin={"r": 0, "t": 30, "l": 0, "b": 0},
        title="XY Point Map",
    )

    return fig1, fig2


@callback(Output("sampling_sites", "value"), Input("map", "clickData"))
def map_click(click_value):
    print("clickData received:", click_value)  # 🔍 See exactly what's coming in
    if click_value is None:
        return no_update

    site_clicked = click_value["points"][0].get("text")
    print("site clicked:", site_clicked)
    return site_clicked


# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)  # for render deployment
