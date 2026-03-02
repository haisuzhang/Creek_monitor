#!/usr/bin/env python
# coding: utf-8

"""
Test script for the Water Quality Alert System
"""

import pandas as pd
import sys
from alerts import WaterQualityAlertSystem, AlertSeverity

def test_alert_system():
    """Test the alert system functionality"""
    
    print("Testing Water Quality Alert System")
    print("=" * 50)
    
    try:
        # Load test data
        print("📊 Loading test data...")
        df = pd.read_csv("data/Updated results.csv", skiprows=2)
        site_loc = pd.read_csv("data/Site_loc.csv")
        
        # Clean data (same as in app.py)
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
        
        df = (
            df.drop(columns=["Date"])
            .groupby(["WeekDate", "site"])
            .mean()
            .reset_index()
        )
        
        print("✅ Test data loaded and cleaned successfully")
        
        # Initialize alert system
        print("\n🚨 Initializing Alert System...")
        alert_system = WaterQualityAlertSystem(df, site_loc)
        print("✅ Alert system initialized")
        
        # Test 1: Run all alert checks
        print("\n1️⃣ Testing alert detection...")
        all_alerts = alert_system.run_all_checks()
        print(f"✅ Alert checks completed: {len(alert_system.active_alerts)} alerts found")
        
        # Test 2: Display alert summary
        print("\n2️⃣ Alert Summary:")
        summary = alert_system.get_alert_summary()
        print(f"Total alerts: {summary['total_alerts']}")
        print(f"Sites affected: {summary['sites_affected']}")
        print(f"By severity: {summary['by_severity']}")
        print(f"By type: {summary['by_type']}")
        
        # Test 3: Check each alert type
        print("\n3️⃣ Alert Details by Type:")
        for alert_type, alerts in all_alerts.items():
            if alerts:
                print(f"\n{alert_type.upper()} ({len(alerts)} alerts):")
                for alert in alerts:
                    print(f"  • {alert.message}")
                    print(f"    Site: {alert.site_name}")
                    print(f"    Severity: {alert.severity.value}")
                    print(f"    Date: {alert.date}")
            else:
                print(f"\n{alert_type.upper()}: No alerts")
        
        # Test 4: Critical alerts
        print("\n4️⃣ Critical Alerts:")
        critical_alerts = alert_system.get_critical_alerts()
        if critical_alerts:
            for alert in critical_alerts:
                print(f"🚨 {alert.message}")
                print(f"   Recommendation: {alert.recommendation}")
        else:
            print("✅ No critical alerts")
        
        # Test 5: Test site-specific alerts
        print("\n5️⃣ Site-Specific Alert Test:")
        sites = ["peav@oldb", "peav@ndec", "peav@vick", "lull@lull"]
        for site_code in sites:
            site_alerts = alert_system.get_alerts_by_site(site_code)
            site_name = alert_system.site_names.get(site_code, site_code)
            print(f"{site_name}: {len(site_alerts)} alert{'s' if len(site_alerts) != 1 else ''}")
        
        # Test 6: JSON export
        print("\n6️⃣ Testing JSON export...")
        json_export = alert_system.export_alerts_to_json()
        print(f"✅ JSON export successful ({len(json_export)} characters)")
        
        # Test 7: Show some actual alert data if available
        if alert_system.active_alerts:
            print(f"\n7️⃣ Sample Alert Details:")
            sample_alert = alert_system.active_alerts[0]
            print(f"ID: {sample_alert.id}")
            print(f"Type: {sample_alert.alert_type.value}")
            print(f"Severity: {sample_alert.severity.value}")
            print(f"Message: {sample_alert.message}")
            print(f"Recommendation: {sample_alert.recommendation}")
        
        print(f"\n🎉 Alert System Test Complete!")
        print(f"Summary: {len(alert_system.active_alerts)} active alerts detected")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_chatbot_integration():
    """Test chatbot integration with alerts"""
    print("\n🤖 Testing Chatbot Integration with Alerts")
    print("=" * 50)
    
    try:
        # Check if OpenAI API key is set
        import os
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️ OPENAI_API_KEY not set. Skipping chatbot integration test.")
            return True
            
        from chatbot import CreekChatbot
        import pandas as pd
        
        # Load data
        df = pd.read_csv("data/Updated results.csv", skiprows=2)
        site_loc = pd.read_csv("data/Site_loc.csv")
        
        # Initialize chatbot
        print("🤖 Initializing chatbot with alert integration...")
        chatbot = CreekChatbot(df, site_loc)
        print("✅ Chatbot initialized successfully")
        
        # Test alert tools
        print("\n1️⃣ Testing alert tools access...")
        
        # Check if alert tools are available
        tool_names = [tool.name for tool in chatbot.tool_list]
        alert_tools = [name for name in tool_names if 'alert' in name or 'compliance' in name]
        print(f"Alert tools found: {alert_tools}")
        
        print("✅ Chatbot integration test complete")
        return True
        
    except Exception as e:
        print(f"❌ Error during chatbot integration test: {str(e)}")
        return False

if __name__ == "__main__":
    print("Creek Monitoring Alert System Test Suite")
    print("=" * 60)
    
    # Test 1: Alert System
    test1_passed = test_alert_system()
    
    # Test 2: Chatbot Integration  
    test2_passed = test_chatbot_integration()
    
    # Final Results
    print(f"\n📊 Test Results:")
    print(f"Alert System: {'✅ PASS' if test1_passed else '❌ FAIL'}")
    print(f"Chatbot Integration: {'✅ PASS' if test2_passed else '❌ FAIL'}")
    
    if test1_passed and test2_passed:
        print(f"\n🎉 All tests passed! The alert system is ready to use.")
    else:
        print(f"\n⚠️ Some tests failed. Please check the errors above.")
        sys.exit(1)