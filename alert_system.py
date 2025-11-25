# src/alert_system.py

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path


class AlertSystem:
    def __init__(self, config: dict):
        """
        Initialize the alert system.
        Config example:
        {
            "enabled": True,
            "confidence_threshold": 0.85,
            "console_alerts": True,
            "log_alerts": True,
            "email_alerts": False,
            "smtp_server": "smtp.example.com",
            "smtp_port": 587,
            "email_sender": "dlp@example.com",
            "email_recipient": "admin@example.com",
            "email_password": "password123"
        }
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def send_alert(self, finding: dict, event_type: str = "scan"):
        """
        Send alert for a given finding.
        finding example:
        {
            "file_path": "/home/user/secrets.txt",
            "pattern_matches": {"credit_card": ["1234-5678-9012-3456"]},
            "ai_analysis": {"confidence": 0.92},
            "anomaly_detected": True
        }
        """
        if not self.config.get("enabled", True):
            return
        
        confidence = finding.get("ai_analysis", {}).get("confidence", 0)
        if confidence < self.config.get("confidence_threshold", 0.85):
            return
        
        message = self._prepare_alert_message(finding, event_type)
        
        if self.config.get("console_alerts", True):
            self._send_console_alert(message)
        
        if self.config.get("log_alerts", True):
            self._send_log_alert(message)
        
        if self.config.get("email_alerts", False):
            self._send_email_alert(message)
    
    def _prepare_alert_message(self, finding: dict, event_type: str) -> str:
        """Prepare alert message string"""
        file_path = finding.get("file_path", "unknown")
        patterns = finding.get("pattern_matches", {})
        ai_confidence = finding.get("ai_analysis", {}).get("confidence", 0)
        anomaly_detected = finding.get("anomaly_detected", False)
        
        message = f"""
================ DLP SECURITY ALERT =================

File: {file_path}
Event: {event_type}
Time: {datetime.now().isoformat()}

Detection Results:
- AI Confidence: {ai_confidence:.2f}
- Patterns Found: {list(patterns.keys())}
- Anomaly Detected: {anomaly_detected}

Recommended Actions:
- Review file content
- Verify business data legitimacy
- Take appropriate security measures
====================================================
"""
        return message
    
    def _send_console_alert(self, message: str):
        """Print alert to console"""
        print(message)
    
    def _send_log_alert(self, message: str):
        """Log alert using logging"""
        self.logger.warning(f"DLP Alert: {message}")
    
    def _send_email_alert(self, message: str):
        """Send alert via SMTP email"""
        try:
            smtp_server = self.config.get("smtp_server", "smtp.example.com")
            smtp_port = self.config.get("smtp_port", 587)
            sender = self.config.get("email_sender", "dlp@example.com")
            recipient = self.config.get("email_recipient", "admin@example.com")
            password = self.config.get("email_password", "")
            
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = "DLP Security Alert"
            msg.attach(MIMEText(message, "plain"))
            
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                if password:
                    server.login(sender, password)
                server.send_message(msg)
            
            self.logger.info(f"Email alert sent to {recipient}")
        
        except Exception as e:
            self.logger.error(f"Failed to send email alert: {e}")

