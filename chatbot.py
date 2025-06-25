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
        
        # Create tools list with proper decorators
        self.tool_list = [
            tool(get_site_info_tool),
            tool(get_water_quality_summary_tool),
            tool(get_trends_tool),
            tool(compare_sites_tool),
            tool(get_available_sites_tool),
            tool(get_measurement_info_tool)
        ]
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant for a creek monitoring dashboard. You help users understand water quality data from various monitoring sites.

You have access to data about:
- E. coli concentrations (EPA standard: 1000 MPN/100 mL)
- pH levels (EPA standard: 6.5-8.5)
- Turbidity measurements (NTU)

Available monitoring sites:
- Peavine creek/Old briarcliff way
- Peavine creek/Oxford Rd NE  
- Peavine creek/Chelsea Cir NE
- Lullwater creek/Lullwater Rd NE

Use the available tools to answer questions about water quality, trends, and site comparisons. Be helpful and informative, and explain what the data means in terms of water quality and potential health implications.

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