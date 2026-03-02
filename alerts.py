#!/usr/bin/env python
# coding: utf-8

"""
EPA Water Quality Alert System for Creek Monitoring Dashboard

This module provides comprehensive alert detection and management for water quality violations
based on EPA recreational water quality standards and drinking water regulations.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import json


class AlertSeverity(Enum):
    """Alert severity levels based on threshold violations"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class AlertType(Enum):
    """Types of water quality alerts"""
    ECOLI_VIOLATION = "ecoli_violation"
    PH_VIOLATION = "ph_violation"
    TURBIDITY_VIOLATION = "turbidity_violation"
    MISSING_DATA = "missing_data"
    TREND_WARNING = "trend_warning"


@dataclass
class Alert:
    """Water quality alert data structure"""
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    site_code: str
    site_name: str
    parameter: str
    value: float
    threshold: float
    date: str
    message: str
    recommendation: str
    is_active: bool = True
    acknowledged: bool = False
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'site_code': self.site_code,
            'site_name': self.site_name,
            'parameter': self.parameter,
            'value': self.value,
            'threshold': self.threshold,
            'date': self.date,
            'message': self.message,
            'recommendation': self.recommendation,
            'is_active': self.is_active,
            'acknowledged': self.acknowledged,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WaterQualityAlertSystem:
    """Comprehensive alert system for water quality monitoring"""
    
    # EPA Recreational Water Quality Standards
    EPA_STANDARDS = {
        'ecoli': {
            'safe': 126,  # EPA RWQC 2012: 126 MPN/100mL for freshwater
            'moderate': 400,  # Custom threshold for moderate concern
            'high': 1000,  # Traditional E. coli standard
            'critical': 2400  # Very high contamination
        },
        'ph': {
            'min_safe': 6.5,
            'max_safe': 8.5,
            'min_moderate': 6.0,
            'max_moderate': 9.0
        },
        'turbidity': {
            'safe': 1.0,  # EPA drinking water standard: 1 NTU
            'moderate': 4.0,  # Noticeable cloudiness
            'high': 10.0,  # High turbidity affecting aesthetics
            'critical': 25.0  # Very poor water quality
        }
    }
    
    def __init__(self, df: pd.DataFrame, site_loc: pd.DataFrame):
        self.df = df
        self.site_loc = site_loc
        self.active_alerts: List[Alert] = []
        self.alert_history: List[Alert] = []
        
        # Site name mapping
        self.site_names = {
            "peav@oldb": "Peavine creek/Old briarcliff way",
            "peav@ndec": "Peavine creek/Oxford Rd NE", 
            "peav@vick": "Peavine creek/Chelsea Cir NE",
            "lull@lull": "Lullwater creek/Lullwater Rd NE",
        }

    def generate_alert_id(self, site_code: str, alert_type: AlertType, date: str) -> str:
        """Generate unique alert ID"""
        return f"{alert_type.value}_{site_code}_{date}_{datetime.now().strftime('%H%M%S')}"

    def check_ecoli_violations(self) -> List[Alert]:
        """Check for E. coli violations across all sites"""
        alerts = []
        
        for site_code, site_name in self.site_names.items():
            site_data = self.df[self.df['site'] == site_code].copy()
            if site_data.empty:
                continue
                
            # Get latest reading
            date_col = 'WeekDate' if 'WeekDate' in site_data.columns else 'Date'
            site_data = site_data.sort_values(date_col)
            latest = site_data.iloc[-1]
            
            # Skip if no E. coli data
            if pd.isna(latest['ecoli_conc']) or latest['ecoli_conc'] == 'N/A':
                continue
            
            # Handle string values like ">2419.6"
            ecoli_value = latest['ecoli_conc']
            if isinstance(ecoli_value, str):
                if ecoli_value.startswith('>'):
                    ecoli_value = float(ecoli_value[1:])
                else:
                    try:
                        ecoli_value = float(ecoli_value)
                    except ValueError:
                        continue
            
            # Determine severity and create alert if violation
            if ecoli_value >= self.EPA_STANDARDS['ecoli']['critical']:
                severity = AlertSeverity.CRITICAL
                threshold = self.EPA_STANDARDS['ecoli']['critical']
                message = f"CRITICAL E. coli violation at {site_name}: {ecoli_value:.1f} MPN/100mL"
                recommendation = "Immediate action required. Site poses serious health risk. Advise against all water contact."
                
            elif ecoli_value >= self.EPA_STANDARDS['ecoli']['high']:
                severity = AlertSeverity.HIGH
                threshold = self.EPA_STANDARDS['ecoli']['high']
                message = f"HIGH E. coli violation at {site_name}: {ecoli_value:.1f} MPN/100mL"
                recommendation = "High health risk. Strongly advise against swimming or water contact. Monitor closely."
                
            elif ecoli_value >= self.EPA_STANDARDS['ecoli']['moderate']:
                severity = AlertSeverity.MODERATE
                threshold = self.EPA_STANDARDS['ecoli']['moderate']
                message = f"MODERATE E. coli elevation at {site_name}: {ecoli_value:.1f} MPN/100mL"
                recommendation = "Elevated bacterial contamination. Use caution with water activities."
                
            elif ecoli_value >= self.EPA_STANDARDS['ecoli']['safe']:
                severity = AlertSeverity.LOW
                threshold = self.EPA_STANDARDS['ecoli']['safe']
                message = f"E. coli above EPA recreational standard at {site_name}: {ecoli_value:.1f} MPN/100mL"
                recommendation = "Above EPA recreational water quality criteria. Consider health advisory."
            else:
                continue  # No violation
            
            alert = Alert(
                id=self.generate_alert_id(site_code, AlertType.ECOLI_VIOLATION, str(latest[date_col])),
                alert_type=AlertType.ECOLI_VIOLATION,
                severity=severity,
                site_code=site_code,
                site_name=site_name,
                parameter="E. coli",
                value=float(ecoli_value),
                threshold=threshold,
                date=str(latest[date_col]),
                message=message,
                recommendation=recommendation
            )
            alerts.append(alert)
        
        return alerts

    def check_ph_violations(self) -> List[Alert]:
        """Check for pH violations across all sites"""
        alerts = []
        
        for site_code, site_name in self.site_names.items():
            site_data = self.df[self.df['site'] == site_code].copy()
            if site_data.empty:
                continue
                
            # Get latest reading
            date_col = 'WeekDate' if 'WeekDate' in site_data.columns else 'Date'
            site_data = site_data.sort_values(date_col)
            latest = site_data.iloc[-1]
            
            # Skip if no pH data
            if pd.isna(latest['ph']) or latest['ph'] == 'N/A':
                continue
            
            try:
                ph_value = float(latest['ph'])
            except (ValueError, TypeError):
                continue
            
            # Check pH violations
            if ph_value < self.EPA_STANDARDS['ph']['min_moderate'] or ph_value > self.EPA_STANDARDS['ph']['max_moderate']:
                severity = AlertSeverity.HIGH
                message = f"SEVERE pH violation at {site_name}: {ph_value:.2f}"
                recommendation = "Extreme pH levels can be harmful to aquatic life and indicate pollution."
                threshold = self.EPA_STANDARDS['ph']['min_moderate'] if ph_value < 6.0 else self.EPA_STANDARDS['ph']['max_moderate']
                
            elif ph_value < self.EPA_STANDARDS['ph']['min_safe'] or ph_value > self.EPA_STANDARDS['ph']['max_safe']:
                severity = AlertSeverity.MODERATE
                message = f"pH outside acceptable range at {site_name}: {ph_value:.2f}"
                recommendation = "pH should be between 6.5-8.5 for healthy aquatic ecosystems."
                threshold = self.EPA_STANDARDS['ph']['min_safe'] if ph_value < 6.5 else self.EPA_STANDARDS['ph']['max_safe']
            else:
                continue  # No violation
            
            alert = Alert(
                id=self.generate_alert_id(site_code, AlertType.PH_VIOLATION, str(latest[date_col])),
                alert_type=AlertType.PH_VIOLATION,
                severity=severity,
                site_code=site_code,
                site_name=site_name,
                parameter="pH",
                value=ph_value,
                threshold=threshold,
                date=str(latest[date_col]),
                message=message,
                recommendation=recommendation
            )
            alerts.append(alert)
        
        return alerts

    def check_turbidity_violations(self) -> List[Alert]:
        """Check for turbidity violations across all sites"""
        alerts = []
        
        for site_code, site_name in self.site_names.items():
            site_data = self.df[self.df['site'] == site_code].copy()
            if site_data.empty:
                continue
                
            # Get latest reading
            date_col = 'WeekDate' if 'WeekDate' in site_data.columns else 'Date'
            site_data = site_data.sort_values(date_col)
            latest = site_data.iloc[-1]
            
            # Skip if no turbidity data or marked as "<21" (below detection limit)
            turb_value = latest['turbidity']
            if pd.isna(turb_value) or turb_value == 'N/A' or str(turb_value).startswith('<'):
                continue
            
            try:
                turb_value = float(turb_value)
            except (ValueError, TypeError):
                continue
            
            # Determine severity
            if turb_value >= self.EPA_STANDARDS['turbidity']['critical']:
                severity = AlertSeverity.CRITICAL
                threshold = self.EPA_STANDARDS['turbidity']['critical']
                message = f"CRITICAL turbidity violation at {site_name}: {turb_value:.1f} NTU"
                recommendation = "Extremely high turbidity indicates severe water quality issues. Investigate pollution sources."
                
            elif turb_value >= self.EPA_STANDARDS['turbidity']['high']:
                severity = AlertSeverity.HIGH
                threshold = self.EPA_STANDARDS['turbidity']['high']
                message = f"HIGH turbidity at {site_name}: {turb_value:.1f} NTU"
                recommendation = "High turbidity affects water clarity and may indicate pollution or erosion."
                
            elif turb_value >= self.EPA_STANDARDS['turbidity']['moderate']:
                severity = AlertSeverity.MODERATE
                threshold = self.EPA_STANDARDS['turbidity']['moderate']
                message = f"ELEVATED turbidity at {site_name}: {turb_value:.1f} NTU"
                recommendation = "Moderate turbidity levels. Monitor for trends and potential sources."
                
            elif turb_value > self.EPA_STANDARDS['turbidity']['safe']:
                severity = AlertSeverity.LOW
                threshold = self.EPA_STANDARDS['turbidity']['safe']
                message = f"Turbidity above EPA standard at {site_name}: {turb_value:.1f} NTU"
                recommendation = "Above EPA drinking water standard of 1 NTU. Consider filtration needs."
            else:
                continue  # No violation
            
            alert = Alert(
                id=self.generate_alert_id(site_code, AlertType.TURBIDITY_VIOLATION, str(latest[date_col])),
                alert_type=AlertType.TURBIDITY_VIOLATION,
                severity=severity,
                site_code=site_code,
                site_name=site_name,
                parameter="Turbidity",
                value=turb_value,
                threshold=threshold,
                date=str(latest[date_col]),
                message=message,
                recommendation=recommendation
            )
            alerts.append(alert)
        
        return alerts

    def check_missing_data(self) -> List[Alert]:
        """Check for missing critical data points"""
        alerts = []
        
        for site_code, site_name in self.site_names.items():
            site_data = self.df[self.df['site'] == site_code].copy()
            if site_data.empty:
                continue
                
            # Get latest reading
            date_col = 'WeekDate' if 'WeekDate' in site_data.columns else 'Date'
            site_data = site_data.sort_values(date_col)
            latest = site_data.iloc[-1]
            
            missing_params = []
            if pd.isna(latest['ecoli_conc']) or latest['ecoli_conc'] == 'N/A':
                missing_params.append('E. coli')
            if pd.isna(latest['ph']) or latest['ph'] == 'N/A':
                missing_params.append('pH')
            if pd.isna(latest['turbidity']) or latest['turbidity'] == 'N/A':
                missing_params.append('Turbidity')
            
            if missing_params:
                alert = Alert(
                    id=self.generate_alert_id(site_code, AlertType.MISSING_DATA, str(latest[date_col])),
                    alert_type=AlertType.MISSING_DATA,
                    severity=AlertSeverity.LOW,
                    site_code=site_code,
                    site_name=site_name,
                    parameter=", ".join(missing_params),
                    value=0,
                    threshold=0,
                    date=str(latest[date_col]),
                    message=f"Missing data at {site_name}: {', '.join(missing_params)}",
                    recommendation=f"Complete water quality assessment requires all parameters. Missing: {', '.join(missing_params)}"
                )
                alerts.append(alert)
        
        return alerts

    def run_all_checks(self) -> Dict[str, List[Alert]]:
        """Run all alert checks and return categorized results"""
        all_alerts = {
            'ecoli': self.check_ecoli_violations(),
            'ph': self.check_ph_violations(),
            'turbidity': self.check_turbidity_violations(),
            'missing_data': self.check_missing_data()
        }
        
        # Update active alerts
        self.active_alerts = []
        for alert_category in all_alerts.values():
            self.active_alerts.extend(alert_category)
        
        return all_alerts

    def get_alerts_by_severity(self, severity: AlertSeverity = None) -> List[Alert]:
        """Get alerts filtered by severity"""
        if severity is None:
            return self.active_alerts
        return [alert for alert in self.active_alerts if alert.severity == severity]

    def get_alerts_by_site(self, site_code: str) -> List[Alert]:
        """Get alerts for a specific site"""
        return [alert for alert in self.active_alerts if alert.site_code == site_code]

    def get_critical_alerts(self) -> List[Alert]:
        """Get only critical alerts"""
        return self.get_alerts_by_severity(AlertSeverity.CRITICAL)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Mark an alert as acknowledged"""
        for alert in self.active_alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def dismiss_alert(self, alert_id: str) -> bool:
        """Dismiss an alert (move to history)"""
        for i, alert in enumerate(self.active_alerts):
            if alert.id == alert_id:
                alert.is_active = False
                dismissed_alert = self.active_alerts.pop(i)
                self.alert_history.append(dismissed_alert)
                return True
        return False

    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary statistics of current alerts"""
        if not self.active_alerts:
            return {
                'total_alerts': 0,
                'by_severity': {},
                'by_type': {},
                'sites_affected': 0
            }
        
        severity_counts = {}
        type_counts = {}
        affected_sites = set()
        
        for alert in self.active_alerts:
            # Count by severity
            severity_key = alert.severity.value
            severity_counts[severity_key] = severity_counts.get(severity_key, 0) + 1
            
            # Count by type
            type_key = alert.alert_type.value
            type_counts[type_key] = type_counts.get(type_key, 0) + 1
            
            # Track affected sites
            affected_sites.add(alert.site_code)
        
        return {
            'total_alerts': len(self.active_alerts),
            'by_severity': severity_counts,
            'by_type': type_counts,
            'sites_affected': len(affected_sites)
        }

    def export_alerts_to_json(self) -> str:
        """Export current alerts to JSON format"""
        alerts_data = {
            'active_alerts': [alert.to_dict() for alert in self.active_alerts],
            'summary': self.get_alert_summary(),
            'generated_at': datetime.now().isoformat()
        }
        return json.dumps(alerts_data, indent=2)