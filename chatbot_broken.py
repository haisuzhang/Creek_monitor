#!/usr/bin/env python
# coding: utf-8

import os
import pandas as pd
from typing import List, Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain.tools import BaseTool
from langchain.schema import BaseMessage, HumanMessage, AIMessage
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferWindowMemory
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.tools import tool
import json
from alerts import WaterQualityAlertSystem, AlertSeverity

class CreekDataTools:
    """Tools for interacting with creek monitoring data"""
    
    def __init__(self, df: pd.DataFrame, site_loc: pd.DataFrame):
        self.df = df
        self.site_loc = site_loc
        self.color_map = {
            "peav@oldb": "Peavine creek/Old briarcliff way",
            "peav@ndec": "Peavine creek/Oxford Rd NE", 
            "peav@vick": "Peavine creek/Chelsea Cir NE",
            "lull@lull": "Lullwater creek/Lullwater Rd NE",
        }
        # Initialize alert system
        self.alert_system = WaterQualityAlertSystem(df, site_loc)
    
    def get_site_info(self, site_name: str) -> str:
        """Get information about a specific monitoring site"""
        # Convert to lowercase for matching
        site_name_lower = site_name.lower()
        
        # Try to match by full name first
        if site_name_lower in [name.lower() for name in self.color_map.values()]:
            site_code = [k for k, v in self.color_map.items() if v.lower() == site_name_lower][0]
        elif site_name_lower in self.color_map:
            site_code = site_name_lower
        else:
            return f"Site '{site_name}' not found. Available sites: {list(self.color_map.values())}"
        
        # Get site data
        site_data = self.df[self.df['site'] == site_code]
        if site_data.empty:
            return f"No data available for site '{site_name}'"
        
        # Get location info
        loc_data = self.site_loc[self.site_loc['site'] == site_code]
        
        # Get latest readings
        latest = site_data.sort_values('WeekDate').iloc[-1]
        
        result = f"Site: {self.color_map[site_code]}\n"
        if not loc_data.empty:
            result += f"Location: Lat {loc_data.iloc[0]['lat']:.4f}, Lon {loc_data.iloc[0]['lon']:.4f}\n"
        result += f"Latest reading date: {latest['WeekDate']}\n"
        result += f"E. coli concentration: {latest['ecoli_conc']:.1f} MPN/100 mL\n"
        result += f"pH: {latest['ph']:.2f}\n"
        result += f"Turbidity: {latest['tubidity']:.1f} NTU\n"
        
        return result
    
    def get_water_quality_summary(self) -> str:
        """Get a summary of water quality across all monitoring sites"""
        # Get latest data for each site
        latest_data = []
        for site_code in self.color_map.keys():
            site_data = self.df[self.df['site'] == site_code]
            if not site_data.empty:
                latest = site_data.sort_values('WeekDate').iloc[-1]
                latest_data.append({
                    'site': self.color_map[site_code],
                    'ecoli': latest['ecoli_conc'],
                    'ph': latest['ph'],
                    'turbidity': latest['tubidity'],
                    'date': latest['WeekDate']
                })
        
        if not latest_data:
            return "No water quality data available."
        
        # Calculate summary statistics
        ecoli_values = [d['ecoli'] for d in latest_data]
        ph_values = [d['ph'] for d in latest_data]
        turbidity_values = [d['turbidity'] for d in latest_data]
        
        # EPA standard for E. coli is 1000 MPN/100 mL
        sites_above_standard = sum(1 for e in ecoli_values if e >= 1000)
        
        summary = "Water Quality Summary:\n\n"
        summary += f"Monitoring Sites: {len(latest_data)}\n"
        summary += f"Sites above E. coli standard (1000 MPN/100 mL): {sites_above_standard}\n\n"
        
        summary += "Latest Readings:\n"
        for data in latest_data:
            ecoli_status = "⚠️ ABOVE STANDARD" if data['ecoli'] >= 1000 else "✅ Below standard"
            summary += f"• {data['site']} ({data['date']}):\n"
            summary += f"  - E. coli: {data['ecoli']:.1f} MPN/100 mL {ecoli_status}\n"
            summary += f"  - pH: {data['ph']:.2f}\n"
            summary += f"  - Turbidity: {data['turbidity']:.1f} NTU\n\n"
        
        return summary
    
    def get_trends(self, site_name: str, measurement: str = "ecoli_conc", weeks: int = 8) -> str:
        """Get trends for a specific measurement at a site over the last N weeks"""
        # Convert site name
        site_name_lower = site_name.lower()
        if site_name_lower in [name.lower() for name in self.color_map.values()]:
            site_code = [k for k, v in self.color_map.items() if v.lower() == site_name_lower][0]
        elif site_name_lower in self.color_map:
            site_code = site_name_lower
        else:
            return f"Site '{site_name}' not found."
        
        # Get site data
        site_data = self.df[self.df['site'] == site_code].sort_values('WeekDate')
        if site_data.empty:
            return f"No data available for site '{site_name}'"
        
        # Get last N weeks
        recent_data = site_data.tail(weeks)
        
        if recent_data.empty:
            return f"No recent data available for site '{site_name}'"
        
        # Calculate trends
        values = recent_data[measurement].values
        dates = recent_data['WeekDate'].values
        
        if len(values) < 2:
            return f"Insufficient data for trend analysis at {site_name}"
        
        # Simple trend calculation
        first_value = values[0]
        last_value = values[-1]
        change = last_value - first_value
        change_percent = (change / first_value * 100) if first_value != 0 else 0
        
        # Measurement labels
        labels = {
            'ecoli_conc': 'E. coli concentration (MPN/100 mL)',
            'ph': 'pH',
            'tubidity': 'Turbidity (NTU)'
        }
        
        label = labels.get(measurement, measurement)
        
        result = f"Trend Analysis for {self.color_map[site_code]} - {label}\n"
        result += f"Period: {dates[0]} to {dates[-1]} ({len(values)} weeks)\n\n"
        
        result += f"First reading: {first_value:.2f}\n"
        result += f"Latest reading: {last_value:.2f}\n"
        result += f"Change: {change:+.2f} ({change_percent:+.1f}%)\n\n"
        
        # Trend interpretation
        if measurement == 'ecoli_conc':
            if change > 0:
                result += "⚠️ E. coli levels are increasing, which may indicate deteriorating water quality."
            elif change < 0:
                result += "✅ E. coli levels are decreasing, indicating improving water quality."
            else:
                result += "➡️ E. coli levels are stable."
        elif measurement == 'ph':
            if change > 0.5:
                result += "⚠️ pH is becoming more alkaline."
            elif change < -0.5:
                result += "⚠️ pH is becoming more acidic."
            else:
                result += "➡️ pH is relatively stable."
        elif measurement == 'tubidity':
            if change > 5:
                result += "⚠️ Turbidity is increasing, indicating more suspended particles."
            elif change < -5:
                result += "✅ Turbidity is decreasing, indicating clearer water."
            else:
                result += "➡️ Turbidity is relatively stable."
        
        return result
    
    def compare_sites(self, measurement: str = "ecoli_conc") -> str:
        """Compare the latest readings across all monitoring sites for a specific measurement"""
        # Get latest data for each site
        site_comparisons = []
        for site_code in self.color_map.keys():
            site_data = self.df[self.df['site'] == site_code]
            if not site_data.empty:
                latest = site_data.sort_values('WeekDate').iloc[-1]
                site_comparisons.append({
                    'site': self.color_map[site_code],
                    'value': latest[measurement],
                    'date': latest['WeekDate']
                })
        
        if not site_comparisons:
            return "No data available for comparison."
        
        # Sort by measurement value
        site_comparisons.sort(key=lambda x: x['value'], reverse=True)
        
        # Measurement labels
        labels = {
            'ecoli_conc': 'E. coli concentration (MPN/100 mL)',
            'ph': 'pH',
            'tubidity': 'Turbidity (NTU)'
        }
        
        label = labels.get(measurement, measurement)
        
        result = f"Site Comparison - {label}\n\n"
        
        for i, comp in enumerate(site_comparisons):
            rank = i + 1
            result += f"{rank}. {comp['site']}: {comp['value']:.2f} ({comp['date']})\n"
        
        # Add interpretation for E. coli
        if measurement == 'ecoli_conc':
            result += "\nEPA Standard: 1000 MPN/100 mL\n"
            above_standard = [c for c in site_comparisons if c['value'] >= 1000]
            if above_standard:
                result += f"⚠️ {len(above_standard)} site(s) above standard: "
                result += ", ".join([c['site'] for c in above_standard])
            else:
                result += "✅ All sites below EPA standard"
        
        return result
    
    def get_available_sites(self) -> str:
        """Get a list of all available monitoring sites"""
        sites = list(self.color_map.values())
        return f"Available monitoring sites:\n" + "\n".join([f"• {site}" for site in sites])
    
    def get_measurement_info(self, measurement: str) -> str:
        """Get information about what a specific measurement means and its standards"""
        info = {
            'ecoli_conc': {
                'name': 'E. coli concentration',
                'unit': 'MPN/100 mL',
                'description': 'Escherichia coli is a bacteria that indicates fecal contamination in water.',
                'epa_standard': '1000 MPN/100 mL',
                'health_risk': 'High levels indicate potential health risks from waterborne pathogens.',
                'interpretation': 'Lower values indicate cleaner water. Values above 1000 MPN/100 mL exceed EPA standards.'
            },
            'ph': {
                'name': 'pH',
                'unit': 'pH units',
                'description': 'pH measures how acidic or basic the water is on a scale of 0-14.',
                'epa_standard': '6.5-8.5',
                'health_risk': 'Extreme pH values can harm aquatic life and indicate pollution.',
                'interpretation': '7.0 is neutral. Values below 7 are acidic, above 7 are basic. Natural streams typically range from 6.5-8.5.'
            },
            'tubidity': {
                'name': 'Turbidity',
                'unit': 'NTU (Nephelometric Turbidity Units)',
                'description': 'Turbidity measures water clarity and the amount of suspended particles.',
                'epa_standard': 'Varies by water body type',
                'health_risk': 'High turbidity can reduce light penetration and affect aquatic life.',
                'interpretation': 'Lower values indicate clearer water. Values above 10 NTU may indicate runoff or erosion.'
            }
        }
        
        if measurement not in info:
            return f"Measurement '{measurement}' not found. Available measurements: {list(info.keys())}"
        
        data = info[measurement]
        result = f"{data['name']} ({data['unit']})\n\n"
        result += f"Description: {data['description']}\n"
        result += f"EPA Standard: {data['epa_standard']}\n"
        result += f"Health Risk: {data['health_risk']}\n"
        result += f"Interpretation: {data['interpretation']}"
        
        return result
    
    def get_current_alerts(self) -> str:
        """Get current water quality alerts and violations"""
        # Run alert checks
        all_alerts = self.alert_system.run_all_checks()
        
        if not self.alert_system.active_alerts:
            return "✅ No current water quality alerts. All monitoring sites are within acceptable parameters."
        
        # Get alert summary
        summary = self.alert_system.get_alert_summary()
        
        result = f"🚨 Current Water Quality Alerts ({summary['total_alerts']} active)\n\n"
        
        # Group alerts by severity
        critical_alerts = self.alert_system.get_alerts_by_severity(AlertSeverity.CRITICAL)
        high_alerts = self.alert_system.get_alerts_by_severity(AlertSeverity.HIGH)
        
        if critical_alerts:
            result += f"🚨 CRITICAL ALERTS ({len(critical_alerts)}):\\n"
            for alert in critical_alerts:
                result += f"• {alert.message}\n"
                result += f"  Recommendation: {alert.recommendation}\n"
                result += f"  Date: {alert.date}\n\n"
        
        if high_alerts:
            result += f"⚠️ HIGH PRIORITY ALERTS ({len(high_alerts)}):\n"
            for alert in high_alerts:
                result += f"• {alert.message}\n"
                result += f"  Recommendation: {alert.recommendation}\n"
                result += f"  Date: {alert.date}\n\n"
        
        # Show other alerts summary
        other_count = summary['total_alerts'] - len(critical_alerts) - len(high_alerts)
        if other_count > 0:
            result += f"ℹ️ Other alerts: {other_count} moderate/low priority alerts\n"
        
        result += f"\nSites affected: {summary['sites_affected']} out of 4 monitoring locations"
        
        return result
    
    def get_alert_details_for_site(self, site_name: str) -> str:
        \"\"\"Get specific alert details for a monitoring site\"\"\"
        # Convert site name to code
        site_name_lower = site_name.lower()
        if site_name_lower in [name.lower() for name in self.color_map.values()]:
            site_code = [k for k, v in self.color_map.items() if v.lower() == site_name_lower][0]
        elif site_name_lower in self.color_map:
            site_code = site_name_lower
        else:
            return f"Site '{site_name}' not found. Available sites: {list(self.color_map.values())}"
        
        # Run alert checks
        self.alert_system.run_all_checks()
        
        # Get alerts for this site
        site_alerts = self.alert_system.get_alerts_by_site(site_code)
        
        if not site_alerts:
            return f"✅ No current alerts for {self.color_map[site_code]}. Water quality parameters are within acceptable ranges."
        
        result = f"🚨 Water Quality Alerts for {self.color_map[site_code]}:\n\n"
        
        for alert in site_alerts:
            severity_icon = {'critical': '🚨', 'high': '⚠️', 'moderate': 'ℹ️', 'low': '🔍'}.get(alert.severity.value, 'ℹ️')
            result += f"{severity_icon} {alert.severity.value.upper()}: {alert.message}\n"
            result += f"Parameter: {alert.parameter}\n"
            result += f"Value: {alert.value} (Threshold: {alert.threshold})\n"
            result += f"Recommendation: {alert.recommendation}\n"
            result += f"Date: {alert.date}\n\n"
        
        return result
    
    def check_epa_compliance(self) -> str:
        \"\"\"Check EPA compliance status across all sites\"\"\"
        # Run alert checks
        self.alert_system.run_all_checks()
        
        result = \"EPA Compliance Status Report:\n\n\"
        
        # Check E. coli compliance
        ecoli_violations = [alert for alert in self.alert_system.active_alerts if alert.alert_type.value == 'ecoli_violation']
        
        result += f"E. coli Compliance (EPA Recreational Standard: 126 MPN/100mL):\n"
        if ecoli_violations:
            result += f"❌ {len(ecoli_violations)} site(s) in violation:\n"
            for alert in ecoli_violations:
                result += f"  • {alert.site_name}: {alert.value:.1f} MPN/100mL\n"
        else:
            result += \"✅ All sites compliant with E. coli standards\n\"
        
        result += "
\"
        
        # Check pH compliance
        ph_violations = [alert for alert in self.alert_system.active_alerts if alert.alert_type.value == 'ph_violation']
        
        result += f"pH Compliance (Acceptable Range: 6.5-8.5):\n"
        if ph_violations:
            result += f"❌ {len(ph_violations)} site(s) outside acceptable range:\n"
            for alert in ph_violations:
                result += f"  • {alert.site_name}: {alert.value:.2f}\n"
        else:
            result += \"✅ All sites within acceptable pH range\n\"
        
        result += "
\"
        
        # Check turbidity
        turbidity_violations = [alert for alert in self.alert_system.active_alerts if alert.alert_type.value == 'turbidity_violation']
        
        result += f"Turbidity Status (EPA Drinking Water Standard: 1.0 NTU):\n"
        if turbidity_violations:
            result += f"⚠️ {len(turbidity_violations)} site(s) above standard:\n"
            for alert in turbidity_violations:
                result += f"  • {alert.site_name}: {alert.value:.1f} NTU\n"
        else:
            result += \"✅ All sites within turbidity guidelines\n\"
        
        # Overall compliance
        total_violations = len(ecoli_violations) + len(ph_violations) + len(turbidity_violations)
        result += f"\nOverall Status: {4 - len(set(alert.site_code for alert in self.alert_system.active_alerts))}/4 sites fully compliant"
        
        return result

class CreekChatbot:
    """Main chatbot class for creek monitoring data"""
    
    def __init__(self, df: pd.DataFrame, site_loc: pd.DataFrame):
        self.df = df
        self.site_loc = site_loc
        self.tools = CreekDataTools(df, site_loc)
        
        # Initialize OpenAI model
        self.llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            temperature=0.1,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create standalone tool functions
        def get_site_info_tool(site_name: str) -> str:
            """Get information about a specific monitoring site including location and latest readings"""
            return self.tools.get_site_info(site_name)
        
        def get_water_quality_summary_tool() -> str:
            """Get a summary of water quality across all monitoring sites with EPA compliance status"""
            return self.tools.get_water_quality_summary()
        
        def get_trends_tool(site_name: str, measurement: str = "ecoli_conc", weeks: int = 8) -> str:
            """Get trends for a specific measurement at a site over the last N weeks"""
            return self.tools.get_trends(site_name, measurement, weeks)
        
        def compare_sites_tool(measurement: str = "ecoli_conc") -> str:
            """Compare the latest readings across all monitoring sites for a specific measurement"""
            return self.tools.compare_sites(measurement)
        
        def get_available_sites_tool() -> str:
            """Get a list of all available monitoring sites"""
            return self.tools.get_available_sites()
        
        def get_measurement_info_tool(measurement: str) -> str:
            """Get information about what a specific measurement means and its standards"""
            return self.tools.get_measurement_info(measurement)
        
        def get_current_alerts_tool() -> str:
            """Get current water quality alerts and violations across all monitoring sites"""
            return self.tools.get_current_alerts()
        
        def get_alert_details_for_site_tool(site_name: str) -> str:
            """Get specific alert details for a monitoring site"""
            return self.tools.get_alert_details_for_site(site_name)
        
        def check_epa_compliance_tool() -> str:
            """Check EPA compliance status across all sites"""
            return self.tools.check_epa_compliance()
        
        # Create tools list with proper decorators
        self.tool_list = [
            tool(get_site_info_tool),
            tool(get_water_quality_summary_tool),
            tool(get_trends_tool),
            tool(compare_sites_tool),
            tool(get_available_sites_tool),
            tool(get_measurement_info_tool),
            tool(get_current_alerts_tool),
            tool(get_alert_details_for_site_tool),
            tool(check_epa_compliance_tool)
        ]
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant for a creek monitoring dashboard. You help users understand water quality data from various monitoring sites.

You have access to data about:
- E. coli concentrations (EPA standard: 126 MPN/100 mL for recreational water, 1000 MPN/100 mL traditional standard)
- pH levels (EPA standard: 6.5-8.5)
- Turbidity measurements (NTU)

Available monitoring sites:
- Peavine creek/Old briarcliff way
- Peavine creek/Oxford Rd NE  
- Peavine creek/Chelsea Cir NE
- Lullwater creek/Lullwater Rd NE

You also have access to a comprehensive alert system that monitors EPA threshold violations:
- Critical alerts for severe violations (immediate health risk)
- High priority alerts for significant violations
- Moderate/low alerts for minor concerns
- Missing data alerts

Use the available tools to answer questions about water quality, trends, site comparisons, and current alerts. Be helpful and informative, and explain what the data means in terms of water quality and potential health implications.

When users ask about alerts, violations, or EPA compliance, use the alert tools to provide current status and recommendations.

If a user asks about a specific site or measurement, use the appropriate tool to get current data."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # Create agent
        self.agent = create_openai_tools_agent(self.llm, self.tool_list, self.prompt)
        
        # Create memory
        self.memory = ConversationBufferWindowMemory(
            memory_key="chat_history",
            return_messages=True,
            k=10
        )
        
        # Create agent executor
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tool_list,
            memory=self.memory,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def chat(self, message: str) -> str:
        """Send a message to the chatbot and get a response"""
        try:
            response = self.agent_executor.invoke({"input": message})
            return response["output"]
        except Exception as e:
            return f"I encountered an error: {str(e)}. Please try rephrasing your question."
    
    def get_chat_history(self) -> List[Dict[str, str]]:
        """Get the chat history for display"""
        history = []
        messages = self.memory.chat_memory.messages
        
        for i in range(0, len(messages), 2):
            if i + 1 < len(messages):
                history.append({
                    "user": messages[i].content,
                    "assistant": messages[i + 1].content
                })
        
        return history 