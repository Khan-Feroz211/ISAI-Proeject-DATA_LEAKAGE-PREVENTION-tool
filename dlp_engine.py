import logging
import os
from datetime import datetime
import json
from typing import List, Dict, Optional

class DLPEngine:
    """
    Simplified DLP Engine for Flask integration
    """

    def __init__(self, config: Dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Setup basic logging if not configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        self.report_dir = config.get("reporting", {}).get("output_path", "./reports")
        os.makedirs(self.report_dir, exist_ok=True)

        self.statistics = {
            "files_scanned": 0,
            "sensitive_files_found": 0,
            "last_scan": None
        }

    def scan_target(self, target_path: str) -> List[Dict]:
        """Scan a target path and return results"""
        self.logger.info(f"Scanning target: {target_path}")
        
        results = []
        
        if os.path.isfile(target_path):
            results.append(self.scan_file(target_path))
        elif os.path.isdir(target_path):
            for root, dirs, files in os.walk(target_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    results.append(self.scan_file(file_path))
        
        self.statistics["files_scanned"] += len(results)
        self.statistics["last_scan"] = datetime.now().isoformat()
        
        return results

    def scan_file(self, file_path: str) -> Dict:
        """Scan individual file"""
        try:
            file_stat = os.stat(file_path)
            file_info = {
                'path': file_path,
                'size': file_stat.st_size,
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'sensitive_content': False,
                'issues': []
            }
            
            # Basic content checking (you can enhance this)
            if self.check_sensitive_content(file_path):
                file_info['sensitive_content'] = True
                file_info['issues'].append('Potential sensitive data found')
                self.statistics["sensitive_files_found"] += 1
            
            return file_info
            
        except Exception as e:
            return {
                'path': file_path,
                'error': str(e),
                'sensitive_content': False,
                'issues': ['Scan failed']
            }

    def check_sensitive_content(self, file_path: str) -> bool:
        """Basic sensitive content detection"""
        try:
            # Only read text files for now
            if file_path.lower().endswith(('.txt', '.log', '.csv')):
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().lower()
                    
                    # Check for common sensitive patterns
                    sensitive_terms = ['password', 'secret', 'confidential', 'ssn', 'credit card']
                    return any(term in content for term in sensitive_terms)
        except:
            pass
        return False

    def generate_report(self) -> Dict:
        """Generate scan report"""
        return {
            "report_time": datetime.now().isoformat(),
            "statistics": self.statistics
        }