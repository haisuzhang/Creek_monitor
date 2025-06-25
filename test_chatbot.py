#!/usr/bin/env python
# coding: utf-8

"""
Test script for the Creek Monitoring Chatbot
"""

import os
import pandas as pd
from chatbot import CreekChatbot

def test_chatbot():
    """Test the chatbot functionality"""
    
    # Check if OpenAI API key is set
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY environment variable not set!")
        print("Please set your OpenAI API key before running the chatbot.")
        return False
    
    try:
        # Load test data (you'll need to adjust paths based on your setup)
        print("📊 Loading test data...")
        
        # Try to load the data files
        try:
            df = pd.read_csv("data/Updated results.csv", skiprows=2)
            site_loc = pd.read_csv("data/Site_loc.csv")
            print("✅ Data files loaded successfully")
        except FileNotFoundError:
            print("❌ Data files not found. Please ensure the data files are in the correct location.")
            return False
        
        # Initialize chatbot
        print("🤖 Initializing chatbot...")
        chatbot = CreekChatbot(df, site_loc)
        print("✅ Chatbot initialized successfully")
        
        # Test basic functionality
        print("\n🧪 Testing chatbot responses...")
        
        # Test 1: Get available sites
        print("\n1. Testing 'get available sites'...")
        response = chatbot.chat("What monitoring sites are available?")
        print(f"Response: {response[:200]}...")
        
        # Test 2: Get water quality summary
        print("\n2. Testing 'water quality summary'...")
        response = chatbot.chat("Give me a water quality summary")
        print(f"Response: {response[:200]}...")
        
        # Test 3: Get site info
        print("\n3. Testing 'site info'...")
        response = chatbot.chat("Tell me about Peavine creek/Old briarcliff way")
        print(f"Response: {response[:200]}...")
        
        print("\n✅ All tests completed successfully!")
        print("\n🎉 The chatbot is ready to use in your Dash app!")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

if __name__ == "__main__":
    test_chatbot() 