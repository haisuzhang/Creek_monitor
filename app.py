#!/usr/bin/env python
# coding: utf-8

# Import packages
import dash
from dash import (
    Dash,
    html,
    dash_table,
    dcc,
    callback,
    Output,
    Input,
    no_update,
    State,
    callback_context,
    no_update,
)
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
import fsspec, os, glob, re
from pathlib import Path
import dash_bootstrap_components as dbc
import numpy as np
import googlemaps
from dash.exceptions import PreventUpdate


# Dont run when locally deploy.
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")  # Store username in env vars
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Get token from Render env vars
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")  # Get token from Render env vars
GMAPS_KEY = os.getenv("GMAPS_KEY")  # ← NEW: Google Maps / Directions

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


# google map api key
gmaps = googlemaps.Client(key=GMAPS_KEY)
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
df = df[~df["Date"].isnull()]

# Delete the > .
df["tot_coli_conc"] = df["tot_coli_conc"].str.replace(r"[>]", "", regex=True)
df["ecoli_conc"] = df["ecoli_conc"].str.replace(r"[>]", "", regex=True)
df["tot_coli_conc"] = pd.to_numeric(df["tot_coli_conc"])
df["ecoli_conc"] = pd.to_numeric(df["ecoli_conc"])
df["tubidity"] = pd.to_numeric(df["tubidity"], errors="coerce")


# Convert date
df["Date"] = pd.to_datetime(df["Date"].str.strip())  # clean + parse
df["WeekDate"] = (
    df["Date"]
    .dt.to_period("W")  # Monday‑anchored weekly period
    .apply(lambda p: p.start_time + pd.Timedelta(days=2))
)
df["WeekDate"] = df["WeekDate"].dt.date  # Convert to YYYY-mm-dd


# Add full name for the creek monitors.
color_map = {
    "peav@oldb": "Peavine creek/Old briarcliff way",
    "peav@ndec": "Peavine creek/Oxford Rd NE",
    "peav@vick": "Peavine creek/Chelsea Cir NE",
    "lull@lull": "Lullwater creek/Lullwater Rd NE",
}
df["site_full"] = df["site"].map(color_map)


# Average out the multiple values within same day.
df = (
    df.drop(columns=["Date"])
    .groupby(["WeekDate", "site", "site_full"])
    .mean()
    .reset_index()
)


# Assign the most recent reading to each site.
df_recent = df.sort_values(["site", "WeekDate"]).groupby("site", as_index=False).last()

# Join with the location info
site = pd.merge(site_loc, df_recent, left_on="site", right_on="site", how="left")


# Calculate center point
center_lat = site["lat"].mean()
center_lon = site["lon"].mean()

# Create a df for measurements their labels.
col_labels = pd.DataFrame(
    {
        "colname": ["ecoli_conc", "ph", "tubidity"],
        "labels": [
            "<i>E.&nbsp;coli</i> concentrations (MPN/100 ml)",
            "PH",
            "Tubidity (NTU)",
        ],
    }
)


# Initialize the app
app = Dash(
    external_stylesheets=[dbc.themes.FLATLY]
)  # Using FLATLY theme for a modern look
server = app.server

# App layout
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            "Creek Monitoring Data Dashboard",
                            className="text-primary text-center mb-4 mt-3",
                            style={"font-weight": "bold"},
                        )
                    ]
                )
            ]
        ),
        dbc.Row(
            [
                # ───────────────────────── left column ─────────────────────────
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Measurements", className="card-title mb-3"
                                        ),
                                        dcc.RadioItems(
                                            id="measurement",
                                            options=[
                                                {
                                                    "label": html.Span(
                                                        [
                                                            html.Em(
                                                                "E. coli"
                                                            ),  # ← italics
                                                            " concentrations",
                                                        ]
                                                    ),
                                                    "value": "ecoli_conc",
                                                },
                                                {"label": " pH", "value": "ph"},
                                                {
                                                    "label": " Turbidity",
                                                    "value": "tubidity",
                                                },
                                            ],
                                            value="ecoli_conc",
                                            className="radio-items",
                                            labelStyle={
                                                "display": "block",
                                                "margin": "10px 0",
                                                "font-size": "1.1em",
                                            },
                                        ),
                                    ]
                                )
                            ],
                            className="h-100 shadow",
                        )
                    ],
                    md=6,
                ),
                # ───────────────────────── right column ────────────────────────
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        html.H5(
                                            "Monitoring sites",
                                            className="card-title mb-3",
                                        ),
                                        dcc.Dropdown(
                                            id="sampling_sites",
                                            options=[
                                                {"label": s, "value": s}
                                                for s in df["site_full"].unique()
                                            ],
                                            value=df["site_full"].unique()[1],
                                            clearable=False,
                                            className="mb-2",
                                        ),
                                    ]
                                )
                            ],
                            className="h-100 shadow",
                        )
                    ],
                    md=6,
                ),
            ],
            className="mb-4 g-3",
        ),
        # ───────── Address → Nearest‑site card (copy‑paste block) ─────────
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                # input + button in one row
                                dbc.Row(
                                    [
                                        dbc.Col(
                                            dbc.Input(
                                                id="address_input",
                                                placeholder="Type an address or place name…",
                                                type="text",
                                                debounce=True,
                                                className="mb-2",
                                            ),
                                            md=8,
                                        ),
                                        dbc.Col(
                                            dbc.Button(
                                                "Find nearest site",
                                                id="find_site_btn",
                                                color="primary",
                                                className="mb-2",
                                                n_clicks=0,
                                            ),
                                            md=4,
                                        ),
                                    ],
                                    className="g-2",  # small gap between input & button
                                ),
                                # distance / error message
                                dbc.Alert(
                                    id="distance_alert",
                                    color="info",
                                    is_open=False,
                                    fade=False,
                                    className="mt-1 mb-0",
                                ),
                            ]
                        ),
                        className="shadow",
                    )
                )
            ],
            className="mb-4",  # bottom margin before the map card
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [dcc.Graph(figure={}, id="map", className="mb-2")]
                                )
                            ],
                            className="shadow mb-4",
                        )
                    ]
                )
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Card(
                            [
                                dbc.CardBody(
                                    [
                                        dcc.Graph(
                                            figure={}, id="barchart", className="mb-1"
                                        ),
                                        html.Small(
                                            [
                                                "* Sample results are weekly medians; dashed line marks the EPA standard for ",
                                                html.Em(
                                                    "E. coli"
                                                ),  # italics for the species name
                                                " (<1000 MPN/100 mL).",
                                            ],
                                            className="text-muted",
                                        ),
                                    ]
                                )
                            ],
                            className="shadow",
                        )
                    ]
                )
            ]
        ),
    ],
    fluid=True,
    className="px-4 py-3",
)

# Add custom CSS
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Creek Monitor Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            .radio-items input[type="radio"] {
                margin-right: 8px;
            }
            .card {
                border-radius: 10px;
                border: none;
            }
            .card-title {
                color: #2C3E50;
                font-weight: 600;
            }
            body {
                background-color: #f8f9fa;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


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

    # PH needs to be shown between 7-8
    if col_chosen == "ph":
        lower_bound = min(bar_dat[col_chosen].min(), 7)
        upper_bound = max(bar_dat[col_chosen].max(), 8)
        fig2 = px.bar(
            bar_dat,
            x="WeekDate",
            y=col_chosen,
            title=f"{bar_labels}",
            range_y=[lower_bound, upper_bound],
        )
        labels = {col_chosen: bar_labels}

    # Ecoli standard is 1000
    elif col_chosen == "ecoli_conc":
        bar_dat["level"] = np.where(
            bar_dat[col_chosen] >= 1000, "Above standard", "Below standard"
        )

        fig2 = px.bar(
            bar_dat,
            x="WeekDate",
            y=col_chosen,
            color="level",  # legend groups
            color_discrete_map={"Above standard": "red", "Below standard": "blue"},
            title=bar_labels,  # main plot title
            labels={
                col_chosen: "<i>E.&nbsp;coli</i> level",  # y-axis label
                "level": "<i>E.&nbsp;coli</i> level",  # legend title
            },
        )
        fig2.add_hline(
            y=1000, line_dash="dash", line_color="black"  # standard threshold
        )
        fig2.update_layout(margin=dict(t=60))
    else:
        fig2 = px.bar(
            bar_dat,
            x="WeekDate",
            y=col_chosen,
            title=f"{bar_labels}",
            labels={col_chosen: bar_labels},
        )

    # Update the title for fig2.
    fig2.update_layout(xaxis_title="Date")

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
            customdata=site[["ecoli_conc", "ph", "tubidity", "WeekDate"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                + "Most recent results:<br>"
                + "Date: %{customdata[3]}<br>"  # 2025-03-24 (W13)
                + "<i>E.&nbsp;coli</i> (MPN/100&nbsp;mL): %{customdata[0]}<br>"
                + "pH: %{customdata[1]}<br>"
                + "Turbidity (NTU): %{customdata[2]}<br>"
                + "<extra></extra>"
            ),
            hoverlabel=dict(
                bgcolor="white",  # Background color of hover box
                font_size=16,
                font_family="Arial",
            ),
            marker=go.scattermapbox.Marker(
                size=styled_site["size"], color=styled_site["color"], opacity=1
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


@callback(
    Output("sampling_sites", "value", allow_duplicate=True),  # auto‑select nearest site
    Output("distance_alert", "children"),  # show distance/time
    Output("distance_alert", "is_open"),
    Input("find_site_btn", "n_clicks"),
    State("address_input", "value"),
    prevent_initial_call=True,
)
def pick_nearest_site(n_clicks, address):
    if not address:
        raise PreventUpdate

    try:
        # 1️⃣ query walking directions to every site
        best_site = None
        best_meters = float("inf")
        best_time = None

        for _, row in site.iterrows():  # site = your lat/lon table
            dest = f"{row.lat},{row.lon}"
            directions = gmaps.directions(
                origin=address, destination=dest, mode="walking", units="metric"
            )
            if not directions:  # skip if API found nothing
                continue
            leg = directions[0]["legs"][0]
            dist_m = leg["distance"]["value"]
            time_s = leg["duration"]["value"]

            if dist_m < best_meters:
                best_site = row["site_full"]
                best_meters = dist_m
                best_time = time_s

        if best_site is None:  # nothing returned
            return (
                dash.no_update,
                (
                    "No walking route found. "
                    "Try a different address or check your spelling."
                ),
                True,
            )

        # 2️⃣ human‑readable numbers
        km = best_meters / 1000
        mins = int(round(best_time / 60))

        message = (
            f"Closest monitoring site: **{best_site}** "
            f"— {km:.2f} km, approx. {mins} min walk."
        )

        # 3️⃣ update dropdown & open alert
        return best_site, dcc.Markdown(message), True

    except Exception as e:
        # log error if you wish
        return dash.no_update, f"Error: {e}", True


# Run the app
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)  # for render deployment
