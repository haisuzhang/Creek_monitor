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
    from dotenv import load_dotenv
    load_dotenv()
    print("Environment variables loaded from .env file")
except ImportError:
    print("Warning: python-dotenv not installed, using system environment variables only")
    pass
except Exception as e:
    print(f"Warning: Could not load .env file: {e}")
    pass

# Environment variables
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
GMAPS_KEY = os.getenv("GMAPS_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

### Incorporate data (same as original)
destination = Path.cwd() / "data"
destination.mkdir(exist_ok=True, parents=True)

if GITHUB_TOKEN and GITHUB_USERNAME:
    fs = fsspec.filesystem(
        "github",
        org="haisuzhang",
        repo="Creek_monitor",
        username=GITHUB_USERNAME,
        token=GITHUB_TOKEN,
    )
    fs.get(fs.glob("data/*"), destination.as_posix(), recursive=True)

# google map api key
if GMAPS_KEY:
    gmaps = googlemaps.Client(key=GMAPS_KEY)

# Incorporate data
df = pd.read_csv("data/Updated results.csv", skiprows=2)
site_loc = pd.read_csv("data/Site_loc.csv")

# Plotly configuration
pio.renderers.default = "browser"
pio.templates.default = "plotly"
if MAPBOX_TOKEN:
    pio.templates["plotly"].layout.mapbox.accesstoken = MAPBOX_TOKEN

# Data cleaning (same as original)
df = df[["Date", "site", "tot_coli_conc", "ecoli_conc", "ph", "turbidity"]]
df["site"] = df["site"].str.lower()
site_loc["site"] = site_loc["site"].str.lower()

pattern = "|".join(site_loc["site"].tolist())
df["site"] = df["site"].str.extract(f"({pattern})", expand=False)
df = df[~df["site"].isnull()]
df = df[~df["Date"].isnull()]

df["tot_coli_conc"] = df["tot_coli_conc"].str.replace(r"[>]", "", regex=True)
df["ecoli_conc"] = df["ecoli_conc"].str.replace(r"[>]", "", regex=True)
df["tot_coli_conc"] = pd.to_numeric(df["tot_coli_conc"])
df["ecoli_conc"] = pd.to_numeric(df["ecoli_conc"])
df["turbidity"] = pd.to_numeric(df["turbidity"], errors="coerce")

df["Date"] = pd.to_datetime(df["Date"].str.strip())
df["WeekDate"] = (
    df["Date"]
    .dt.to_period("W")
    .apply(lambda p: p.start_time + pd.Timedelta(days=2))
)
df["WeekDate"] = df["WeekDate"].dt.date

color_map = {
    "peav@oldb": "Peavine creek/Old briarcliff way",
    "peav@ndec": "Peavine creek/Oxford Rd NE",
    "peav@vick": "Peavine creek/Chelsea Cir NE",
    "lull@lull": "Lullwater creek/Lullwater Rd NE",
}
df["site_full"] = df["site"].map(color_map)

df = (
    df.drop(columns=["Date"])
    .groupby(["WeekDate", "site", "site_full"])
    .mean()
    .reset_index()
)

df_recent = df.sort_values(["site", "WeekDate"]).groupby("site", as_index=False).last()
site = pd.merge(site_loc, df_recent, left_on="site", right_on="site", how="left")

center_lat = site["lat"].mean()
center_lon = site["lon"].mean()

col_labels = pd.DataFrame({
    "colname": ["ecoli_conc", "ph", "turbidity"],
    "labels": [
        "<i>E.&nbsp;coli</i> concentrations (MPN/100 ml)",
        "PH", 
        "Turbidity (NTU)",
    ],
})

# Initialize chatbot and alert system
chatbot = CreekChatbot(df, site_loc)
alert_system = WaterQualityAlertSystem(df, site_loc)
all_alerts = alert_system.run_all_checks()
alert_summary = alert_system.get_alert_summary()

# Initialize mobile-optimized app
app = Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.CERULEAN,  # Water-themed colors perfect for creek monitoring
        "https://use.fontawesome.com/releases/v5.15.4/css/all.css",  # Icons for better UX
        "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap"  # Modern font
    ],
    meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1, shrink-to-fit=no"}
    ]
)

# Set suppression after app initialization
app.config.suppress_callback_exceptions = True

server = app.server

# Enhanced mobile CSS
app.index_string = '''
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>Creek Monitoring Dashboard</title>
        {%favicon%}
        {%css%}
        <style>
            /* Mobile-first responsive styles */
            body {
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 14px;
                line-height: 1.5;
            }
            
            .dashboard-header {
                font-size: clamp(1.5rem, 5vw, 2.5rem);
                font-weight: 700;
                margin-bottom: 1rem;
                text-align: center;
            }
            
            .mobile-card {
                margin-bottom: 1rem;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            
            .chat-container {
                height: clamp(200px, 35vh, 350px);
                overflow-y: auto;
                border: 1px solid #e9ecef;
                border-radius: 8px;
                padding: 12px;
                background: #f8f9fa;
            }
            
            .btn-mobile {
                min-height: 44px;
                font-size: 0.9rem;
                border-radius: 6px;
                font-weight: 500;
            }
            
            .alert-card {
                border-radius: 8px;
                border: none;
                margin-bottom: 0.5rem;
            }
            
            .nav-tabs .nav-link {
                font-size: 0.85rem;
                padding: 0.75rem 0.5rem;
                border-radius: 6px 6px 0 0;
            }
            
            /* Touch-friendly elements */
            .radio-items {
                margin: 0.5rem 0;
            }
            
            .radio-items label {
                display: block;
                padding: 12px 16px;
                margin: 6px 0;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                cursor: pointer;
                transition: all 0.2s ease;
                background: white;
            }
            
            .radio-items input[type="radio"]:checked + label,
            .radio-items label:hover {
                background-color: var(--bs-primary-bg-subtle);
                border-color: var(--bs-primary);
            }
            
            /* Responsive spacing */
            @media (max-width: 768px) {
                .container, .container-fluid {
                    padding-left: 16px;
                    padding-right: 16px;
                }
                
                .card-body {
                    padding: 1rem;
                }
                
                .btn:not(.btn-sm):not(.quick-btn) {
                    width: 100%;
                    margin-bottom: 0.5rem;
                }
                
                .quick-actions .btn {
                    width: auto;
                    margin: 0.25rem;
                    flex: 1;
                }
                
                .nav-tabs .nav-link {
                    font-size: 0.75rem;
                    padding: 0.5rem 0.25rem;
                }
                
                .dashboard-header {
                    font-size: 1.5rem;
                    margin-bottom: 1rem;
                }
            }
            
            /* Chart responsiveness */
            .js-plotly-plot {
                width: 100% !important;
                height: auto !important;
            }
            
            /* Loading states */
            .loading {
                opacity: 0.7;
                pointer-events: none;
            }
            
            /* Alert animations */
            .alert {
                animation: slideIn 0.3s ease-in-out;
            }
            
            @keyframes slideIn {
                from { transform: translateY(-10px); opacity: 0; }
                to { transform: translateY(0); opacity: 1; }
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

# Simple mobile-first layout - all features visible
app.layout = dbc.Container([
    
    # Header with icon
    html.Div([
        html.H1([
            html.I(className="fas fa-tint me-2 text-primary"),
            "Creek Monitoring"
        ], className="dashboard-header text-primary")
    ], className="text-center mb-3"),
    
    # Alert banner - responsive
    html.Div(id="alert-banner", className="mb-3"),
    
    # Chat section - mobile optimized
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-comments me-2"),
            "Chat Assistant"
        ]),
        dbc.CardBody([
            # Chat messages area
            html.Div(
                id="chat-messages",
                className="chat-container mb-3"
            ),
            
            # Chat input - mobile optimized
            dbc.Row([
                dbc.Col([
                    dbc.InputGroup([
                        dbc.Input(
                            id="chat-input",
                            placeholder="Ask about water quality...",
                            type="text",
                            className="border-end-0"
                        ),
                        dbc.Button([
                            html.I(className="fas fa-paper-plane")
                        ], 
                        id="send-chat-btn",
                        color="primary",
                        n_clicks=0,
                        className="btn-mobile"
                        )
                    ])
                ], width=12)
            ], className="g-2 mb-3"),
            
            # Quick action buttons - responsive
            html.Div([
                html.H6("Quick Actions:", className="mb-2 text-muted"),
                dbc.ButtonGroup([
                    dbc.Button([
                        html.I(className="fas fa-chart-bar me-1 d-none d-sm-inline"),
                        "Summary"
                    ], 
                    id="quick-summary-btn",
                    color="outline-info",
                    size="sm",
                    n_clicks=0,
                    className="quick-btn"
                    ),
                    dbc.Button([
                        html.I(className="fas fa-balance-scale me-1 d-none d-sm-inline"),
                        "Compare"
                    ], 
                    id="quick-compare-btn",
                    color="outline-success",
                    size="sm", 
                    n_clicks=0,
                    className="quick-btn"
                    ),
                    dbc.Button([
                        html.I(className="fas fa-map-pin me-1 d-none d-sm-inline"),
                        "Sites"
                    ], 
                    id="quick-sites-btn",
                    color="outline-warning",
                    size="sm",
                    n_clicks=0,
                    className="quick-btn"
                    ),
                    dbc.Button([
                        html.I(className="fas fa-exclamation-triangle me-1 d-none d-sm-inline"),
                        "Alerts"
                    ], 
                    id="quick-alerts-btn",
                    color="outline-danger",
                    size="sm",
                    n_clicks=0,
                    className="quick-btn"
                    )
                ], className="w-100 d-flex flex-wrap")
            ], className="quick-actions")
        ])
    ], className="mobile-card shadow mb-4"),
    
    # Controls section
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-sliders-h me-2"),
            "Data Controls"
        ]),
        dbc.CardBody([
            dbc.Row([
                # Measurement selection - mobile friendly
                dbc.Col([
                    html.H6([
                        html.I(className="fas fa-flask me-2"),
                        "Select Measurement"
                    ], className="mb-3"),
                    dbc.RadioItems(
                        id="measurement",
                        options=[
                            {
                                "label": html.Div([
                                    html.Strong("E. coli"),
                                    html.Small(" (bacteria levels)", className="text-muted d-block")
                                ]),
                                "value": "ecoli_conc"
                            },
                            {
                                "label": html.Div([
                                    html.Strong("pH"),
                                    html.Small(" (acidity levels)", className="text-muted d-block")
                                ]),
                                "value": "ph"
                            },
                            {
                                "label": html.Div([
                                    html.Strong("Turbidity"),
                                    html.Small(" (water clarity)", className="text-muted d-block")
                                ]),
                                "value": "turbidity"
                            }
                        ],
                        value="ecoli_conc",
                        className="radio-items"
                    )
                ], width=12, lg=6),
                
                # Site selection and finder - mobile optimized
                dbc.Col([
                    html.H6([
                        html.I(className="fas fa-map-marker-alt me-2"),
                        "Monitoring Site"
                    ], className="mb-3"),
                    dcc.Dropdown(
                        id="sampling_sites",
                        options=[
                            {"label": s, "value": s}
                            for s in df["site_full"].unique()
                        ],
                        value=df["site_full"].unique()[0],
                        clearable=False,
                        className="mb-3"
                    ),
                    
                    # Site finder
                    html.H6([
                        html.I(className="fas fa-search-location me-2"),
                        "Find Nearest Site"
                    ], className="mb-3 mt-4"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Input(
                                id="address_input",
                                placeholder="Enter address...",
                                type="text",
                                debounce=True,
                                className="mb-2"
                            )
                        ], width=12, md=8),
                        dbc.Col([
                            dbc.Button([
                                html.I(className="fas fa-search me-2"),
                                "Find"
                            ],
                            id="find_site_btn",
                            color="primary",
                            n_clicks=0,
                            className="btn-mobile w-100"
                            )
                        ], width=12, md=4)
                    ], className="g-2"),
                    
                    # Distance alert
                    dbc.Alert(
                        id="distance_alert",
                        is_open=False,
                        className="mt-3"
                    )
                ], width=12, lg=6)
            ])
        ])
    ], className="mobile-card shadow mb-4"),
    
    # Charts section
    dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-chart-area me-2"),
            "Data Visualization"
        ]),
        dbc.CardBody([
            # Map section
            dbc.Row([
                dbc.Col([
                    html.H6([
                        html.I(className="fas fa-map me-2"),
                        "Site Locations"
                    ], className="mb-3"),
                    dcc.Graph(
                        id="map", 
                        config={
                            'responsive': True,
                            'displayModeBar': False,
                            'scrollZoom': True
                        }
                    )
                ], width=12, lg=6),
                
                # Chart section
                dbc.Col([
                    html.H6([
                        html.I(className="fas fa-chart-bar me-2"),
                        "Measurements Over Time"
                    ], className="mb-3"),
                    dcc.Graph(
                        id="barchart", 
                        config={
                            'responsive': True,
                            'displayModeBar': False,
                            'scrollZoom': True
                        }
                    )
                ], width=12, lg=6)
            ])
        ])
    ], className="mobile-card shadow"),
    
], fluid=True, className="py-3")

# No tab callback needed - everything is visible now

# Alert helper functions
def format_chat_response(response_text):
    """Format chat response for better readability"""
    if not response_text:
        return response_text
    
    # Split text into paragraphs and create HTML elements
    paragraphs = response_text.strip().split('\n\n')
    formatted_content = []
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            continue
            
        # Handle bullet points
        if '•' in paragraph or paragraph.strip().startswith('-'):
            lines = paragraph.split('\n')
            bullet_items = []
            for line in lines:
                if line.strip():
                    if line.strip().startswith('-'):
                        bullet_items.append(html.Li(line.strip()[1:].strip()))
                    elif '•' in line:
                        bullet_items.append(html.Li(line.replace('•', '').strip()))
                    else:
                        bullet_items.append(html.Li(line.strip()))
            if bullet_items:
                formatted_content.append(html.Ul(bullet_items, className="mb-2"))
        
        # Handle numbered lists
        elif any(paragraph.strip().startswith(f"{i}.") for i in range(1, 10)):
            lines = paragraph.split('\n')
            list_items = []
            for line in lines:
                if line.strip():
                    # Remove number prefix if exists
                    clean_line = line.strip()
                    if any(clean_line.startswith(f"{i}.") for i in range(1, 10)):
                        clean_line = clean_line[2:].strip()
                    list_items.append(html.Li(clean_line))
            if list_items:
                formatted_content.append(html.Ol(list_items, className="mb-2"))
        
        # Regular paragraphs
        else:
            # Split long paragraphs by sentences for better readability
            lines = paragraph.split('\n')
            paragraph_content = []
            for line in lines:
                if line.strip():
                    paragraph_content.append(line.strip())
                    paragraph_content.append(html.Br())
            
            # Remove last <br> if exists
            if paragraph_content and isinstance(paragraph_content[-1], type(html.Br())):
                paragraph_content.pop()
                
            if paragraph_content:
                formatted_content.append(html.P(paragraph_content, className="mb-2"))
    
    return html.Div(formatted_content)

def create_alert_card(alert):
    """Create a card for displaying an alert"""
    severity_colors = {
        AlertSeverity.CRITICAL: "danger",
        AlertSeverity.HIGH: "warning", 
        AlertSeverity.MODERATE: "info",
        AlertSeverity.LOW: "light"
    }
    
    severity_icons = {
        AlertSeverity.CRITICAL: "fas fa-skull-crossbones",
        AlertSeverity.HIGH: "fas fa-exclamation-triangle",
        AlertSeverity.MODERATE: "fas fa-info-circle",
        AlertSeverity.LOW: "fas fa-eye"
    }
    
    color = severity_colors.get(alert.severity, "secondary")
    icon = severity_icons.get(alert.severity, "fas fa-info")
    
    return dbc.Alert([
        html.Div([
            html.I(className=f"{icon} me-2"),
            html.Strong(f"{alert.severity.value.title()}: "),
            html.Span(alert.message),
            html.Small(f" (Site: {alert.site_name}, Date: {alert.date})", className="text-muted ms-2")
        ])
    ], color=color, className="alert-card mb-2")

# Essential callbacks for mobile app
@callback(
    Output("map", "figure"),
    Output("barchart", "figure"),
    Input("measurement", "value"),
    Input("sampling_sites", "value"),
    prevent_initial_call=False
)
def update_graph(col_chosen, site_chosen):
    # Provide defaults if None
    if col_chosen is None:
        col_chosen = "ecoli_conc"
    if site_chosen is None:
        site_chosen = df["site_full"].unique()[0]
    
    # Modify the barchart (from original app.py)
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

    # Update the title for fig2
    fig2.update_layout(xaxis_title="Date")

    # Modify the map (from original app.py)
    styled_site = site.copy()
    styled_site["color"] = styled_site["site_full"].apply(
        lambda x: "red" if x == site_chosen else "blue"
    )
    styled_site["size"] = styled_site["site_full"].apply(
        lambda x: 20 if x == site_chosen else 10
    )

    fig1 = go.Figure(
        go.Scattermapbox(
            lat=site["lat"],
            lon=site["lon"],
            mode="markers",
            text=site["site_full"],  # hover label
            customdata=site[["ecoli_conc", "ph", "turbidity", "WeekDate"]],
            hovertemplate=(
                "<b>%{text}</b><br>"
                "<i>E. coli</i>: %{customdata[0]}<br>"
                "pH: %{customdata[1]}<br>"
                "Turbidity: %{customdata[2]} NTU<br>"
                "Date: %{customdata[3]}<br>"
                "<extra></extra>"
            ),
            marker=dict(
                size=styled_site["size"],
                color=styled_site["color"],
            ),
        )
    )

    fig1.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=33.79, lon=-84.33),
            zoom=13,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        height=400,
    )
    
    return fig1, fig2

@callback(
    Output("sampling_sites", "value"),
    Input("map", "clickData")
)
def map_click(click_value):
    if click_value is None:
        return no_update
    
    try:
        clicked_lat = click_value["points"][0]["lat"]
        clicked_lon = click_value["points"][0]["lon"]
        
        # Find the corresponding site
        for _, row in site.iterrows():
            if abs(row["lat"] - clicked_lat) < 0.001 and abs(row["lon"] - clicked_lon) < 0.001:
                return row["site_full"]
    except (KeyError, IndexError):
        pass
    
    return no_update

@callback(
    Output("alert-banner", "children"),
    Input("alert-banner", "id")
)
def update_alert_banner(_):
    """Update the alert banner with current alerts"""
    alert_system.run_all_checks()
    
    if not alert_system.active_alerts:
        return dbc.Alert([
            html.I(className="fas fa-check-circle me-2"),
            "All water quality measurements are within EPA guidelines."
        ], color="success", className="mb-0")
    
    # Separate alerts by priority
    high_priority = [alert for alert in alert_system.active_alerts 
                    if alert.severity.value in ['critical', 'high']]
    low_priority = [alert for alert in alert_system.active_alerts 
                   if alert.severity.value in ['moderate', 'low']]
    
    alert_cards = []
    
    # Show all high priority alerts first
    for alert in high_priority:
        alert_cards.append(create_alert_card(alert))
    
    # If there are low priority alerts, add them to collapsible section
    if low_priority:
        low_priority_cards = []
        for alert in low_priority:
            low_priority_cards.append(create_alert_card(alert))
        
        # Add show more button and collapsible content
        alert_cards.append(
            html.Div([
                dbc.Button([
                    html.I(className="fas fa-chevron-down me-2"),
                    f"Show {len(low_priority)} additional alerts (low/moderate)"
                ], 
                id="show-more-alerts", 
                color="outline-secondary", 
                size="sm", 
                className="mb-2 w-100"),
                dbc.Collapse(
                    html.Div(low_priority_cards),
                    id="additional-alerts",
                    is_open=False
                )
            ])
        )
    
    return html.Div(alert_cards)

@callback(
    Output("chat-messages", "children"),
    Output("chat-input", "value"),
    Input("send-chat-btn", "n_clicks"),
    Input("quick-summary-btn", "n_clicks"),
    Input("quick-compare-btn", "n_clicks"),
    Input("quick-sites-btn", "n_clicks"), 
    Input("quick-alerts-btn", "n_clicks"),
    Input("chat-input", "n_submit"),
    State("chat-input", "value"),
    State("chat-messages", "children"),
    prevent_initial_call=True
)
def handle_chat(send_clicks, summary_clicks, compare_clicks, sites_clicks, alerts_clicks,
                n_submit, chat_input, chat_messages):
    ctx = callback_context
    if not ctx.triggered:
        return no_update, no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Initialize chat history
    if chat_messages is None:
        chat_messages = []
    
    # Handle quick buttons
    if trigger_id == "quick-summary-btn":
        user_message = "Can you provide a summary of the current water quality?"
    elif trigger_id == "quick-compare-btn":
        user_message = "Compare water quality across all monitoring sites"
    elif trigger_id == "quick-sites-btn":
        user_message = "Tell me about all the monitoring sites"
    elif trigger_id == "quick-alerts-btn":
        user_message = "What are the current water quality alerts?"
    elif trigger_id in ["send-chat-btn", "chat-input"] and chat_input:
        user_message = chat_input
    else:
        return no_update, no_update
    
    # Add user message
    chat_messages.append(
        dbc.Alert([
            html.Strong("You: "),
            user_message
        ], color="primary", className="mb-2")
    )
    
    # Get chatbot response
    try:
        response = chatbot.chat(user_message)
        formatted_response = format_chat_response(response)
        chat_messages.append(
            dbc.Alert([
                html.Strong("Assistant: "),
                html.Br(),
                formatted_response
            ], color="info", className="mb-2")
        )
    except Exception as e:
        chat_messages.append(
            dbc.Alert([
                html.Strong("Error: "),
                f"Sorry, I encountered an error: {str(e)}"
            ], color="danger", className="mb-2")
        )
    
    return chat_messages, ""

# Add the missing callback that was causing errors
@callback(
    Output("sampling_sites", "value", allow_duplicate=True),
    Input("chat-messages", "children"),
    prevent_initial_call=True,
)
def update_dashboard_from_chat(chat_messages):
    """Update dashboard based on chat context - simplified version"""
    return no_update

@callback(
    Output("sampling_sites", "value", allow_duplicate=True),
    Output("distance_alert", "children"),
    Output("distance_alert", "is_open"),
    Input("find_site_btn", "n_clicks"),
    State("address_input", "value"),
    prevent_initial_call=True
)
def find_nearest_site(n_clicks, address):
    if not n_clicks or not address or not GMAPS_KEY:
        return no_update, no_update, False
    
    try:
        # Geocode the address
        geocode_result = gmaps.geocode(address)
        if not geocode_result:
            return no_update, "Address not found. Please try a different address.", True
        
        user_location = geocode_result[0]['geometry']['location']
        user_lat, user_lon = user_location['lat'], user_location['lng']
        
        # Calculate distances to all sites
        distances = []
        for _, site_row in site_loc.iterrows():
            dist_result = gmaps.distance_matrix(
                origins=[(user_lat, user_lon)],
                destinations=[(site_row['lat'], site_row['lon'])],
                units="imperial"
            )
            
            if dist_result['rows'][0]['elements'][0]['status'] == 'OK':
                distance = dist_result['rows'][0]['elements'][0]['distance']['text']
                duration = dist_result['rows'][0]['elements'][0]['duration']['text']
                distances.append((site_row['site'], distance, duration))
        
        if distances:
            # Find closest site by parsing distance
            closest = min(distances, key=lambda x: float(x[1].split()[0]))
            site_name, distance, duration = closest
            
            # Map to full site name
            full_name = color_map.get(site_name, site_name)
            
            alert_message = [
                html.I(className="fas fa-map-marker-alt me-2"),
                f"Closest site: {full_name}",
                html.Br(),
                html.Small(f"Distance: {distance} (~{duration} drive)", className="text-muted")
            ]
            
            return full_name, alert_message, True
        else:
            return no_update, "Unable to calculate distances to monitoring sites.", True
            
    except Exception as e:
        return no_update, f"Error finding nearest site: {str(e)}", True

@callback(
    Output("additional-alerts", "is_open"),
    Output("show-more-alerts", "children"),
    Input("show-more-alerts", "n_clicks"),
    State("additional-alerts", "is_open"),
    prevent_initial_call=True
)
def toggle_additional_alerts(n_clicks, is_open):
    if n_clicks:
        new_state = not is_open
        if new_state:
            button_text = [
                html.I(className="fas fa-chevron-up me-2"),
                "Hide additional alerts"
            ]
        else:
            # Count low priority alerts for button text
            alert_system.run_all_checks()
            low_priority_count = len([alert for alert in alert_system.active_alerts 
                                    if alert.severity.value in ['moderate', 'low']])
            button_text = [
                html.I(className="fas fa-chevron-down me-2"),
                f"Show {low_priority_count} additional alerts (low/moderate)"
            ]
        return new_state, button_text
    return is_open, no_update

if __name__ == "__main__":
    app.run(debug=True)  # for local deployment