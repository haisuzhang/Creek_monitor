# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Architecture Overview

This is a Creek Water Quality Monitoring Dashboard built with:
- **Dash/Plotly**: Main web framework for the dashboard (app.py:1-50)
- **LangChain + OpenAI**: Powers the integrated chatbot for intelligent data analysis (chatbot.py:1-50)
- **Pandas**: Data processing and analysis of water quality measurements
- **Bootstrap**: UI components via dash-bootstrap-components

### Core Components

1. **app.py**: Main Dash application with water quality visualization dashboard
2. **chatbot.py**: LangChain-based chatbot with custom tools for creek data analysis
   - `CreekDataTools` class provides site information, water quality summaries, and trend analysis
   - Uses OpenAI GPT-3.5-turbo with conversation memory
3. **data/**: Contains CSV files with water quality measurements and site locations
   - `Updated results.csv`: Main water quality data (E. coli, pH, turbidity)
   - `Site_loc.csv`: Monitoring site location information

### Site Mapping
The system tracks 4 creek monitoring sites with coded identifiers:
- `peav@oldb`: Peavine creek/Old briarcliff way
- `peav@ndec`: Peavine creek/Oxford Rd NE  
- `peav@vick`: Peavine creek/Chelsea Cir NE
- `lull@lull`: Lullwater creek/Lullwater Rd NE

## Development Commands

### Installation and Setup
```bash
pip install -r requirements.txt
```

### Testing
```bash
python test_chatbot.py  # Test chatbot functionality
```

### Running the Application
```bash
python app.py  # Start the dashboard locally
```

### Deployment Build
```bash
bash build.sh  # Render deployment build script
```

## Environment Variables

Required environment variables:
- `OPENAI_API_KEY`: OpenAI API key for chatbot functionality
- `MAPBOX_TOKEN`: For map visualizations (optional)
- `GMAPS_KEY`: Google Maps API key (optional)
- `GITHUB_USERNAME` and `GITHUB_TOKEN`: For data access (optional)

## Data Integration

The chatbot has access to:
- Real-time water quality data (E. coli, pH, turbidity measurements)
- Site location and metadata
- EPA standards for compliance checking
- Historical trend analysis capabilities

## Chatbot Tools

The `CreekDataTools` class in chatbot.py provides these tools:
- `get_site_info()`: Information about specific monitoring sites
- `get_water_quality_summary()`: Overview of all sites' current status
- `compare_sites()`: Cross-site comparisons of water quality metrics
- `get_trend_analysis()`: Historical trend analysis for specific parameters

## Alert System

**NEW**: Comprehensive EPA threshold alert system (alerts.py):

### Alert Types and Thresholds:
- **E. coli violations**: 126 MPN/100mL (EPA recreational), 400, 1000, 2400 MPN/100mL (severity levels)
- **pH violations**: Outside 6.5-8.5 range (moderate), outside 6.0-9.0 range (severe)  
- **Turbidity violations**: >1.0 NTU (EPA drinking water), >4.0, >10.0, >25.0 NTU (severity levels)
- **Missing data alerts**: When critical parameters are unavailable

### Alert Severity Levels:
- **Critical**: Immediate health risk, severe violations
- **High**: Significant violations requiring attention  
- **Moderate**: Notable concerns, monitor closely
- **Low**: Minor violations, informational

### Dashboard Integration:
- Real-time alert banner showing current violations
- Color-coded alert cards with severity indicators
- Alert summary badges and detailed recommendations
- Automatic refresh on data updates

### Chatbot Integration:
New chatbot tools for alert management:
- `get_current_alerts()`: Get all active alerts
- `get_alert_details_for_site(site_name)`: Site-specific alerts
- `check_epa_compliance()`: Full EPA compliance report

### Testing:
- Run `python test_alerts_simple.py` to test alert detection
- Alert system automatically detects violations in current data
- Integrated with existing dashboard refresh cycle

## Deployment

Configured for Render deployment with:
- Python 3.11.18 runtime
- Gunicorn WSGI server
- Build script for dependency installation