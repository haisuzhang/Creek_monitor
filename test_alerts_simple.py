#!/usr/bin/env python
# coding: utf-8

"""
Simple test script for the Water Quality Alert System (no emojis)
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
        print("Loading test data...")
        df = pd.read_csv("data/Updated results.csv", skiprows=2)
        site_loc = pd.read_csv("data/Site_loc.csv")
        
        # Clean data (same as in app.py)
        df = df[["Date", "site", "tot_coli_conc", "ecoli_conc", "ph", "tubidity"]]
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
        df["tubidity"] = pd.to_numeric(df["tubidity"], errors="coerce")
        
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
        
        print("SUCCESS: Test data loaded and cleaned successfully")
        print(f"Data shape: {df.shape}")
        print(f"Latest data from: {df['WeekDate'].max()}")
        
        # Initialize alert system
        print("\nInitializing Alert System...")
        alert_system = WaterQualityAlertSystem(df, site_loc)
        print("SUCCESS: Alert system initialized")
        
        # Test 1: Run all alert checks
        print("\n1. Testing alert detection...")
        all_alerts = alert_system.run_all_checks()
        print(f"SUCCESS: Alert checks completed: {len(alert_system.active_alerts)} alerts found")
        
        # Test 2: Display alert summary
        print("\n2. Alert Summary:")
        summary = alert_system.get_alert_summary()
        print(f"Total alerts: {summary['total_alerts']}")
        print(f"Sites affected: {summary['sites_affected']}")
        print(f"By severity: {summary['by_severity']}")
        print(f"By type: {summary['by_type']}")
        
        # Test 3: Check each alert type
        print("\n3. Alert Details by Type:")
        for alert_type, alerts in all_alerts.items():
            if alerts:
                print(f"\n{alert_type.upper()} ({len(alerts)} alerts):")
                for alert in alerts:
                    print(f"  * {alert.message}")
                    print(f"    Site: {alert.site_name}")
                    print(f"    Severity: {alert.severity.value}")
                    print(f"    Date: {alert.date}")
            else:
                print(f"\n{alert_type.upper()}: No alerts")
        
        # Test 4: Critical alerts
        print("\n4. Critical Alerts:")
        critical_alerts = alert_system.get_critical_alerts()
        if critical_alerts:
            for alert in critical_alerts:
                print(f"CRITICAL: {alert.message}")
                print(f"   Recommendation: {alert.recommendation}")
        else:
            print("No critical alerts")
        
        # Test 5: Test site-specific alerts
        print("\n5. Site-Specific Alert Test:")
        sites = ["peav@oldb", "peav@ndec", "peav@vick", "lull@lull"]
        for site_code in sites:
            site_alerts = alert_system.get_alerts_by_site(site_code)
            site_name = alert_system.site_names.get(site_code, site_code)
            print(f"{site_name}: {len(site_alerts)} alert(s)")
        
        # Test 6: Show latest data sample
        print(f"\n6. Latest Data Sample (last 3 entries):")
        latest_data = df.sort_values('WeekDate').tail(3)
        for _, row in latest_data.iterrows():
            print(f"  {row['site']}: E.coli={row['ecoli_conc']}, pH={row['ph']}, Turbidity={row['tubidity']}")
        
        print(f"\nSUCCESS: Alert System Test Complete!")
        print(f"Summary: {len(alert_system.active_alerts)} active alerts detected")
        
        return True
        
    except Exception as e:
        print(f"ERROR during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Creek Monitoring Alert System Test Suite")
    print("=" * 60)
    
    # Test 1: Alert System
    test1_passed = test_alert_system()
    
    # Final Results
    print(f"\nTest Results:")
    print(f"Alert System: {'PASS' if test1_passed else 'FAIL'}")
    
    if test1_passed:
        print(f"\nSUCCESS: Alert system is working correctly!")
    else:
        print(f"\nFAILED: Some tests failed. Please check the errors above.")
        sys.exit(1)