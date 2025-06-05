#!/usr/bin/env python
# coding: utf-8

# Import packages
from dash import Dash, html, dash_table, dcc, callback, Output, Input, no_update
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import fsspec, os, glob, re
from pathlib import Path
import dash_bootstrap_components as dbc
import numpy as np


# Dont run when locally deploy.
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

import plotly.io as pio

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
# Further clean
df = df[~df["site"].isnull()]


color_map = {
    "peav@oldb": "Peavine creek/Old briarcliff way",
    "peav@ndec": "Peavine creek/Oxford Rd NE",
    "peav@vick": "Peavine creek/Chelsea Cir NE",
    "lull@lull": "Lullwater creek/Lullwater Rd NE",
}
df["site_full"] = df["site"].map(color_map)


# Delete the > .
df["tot_coli_conc"] = df["tot_coli_conc"].str.replace(r"[>]", "", regex=True)
df["ecoli_conc"] = df["ecoli_conc"].str.replace(r"[>]", "", regex=True)
df["tot_coli_conc"] = pd.to_numeric(df["tot_coli_conc"])
df["ecoli_conc"] = pd.to_numeric(df["ecoli_conc"])
df["tubidity"] = pd.to_numeric(df["tubidity"], errors="coerce")


# Convert date
df["Date"] = df["Date"].str.strip()
df["Date"] = pd.to_datetime(df["Date"])
df["Date"] = df["Date"].dt.date


# Assign the most recent reading to each site.
df_recent = df.sort_values(["site", "Date"]).groupby("site", as_index=False).last()

# Join with the location info
site = pd.merge(site_loc, df_recent, left_on="site", right_on="site", how="left")


# Calculate center point
center_lat = site["lat"].mean()
center_lon = site["lon"].mean()


# Create a df for measurements their labels.
col_labels = pd.DataFrame(
    {
        "colname": ["ecoli_conc", "ph", "tubidity"],
        "labels": ["E.coli concentrations (MPN/100 ml)", "PH", "Tubidity (NTU)"],
    }
)


# Initialize the app
app = Dash(external_stylesheets=[dbc.themes.LITERA])
server = app.server

# App layout
app.layout = [
    html.Div(
        html.H1(
            "Creek Monitoring Data Dashboard",
            style={"textAlign": "center", "color": "#003366", "marginBottom": "2rem"},
        )
    ),
    dbc.Row(
        [
            # ───────────────────────── left column ─────────────────────────
            dbc.Col(
                [
                    html.H5("Measurements", style={"marginBottom": "0.5rem"}),
                    dcc.RadioItems(
                        id="measurement",
                        options=[
                            {"label": "E.coli concentrations", "value": "ecoli_conc"},
                            {"label": "pH", "value": "ph"},
                            {"label": "Turbidity", "value": "tubidity"},
                        ],
                        value="ecoli_conc",
                        labelStyle={
                            "display": "block"
                        },  # stack radio buttons vertically
                    ),
                ],
                md=6,  # 6 of 12 Bootstrap columns (half-width ≥768 px)
            ),
            # ───────────────────────── right column ────────────────────────
            dbc.Col(
                [
                    html.H5("Monitoring sites", style={"marginBottom": "0.5rem"}),
                    dcc.Dropdown(
                        id="sampling_sites",
                        options=[
                            {"label": s, "value": s} for s in df["site_full"].unique()
                        ],
                        value=df["site_full"].unique()[1],
                        clearable=False,
                    ),
                ],
                md=6,
            ),
        ],
        className="g-3",  # Bootstrap gutter utility: 1 rem gap horizontally & vertically
    ),
    html.Div(
        [dcc.Graph(figure={}, id="map")],
        style={
            "width": "100%",
            "display": "inline-block",
            "padding": "5px",
            "marginTop": "2rem",
        },
    ),
    html.Div(
        [dcc.Graph(figure={}, id="barchart")],
        style={"width": "100%", "display": "inline-block", "padding": "5px"},
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
    bar_dat = df[df["site_full"] == site_chosen]
    bar_labels = col_labels.loc[col_labels["colname"] == col_chosen, "labels"].values[0]
    if col_chosen == "ph":
        lower_bound = min(bar_dat[col_chosen].min(), 7)
        upper_bound = max(bar_dat[col_chosen].max(), 8)
        fig2 = px.bar(
            bar_dat,
            x="Date",
            y=col_chosen,
            title=f"{bar_labels}",
            range_y=[lower_bound, upper_bound],
        )
        labels = {col_chosen: bar_labels}
    elif col_chosen == "ecoli_conc":
        bar_dat["level"] = np.where(
            bar_dat[col_chosen] >= 1000, "Above standard", "Below standard"
        )

        fig2 = px.bar(
            bar_dat,
            x="Date",
            y=col_chosen,
            color="level",  # legend groups
            color_discrete_map={"Above standard": "red", "Below standard": "blue"},
            title=bar_labels,  # main plot title
            labels={
                col_chosen: bar_labels,  # y-axis label
                "level": "E. coli level",  # legend title
            },
        )
    else:
        fig2 = px.bar(
            bar_dat,
            x="Date",
            y=col_chosen,
            title=f"{bar_labels}",
            labels={col_chosen: bar_labels},
        )

    # Modify the map
    styled_site = site.copy()
    styled_site["color"] = styled_site["site_full"].apply(
        lambda x: "red" if x == site_chosen else "blue"
    )
    styled_site["size"] = styled_site["site_full"].apply(
        lambda x: 20 if x == site_chosen else 10
    )
    # styled_site['symbol'] = styled_site['site'].apply(lambda x: 'star' if x == site_chosen else 'circle')

    fig1 = go.Figure(
        go.Scattermapbox(
            lat=site["lat"],
            lon=site["lon"],
            mode="markers",
            text=site["site_full"],  # hover label
            customdata=site[["ecoli_conc", "ph", "tubidity", "Date"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                + "Most recent results:<br>"
                + "Date: %{customdata[3]}<br>"
                + "E.coli (MPN/100 ml): %{customdata[0]}<br>"
                + "PH: %{customdata[1]}<br>"
                + "Tubidity (NTU): %{customdata[2]}<br>"
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
        title={
            "text": "Creek Monitoring Sites",
            "font": {
                "family": "Arial",  # any web-safe or installed font
                "size": 20,  # points
                "color": "#003366",  # hex or rgb/rgba string
            },
        },
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
    port = int(os.environ.get("PORT", 8050))  # fallback to 8050 for local dev
    app.run(host="0.0.0.0", port=port, debug=True)  # for render deployment


test = px.data.tips()
fig = px.scatter(
    test,
    x="total_bill",
    y="tip",
    color="sex",
    symbol="smoker",
    facet_col="time",
    labels={"sex": "Gender", "smoker": "Smokes"},
)
fig.show()
