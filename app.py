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

# Import chatbot and alert system
from chatbot import CreekChatbot
from alerts import WaterQualityAlertSystem, AlertSeverity

# Load environment variables for local development
try:
    # load environment variables from .env file (requires `python-dotenv`)
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables only")
    pass
except Exception as e:
    print(f"⚠️ Could not load .env file: {e}")
    pass

# Dont run when locally deploy.
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")  # Store username in env vars
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # Get token from Render env vars
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")  # Get token from Render env vars
GMAPS_KEY = os.getenv("GMAPS_KEY")  # ← NEW: Google Maps / Directions
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAI API key for chatbot

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

# Initialize chatbot and alert system
chatbot = CreekChatbot(df, site_loc)
alert_system = WaterQualityAlertSystem(df, site_loc)

# Run initial alert checks
all_alerts = alert_system.run_all_checks()
alert_summary = alert_system.get_alert_summary()

# Initialize the app with mobile-optimized theme
app = Dash(
    external_stylesheets=[
        dbc.themes.CERULEAN,  # Water-themed colors perfect for creek monitoring
        "https://use.fontawesome.com/releases/v5.15.4/css/all.css"  # Icons for better UX
    ],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}
    ]
)  # Mobile-first responsive design
server = app.server

# Custom CSS for mobile optimization
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <style>
            /* Mobile-first responsive styles */
            .dashboard-header {
                font-size: clamp(1.5rem, 4vw, 2.5rem);
                font-weight: 700;
                margin-bottom: 1.5rem;
            }
            
            .mobile-card {
                margin-bottom: 1rem;
            }
            
            .chat-container {
                height: clamp(250px, 40vh, 400px);
            }
            
            .btn-mobile {
                min-height: 44px;
                font-size: 0.95rem;
            }
            
            /* Touch-friendly radio buttons */
            .radio-items label {
                padding: 8px 12px;
                margin: 4px 0;
                border-radius: 4px;
                cursor: pointer;
            }
            
            .radio-items input[type="radio"]:checked + label {
                background-color: var(--bs-primary-bg-subtle);
            }
            
            /* Better mobile spacing */
            @media (max-width: 768px) {
                .container, .container-fluid {
                    padding-left: 10px;
                    padding-right: 10px;
                }
                
                .card-body {
                    padding: 1rem;
                }
                
                .btn {
                    width: 100%;
                    margin-bottom: 0.5rem;
                }
                
                .quick-actions .btn {
                    width: auto;
                    margin: 0.25rem;
                }
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
'''

# App layout with mobile-first responsive design
app.layout = dbc.Container(
    [
        # Header with responsive typography
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.H1(
                            [
                                html.I(className="fas fa-tint me-2"),
                                "Creek Monitoring Dashboard"
                            ],
                            className="text-primary text-center dashboard-header"
                        )
                    ],
                    width=12
                )
            ],
            className="mb-3"
        ),
        
        # Alert Banner Section - responsive
        html.Div(id="alert-banner", className="mb-3"),
        
        # Mobile-responsive tabbed interface
        dbc.Card([
            dbc.CardHeader([
                dbc.Tabs([
                    dbc.Tab(label="💬 Chat Assistant", tab_id="tab-chat", active_tab_class_name="fw-bold"),
                    dbc.Tab(label="📊 Data Controls", tab_id="tab-controls", active_tab_class_name="fw-bold"),
                    dbc.Tab(label="🗺️ Site Finder", tab_id="tab-finder", active_tab_class_name="fw-bold"),
                    dbc.Tab(label="📈 Visualizations", tab_id="tab-viz", active_tab_class_name="fw-bold"),
                ], id="main-tabs", active_tab="tab-chat", className="nav-fill")
            ]),
            dbc.CardBody([
                html.Div(id="tab-content")
            ])
        ], className="mobile-card"),
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
    Output("sampling_sites", "value", allow_duplicate=True),
    Output("distance_alert", "children"),
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
            f"— {km:.2f} km, approx. {mins} min walk."
        )

        # 3️⃣ update dropdown & open alert
        return best_site, dcc.Markdown(message), True

    except Exception as e:
        # log error if you wish
        return dash.no_update, f"Error: {e}", True


# Alert system helper functions
def create_alert_card(alert):
    """Create a card component for an individual alert"""
    # Determine alert styling based on severity
    severity_styles = {
        'critical': {'color': 'danger', 'icon': '🚨', 'bg': 'danger'},
        'high': {'color': 'warning', 'icon': '⚠️', 'bg': 'warning'},
        'moderate': {'color': 'info', 'icon': 'ℹ️', 'bg': 'info'},
        'low': {'color': 'secondary', 'icon': '🔍', 'bg': 'light'}
    }
    
    style = severity_styles.get(alert.severity.value, severity_styles['low'])
    
    return dbc.Card(
        [
            dbc.CardHeader(
                [
                    html.Div(
                        [
                            html.Span(style['icon'], style={'margin-right': '10px', 'font-size': '1.2em'}),
                            html.Strong(alert.message, className=f"text-{style['color']}"),
                        ],
                        style={'display': 'flex', 'align-items': 'center'}
                    )
                ],
                className=f"bg-{style['bg']} text-{style['color']}" if style['bg'] != 'light' else f"bg-{style['bg']}"
            ),
            dbc.CardBody(
                [
                    html.P(alert.recommendation, className="mb-2"),
                    html.Small(
                        f"Site: {alert.site_name} | Parameter: {alert.parameter} | Date: {alert.date}",
                        className="text-muted"
                    )
                ]
            )
        ],
        className="mb-3",
        style={'border': f"2px solid {'#dc3545' if style['color'] == 'danger' else '#ffc107' if style['color'] == 'warning' else '#17a2b8' if style['color'] == 'info' else '#6c757d'}"}
    )

def create_alert_summary_badge():
    """Create a summary badge showing alert counts"""
    critical_count = len(alert_system.get_alerts_by_severity(AlertSeverity.CRITICAL))
    high_count = len(alert_system.get_alerts_by_severity(AlertSeverity.HIGH))
    total_count = len(alert_system.active_alerts)
    
    if critical_count > 0:
        return dbc.Badge(
            f"🚨 {critical_count} Critical Alert{'s' if critical_count != 1 else ''}",
            color="danger",
            className="me-2"
        )
    elif high_count > 0:
        return dbc.Badge(
            f"⚠️ {high_count} High Alert{'s' if high_count != 1 else ''}",
            color="warning",
            className="me-2"
        )
    elif total_count > 0:
        return dbc.Badge(
            f"ℹ️ {total_count} Alert{'s' if total_count != 1 else ''}",
            color="info",
            className="me-2"
        )
    else:
        return dbc.Badge(
            "✅ All Clear",
            color="success",
            className="me-2"
        )

# Alert banner callback
@callback(
    Output("alert-banner", "children"),
    Input("alert-banner", "id"),  # Dummy input to trigger on load
)
def update_alert_banner(_):
    """Update the alert banner with current alerts"""
    # Refresh alerts
    alert_system.run_all_checks()
    
    if not alert_system.active_alerts:
        return dbc.Alert(
            [
                html.Div(
                    [
                        html.Span("✅", style={'margin-right': '10px', 'font-size': '1.5em'}),
                        html.Strong("No Water Quality Alerts"),
                        html.Span(" - All monitoring sites are within acceptable parameters", className="ms-2")
                    ],
                    style={'display': 'flex', 'align-items': 'center'}
                )
            ],
            color="success",
            className="mb-3"
        )
    
    # Get critical and high alerts for banner
    critical_alerts = alert_system.get_alerts_by_severity(AlertSeverity.CRITICAL)
    high_alerts = alert_system.get_alerts_by_severity(AlertSeverity.HIGH)
    priority_alerts = critical_alerts + high_alerts
    
    if not priority_alerts:
        # Only low/moderate alerts
        return dbc.Alert(
            [
                html.Div(
                    [
                        create_alert_summary_badge(),
                        html.Span("Minor water quality notifications", className="text-muted ms-2")
                    ],
                    style={'display': 'flex', 'align-items': 'center'}
                ),
                html.Div([create_alert_card(alert) for alert in alert_system.active_alerts[:3]], className="mt-3")  # Show first 3
            ],
            color="info",
            className="mb-3"
        )
    
    # Show critical/high alerts prominently
    alert_color = "danger" if critical_alerts else "warning"
    priority_count = len(priority_alerts)
    
    return dbc.Alert(
        [
            html.Div(
                [
                    html.Span("🚨" if critical_alerts else "⚠️", 
                             style={'margin-right': '10px', 'font-size': '1.5em'}),
                    html.Strong(f"Water Quality Alert - {priority_count} site{'s' if priority_count != 1 else ''} need{'s' if priority_count == 1 else ''} attention"),
                ],
                style={'display': 'flex', 'align-items': 'center', 'margin-bottom': '15px'}
            ),
            html.Div([create_alert_card(alert) for alert in priority_alerts])
        ],
        color=alert_color,
        className="mb-3"
    )

# Chatbot callbacks
@callback(
    Output("chat-messages", "children"),
    Output("chat-input", "value"),
    Input("send-chat-btn", "n_clicks"),
    Input("quick-summary-btn", "n_clicks"),
    Input("quick-compare-btn", "n_clicks"),
    Input("quick-sites-btn", "n_clicks"),
    State("chat-input", "value"),
    State("chat-messages", "children"),
    prevent_initial_call=True,
)
def handle_chat(send_clicks, summary_clicks, compare_clicks, sites_clicks, 
                chat_input, chat_messages):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Handle quick action buttons
    if trigger_id == "quick-summary-btn":
        message = "Give me a water quality summary"
    elif trigger_id == "quick-compare-btn":
        message = "Compare all sites for E. coli levels"
    elif trigger_id == "quick-sites-btn":
        message = "What monitoring sites are available?"
    elif trigger_id == "send-chat-btn" and chat_input:
        message = chat_input
    else:
        return no_update, no_update
    
    # Get chatbot response
    try:
        response = chatbot.chat(message)
    except Exception as e:
        response = f"Sorry, I encountered an error: {str(e)}"
    
    # Create message components
    user_message = html.Div(
        [
            html.Strong("You: ", style={"color": "#007bff"}),
            html.Span(message)
        ],
        style={"margin-bottom": "10px", "padding": "5px"}
    )
    
    assistant_message = html.Div(
        [
            html.Strong("Assistant: ", style={"color": "#28a745"}),
            html.Div(
                # Use pre-line CSS to handle newlines properly
                response,
                style={"white-space": "pre-line"}
            )
        ],
        style={
            "margin-bottom": "15px", 
            "padding": "10px", 
            "background-color": "white",
            "border-radius": "5px",
            "border-left": "3px solid #28a745"
        }
    )
    
    # Update chat messages
    if chat_messages is None:
        chat_messages = []
    
    new_messages = chat_messages + [user_message, assistant_message]
    
    # Clear input for send button
    clear_input = "" if trigger_id == "send-chat-btn" else no_update
    
    return new_messages, clear_input


@callback(
    Output("sampling_sites", "value", allow_duplicate=True),
    Input("chat-messages", "children"),
    prevent_initial_call=True,
)
def update_dashboard_from_chat(chat_messages):
    """Update dashboard based on chat context"""
    if not chat_messages:
        return no_update
    
    # Get the last assistant message
    last_assistant_msg = None
    for msg in reversed(chat_messages):
        if isinstance(msg, dict) and msg.get('props', {}).get('children', [{}])[0].get('props', {}).get('children') == 'Assistant: ':
            last_assistant_msg = msg
            break
    
    if not last_assistant_msg:
        return no_update
    
    # Extract site mentions from the response
    response_text = str(last_assistant_msg)
    
    # Look for site names in the response
    site_mapping = {
        "peavine creek/old briarcliff way": "Peavine creek/Old briarcliff way",
        "peavine creek/oxford rd ne": "Peavine creek/Oxford Rd NE",
        "peavine creek/chelsea cir ne": "Peavine creek/Chelsea Cir NE", 
        "lullwater creek/lullwater rd ne": "Lullwater creek/Lullwater Rd NE"
    }
    
    for site_key, site_value in site_mapping.items():
        if site_key in response_text.lower():
            return site_value
    
    return no_update


# Run the app
if __name__ == "__main__":
#    app.run(host="0.0.0.0", debug=True)  # for render deployment
    app.run(debug=True)  # for local deployment