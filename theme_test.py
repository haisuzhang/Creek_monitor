#!/usr/bin/env python
"""
Test different Bootstrap themes for mobile responsiveness and aesthetics
"""

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# Available themes to test - top recommendations for data dashboards
RECOMMENDED_THEMES = {
    'BOOTSTRAP': {
        'theme': dbc.themes.BOOTSTRAP,
        'pros': ['Clean & modern', 'Excellent mobile support', 'Bootstrap 5 native', 'Great contrast'],
        'best_for': 'Professional dashboards, maximum compatibility'
    },
    'LUX': {
        'theme': dbc.themes.LUX,
        'pros': ['Premium look', 'Great typography', 'Excellent readability', 'Mobile optimized'],
        'best_for': 'Data-rich applications, scientific dashboards'
    },
    'PULSE': {
        'theme': dbc.themes.PULSE,
        'pros': ['Modern colors', 'Great for alerts', 'Mobile friendly', 'Good contrast'],
        'best_for': 'Monitoring dashboards, alert systems'
    },
    'COSMO': {
        'theme': dbc.themes.COSMO,
        'pros': ['Clean design', 'Excellent mobile', 'Good spacing', 'Professional'],
        'best_for': 'Business dashboards, clean layouts'
    },
    'CERULEAN': {
        'theme': dbc.themes.CERULEAN,
        'pros': ['Water-themed colors', 'Great for env data', 'Mobile ready', 'Calm aesthetic'],
        'best_for': 'Environmental monitoring, water quality data'
    }
}

def create_theme_demo(theme_name, theme_info):
    """Create a demo layout for testing themes"""
    return dbc.Container([
        html.H1(f"{theme_name} Theme Demo", className="text-center mb-4"),
        
        # Alert demo
        dbc.Alert([
            html.H4("🚨 Water Quality Alert", className="alert-heading"),
            html.P("Critical E. coli violation detected at monitoring site."),
            html.Hr(),
            html.P("Immediate action required.", className="mb-0")
        ], color="danger", className="mb-4"),
        
        # Cards demo
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📊 Data Visualization"),
                    dbc.CardBody([
                        html.H5("Site Measurements", className="card-title"),
                        html.P("Charts and graphs display here."),
                        dbc.Button("View Details", color="primary", size="sm")
                    ])
                ])
            ], width=12, md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("🤖 Chat Assistant"),
                    dbc.CardBody([
                        html.H5("AI Assistant", className="card-title"),
                        html.P("Interactive chatbot interface."),
                        dbc.Button("Start Chat", color="info", size="sm")
                    ])
                ])
            ], width=12, md=6)
        ], className="g-3 mb-4"),
        
        # Form controls demo  
        dbc.Card([
            dbc.CardBody([
                html.H5("Interactive Controls"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Monitoring Site:"),
                        dcc.Dropdown(
                            options=[
                                {"label": "Peavine Creek - Old Briarcliff", "value": "site1"},
                                {"label": "Peavine Creek - Oxford Rd", "value": "site2"}
                            ],
                            value="site1",
                            className="mb-3"
                        )
                    ], width=12, md=6),
                    dbc.Col([
                        html.Label("Measurement:"),
                        dcc.RadioItems(
                            options=[
                                {"label": "E. coli", "value": "ecoli"},
                                {"label": "pH", "value": "ph"},
                                {"label": "Turbidity", "value": "turbidity"}
                            ],
                            value="ecoli",
                            className="mb-3",
                            labelStyle={"display": "block", "margin": "5px 0"}
                        )
                    ], width=12, md=6)
                ])
            ])
        ]),
        
        html.Hr(),
        html.P(f"Pros: {', '.join(theme_info['pros'])}", className="text-muted"),
        html.P(f"Best for: {theme_info['best_for']}", className="text-muted small")
        
    ], fluid=True, className="py-4")

print("=== THEME SELECTION ANALYSIS ===")
print()

for theme_name, theme_info in RECOMMENDED_THEMES.items():
    print(f"🎨 {theme_name}")
    print(f"   Pros: {', '.join(theme_info['pros'])}")
    print(f"   Best for: {theme_info['best_for']}")
    print()

print("🏆 RECOMMENDATION: LUX or CERULEAN")
print("   - LUX: Best overall for data visualization")
print("   - CERULEAN: Perfect thematic match for water quality monitoring")
print("   - Both have excellent mobile responsiveness")