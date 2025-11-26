import threading
from pathlib import Path
from alert_system import AlertSystem
from dlp_engine import DLPEngine
import os
import re
import logging
import time

class BootnetMonitor:
    LEAKAGE_PATTERNS = {
        "EMAIL": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "PASSWORD": r"password\s*=\s*[\"'].*?[\"']",
        "API_KEY": r"(sk|api|key|token)[_=:\s\"']+[A-Za-z0-9_\-]{12,40}",
        "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b"
    }

    def __init__(self, alert_config: dict, scan_paths=None, scan_interval=30):
        self.alert_system = AlertSystem(alert_config)
        self.ai_model = DLPEngine(alert_config)
        self.scan_paths = scan_paths or ["./data"]
        self.scan_interval = scan_interval
        self.running = False
        self.findings = []
        self.lock = threading.Lock()
        self.logger = logging.getLogger("BootnetMonitor")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def start(self):
        self.running = True
        thread = threading.Thread(target=self._monitor_loop, daemon=True)
        thread.start()
        self.logger.info("BootnetMonitor started in background thread")

    def stop(self):
        self.running = False
        self.logger.info("BootnetMonitor stopped")

    def _monitor_loop(self):
        while self.running:
            new_findings = self.scan_directories()
            if new_findings:
                self.report_findings(new_findings)
            time.sleep(self.scan_interval)

    def scan_directories(self):
        all_findings = []
        for path in self.scan_paths:
            if not os.path.exists(path):
                self.logger.warning(f"Scan path not found: {path}")
                continue
            for root, dirs, files in os.walk(path):
                for file in files:
                    file_path = Path(root) / file
                    results = self.scan_file(file_path)
                    all_findings.extend(results)
        return all_findings

    def scan_file(self, file_path: Path):
        findings = []
        try:
            if not file_path.suffix.lower() in [".txt", ".log", ".csv", ".json"]:
                return []

            with open(file_path, "r", errors="ignore") as f:
                for idx, line in enumerate(f, start=1):
                    for label, pattern in self.LEAKAGE_PATTERNS.items():
                        matches = re.findall(pattern, line)
                        if matches:
                            confidence = self.ai_model.analyze(line)["confidence"]
                            finding = {
                                "file": str(file_path),
                                "line": idx,
                                "pattern_type": label,
                                "matches": matches,
                                "confidence": confidence,
                                "snippet": line.strip()
                            }
                            self.ai_model.add_training_sample(line, label)
                            findings.append(finding)
        except Exception as e:
            self.logger.warning(f"Skipped file {file_path}: {e}")
        return findings

    def report_findings(self, findings):
        with self.lock:
            self.findings.extend(findings)
            for f in findings:
                self.alert_system.send_alert(f, event_type="bootnet_event")
