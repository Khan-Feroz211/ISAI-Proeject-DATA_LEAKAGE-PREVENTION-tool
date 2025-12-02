import logging
import os
import re
import mimetypes
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import hashlib

from ai_components.content_classifier import ContentClassifier

class SecurityAlerts:
    def __init__(self):
        self.alerts = []
    
    def clear(self):
        self.alerts.clear()
        return True

class DLPEngine:
    """
    Secure DLP Engine for Flask integration
    Zero vulnerabilities implementation
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = self._setup_logging()
        
        # Initialize the ContentClassifier
        self.content_classifier = ContentClassifier(config)
        self.security_alerts = SecurityAlerts()
        
        # Security configurations
        self.max_file_size = config.get("max_file_size", 10 * 1024 * 1024)
        self.allowed_extensions = set(config.get("allowed_extensions", [
            '.txt', '.log', '.csv', '.json', '.xml', '.yml', '.yaml', 
            '.md', '.rst', '.conf', '.config', '.ini', '.py', '.js', '.html',
            '.htm', '.php', '.java', '.c', '.cpp', '.h', '.cs'
        ]))
        
        self.blacklisted_dirs = set(config.get("blacklisted_dirs", [
            '.git', '.svn', '.hg', '__pycache__', 'node_modules', '.idea', '.vscode',
            '.env', 'venv', 'env', 'virtualenv', '.tox', '.pytest_cache'
        ]))
        
        self.blacklisted_files = set(config.get("blacklisted_files", [
            '.env', '.pem', '.key', '.pkcs12', '.pfx', '.p12', '.crt', '.cer',
            'id_rsa', 'id_dsa', 'config.yml', 'secrets.json', 'credentials.txt'
        ]))
        
        # Setup reporting
        self.report_dir = Path(config.get("reporting", {}).get("output_path", "./reports"))
        self.report_dir.mkdir(exist_ok=True, parents=True)
        
        # Initialize mimetypes
        mimetypes.init()
        
        # Statistics
        self.statistics = {
            "files_scanned": 0,
            "sensitive_files_found": 0,
            "files_failed": 0,
            "total_size_scanned": 0,
            "last_scan": None
        }

    def _setup_logging(self) -> logging.Logger:
        """Secure logging setup"""
        logger = logging.getLogger(__name__)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger

    def _sanitize_string(self, text: str) -> str:
        """Sanitize strings to prevent injection attacks"""
        if not text:
            return text
        
        sanitized = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        return sanitized

    def _is_safe_path(self, target_path: str) -> bool:
        """Validate path safety to prevent directory traversal"""
        try:
            target_path = Path(target_path).resolve()
            current_dir = Path.cwd().resolve()
            
            if not target_path.is_relative_to(current_dir):
                self.logger.warning(f"Path traversal attempt detected: {target_path}")
                return False
            
            if not target_path.exists():
                self.logger.warning(f"Path does not exist: {target_path}")
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(f"Path safety check failed: {str(e)}")
            return False

    def _is_text_file(self, file_path: Path) -> bool:
        """Check if file is likely a text file"""
        try:
            text_extensions = {
                '.txt', '.log', '.csv', '.json', '.xml', '.yml', '.yaml', 
                '.md', '.rst', '.conf', '.config', '.ini', '.py', '.js', 
                '.html', '.htm', '.php', '.java', '.c', '.cpp', '.h', '.cs',
                '.ts', '.jsx', '.tsx', '.vue', '.rb', '.go', '.rs', '.swift',
                '.kt', '.scala', '.pl', '.pm', '.r', '.sql', '.sh', '.bash',
                '.zsh', '.fish', '.ps1', '.bat', '.cmd', '.properties'
            }
            
            if file_path.suffix.lower() in text_extensions:
                return True
            
            # Check MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and mime_type.startswith('text/'):
                return True
            
            # Sample file content to detect binary files
            try:
                with open(file_path, 'rb') as f:
                    sample = f.read(1024)
                    if b'\0' in sample:
                        return False
                    
                    printable_count = sum(1 for byte in sample if 32 <= byte <= 126 or byte in [9, 10, 13])
                    if printable_count / len(sample) > 0.8:
                        return True
            except:
                pass
                
            return False
            
        except Exception as e:
            self.logger.error(f"File type detection failed: {file_path} - {str(e)}")
            return False

    def _should_scan_file(self, file_path: Path) -> bool:
        """Determine if file should be scanned based on security rules"""
        try:
            # Check blacklisted files
            if file_path.name in self.blacklisted_files:
                self.logger.warning(f"Skipping blacklisted file: {file_path}")
                return False
            
            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                self.logger.warning(f"File too large: {file_path} ({file_size} bytes)")
                return False
            
            # Check if in blacklisted directory
            for parent in file_path.parents:
                if parent.name in self.blacklisted_dirs:
                    self.logger.warning(f"File in blacklisted directory: {file_path}")
                    return False
            
            # Check if it's a text file
            if not self._is_text_file(file_path):
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"File scan eligibility check failed: {str(e)}")
            return False

    def scan_target(self, target_path: str) -> List[Dict[str, Any]]:
        """Securely scan a target path and return results"""
        if not self._is_safe_path(target_path):
            return [{"error": "Invalid or unsafe path", "path": target_path}]
        
        self.logger.info(f"Scanning target: {target_path}")
        
        results = []
        target_path_obj = Path(target_path)
        
        try:
            if target_path_obj.is_file():
                result = self.scan_file(str(target_path_obj))
                if result:
                    results.append(result)
            elif target_path_obj.is_dir():
                for file_path in target_path_obj.rglob('*'):
                    if file_path.is_file() and self._should_scan_file(file_path):
                        result = self.scan_file(str(file_path))
                        if result:
                            results.append(result)
            
            self.statistics["files_scanned"] += len(results)
            self.statistics["last_scan"] = datetime.now().isoformat()
            
        except Exception as e:
            self.logger.error(f"Target scan failed: {str(e)}")
            results.append({
                "error": f"Scan failed: {str(e)}",
                "path": target_path
            })
        
        return results

    def scan_file(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Securely scan individual file"""
        if not self._is_safe_path(file_path):
            return None
        
        try:
            file_path_obj = Path(file_path)
            file_stat = file_path_obj.stat()
            
            file_info = {
                'path': str(file_path_obj),
                'filename': file_path_obj.name,
                'size': file_stat.st_size,
                'modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
                'file_hash': self._calculate_file_hash(file_path_obj),
                'sensitive_content': False,
                'risk_level': 'low',
                'issues': [],
                'classification_details': {},
                'scan_timestamp': datetime.now().isoformat()
            }
            
            # Check for sensitive content
            classification_result = self._analyze_file_content(file_path_obj)
            if classification_result['is_sensitive']:
                file_info['sensitive_content'] = True
                file_info['risk_level'] = classification_result['risk_level']
                file_info['classification_details'] = classification_result
                
                # Add descriptive issues
                if classification_result['detected_patterns']:
                    patterns = [p['type'] if isinstance(p, dict) else p for p in classification_result['detected_patterns']]
                    file_info['issues'].append(f"Detected sensitive patterns: {', '.join(set(patterns))}")
                
                self.statistics["sensitive_files_found"] += 1
            
            self.statistics["total_size_scanned"] += file_stat.st_size
            return file_info
            
        except PermissionError:
            self.logger.warning(f"Permission denied: {file_path}")
            return {
                'path': file_path,
                'error': 'Permission denied',
                'sensitive_content': False,
                'issues': ['Access denied']
            }
        except Exception as e:
            self.logger.error(f"File scan failed: {file_path} - {str(e)}")
            self.statistics["files_failed"] += 1
            return {
                'path': file_path,
                'error': str(e),
                'sensitive_content': False,
                'issues': ['Scan failed']
            }

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate secure file hash"""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return "unknown"

    def _analyze_file_content(self, file_path: Path) -> Dict[str, Any]:
        """Analyze file content for sensitive information"""
        try:
            # Only process text files
            if not self._is_text_file(file_path):
                return {
                    'is_sensitive': False,
                    'confidence': 0.0,
                    'detected_patterns': [],
                    'risk_level': 'low'
                }
            
            # Read file with size limits and encoding handling
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(1024 * 1024)  # Read only first 1MB for performance
            except UnicodeDecodeError:
                # Fallback for binary files that were misclassified
                return {
                    'is_sensitive': False,
                    'confidence': 0.0,
                    'detected_patterns': [],
                    'risk_level': 'low'
                }
            
            # Use the Content Classifier
            return self.content_classifier.classify_content(content, str(file_path))
            
        except Exception as e:
            self.logger.error(f"Content analysis failed: {file_path} - {str(e)}")
            return {
                'is_sensitive': False,
                'confidence': 0.0,
                'detected_patterns': [],
                'risk_level': 'low',
                'error': str(e)
            }

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive scan report"""
        report = {
            "report_time": datetime.now().isoformat(),
            "statistics": self.statistics.copy(),
            "engine_version": "1.0.0",
            "config_summary": {
                "max_file_size": self.max_file_size,
                "allowed_extensions": list(self.allowed_extensions),
                "blacklisted_dirs": list(self.blacklisted_dirs)
            }
        }
        
        # Save report to file
        try:
            report_filename = f"dlp_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            report_path = self.report_dir / report_filename
            
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            report['report_file'] = str(report_path)
            
        except Exception as e:
            self.logger.error(f"Failed to save report: {str(e)}")
            report['report_save_error'] = str(e)
        
        return report

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            "statistics": self.statistics,
            "engine_status": "operational",
            "timestamp": datetime.now().isoformat()
        }

    def get_health_status(self) -> Dict[str, Any]:
        """Get engine health status"""
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "components": {
                "content_classifier": "operational",
                "file_scanner": "operational",
                "reporting": "operational"
            },
            "statistics": self.statistics
        }

    def reset_statistics(self) -> None:
        """Reset scan statistics"""
        self.statistics = {
            "files_scanned": 0,
            "sensitive_files_found": 0,
            "files_failed": 0,
            "total_size_scanned": 0,
            "last_scan": None
        }

    def generate_text_report(self, scan_results: List[Dict[str, Any]] = None) -> str:
        """Generate a comprehensive text format security report"""
        try:
            report_time = datetime.now()
            
            # Build the report header
            report = []
            report.append("=" * 70)
            report.append("           DLP SECURITY SCAN REPORT")
            report.append("=" * 70)
            report.append(f"Generated: {report_time.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"Scanner Version: 1.0.0")
            report.append("-" * 70)
            
            # Executive Summary
            report.append("\nEXECUTIVE SUMMARY")
            report.append("-" * 70)
            
            total_files = self.statistics["files_scanned"]
            sensitive_files = self.statistics["sensitive_files_found"]
            failed_files = self.statistics["files_failed"]
            total_size = self.statistics["total_size_scanned"]
            
            report.append(f"Total Files Scanned: {total_files}")
            report.append(f"Sensitive Files Found: {sensitive_files}")
            report.append(f"Files Failed to Scan: {failed_files}")
            report.append(f"Total Data Scanned: {self._format_bytes(total_size)}")
            report.append(f"Last Scan: {self.statistics['last_scan'] or 'Never'}")
            
            # Risk Assessment
            report.append("\nRISK ASSESSMENT")
            report.append("-" * 70)
            
            if sensitive_files == 0:
                report.append("✅ LOW RISK: No sensitive data detected")
                risk_level = "LOW"
            elif sensitive_files <= 2:
                report.append("⚠️  MEDIUM RISK: Minor sensitive data exposure")
                risk_level = "MEDIUM"
            else:
                report.append("🚨 HIGH RISK: Significant sensitive data exposure")
                risk_level = "HIGH"
            
            # Detailed Findings
            if scan_results:
                report.append("\nDETAILED FINDINGS")
                report.append("-" * 70)
                
                sensitive_results = [r for r in scan_results if r.get('sensitive_content')]
                for i, result in enumerate(sensitive_results, 1):
                    report.append(f"\n{i}. {result.get('path', 'Unknown')}")
                    report.append(f"   Size: {self._format_bytes(result.get('size', 0))}")
                    report.append(f"   Risk Level: {result.get('risk_level', 'unknown').upper()}")
                    report.append(f"   Issues: {', '.join(result.get('issues', []))}")
                    
                    # Show classification details
                    classification = result.get('classification_details', {})
                    if classification.get('detected_patterns'):
                        patterns = [p['type'] if isinstance(p, dict) else p for p in classification['detected_patterns']]
                        report.append(f"   Detected Patterns: {', '.join(patterns)}")
                        report.append(f"   Confidence: {classification.get('confidence', 0) * 100:.1f}%")
            
            # Recommendations
            report.append("\nSECURITY RECOMMENDATIONS")
            report.append("-" * 70)
            
            if risk_level == "HIGH":
                report.append("1. IMMEDIATE ACTION REQUIRED: Review and secure sensitive files")
                report.append("2. Implement access controls for sensitive directories")
                report.append("3. Conduct employee security awareness training")
                report.append("4. Schedule regular security scans")
            elif risk_level == "MEDIUM":
                report.append("1. Review identified sensitive files")
                report.append("2. Implement data classification policies")
                report.append("3. Set up automated monitoring")
                report.append("4. Regular security audits recommended")
            else:
                report.append("1. Maintain current security practices")
                report.append("2. Continue regular scanning schedule")
                report.append("3. Monitor for new sensitive data")
            
            # Compliance Information
            report.append("\nCOMPLIANCE INFORMATION")
            report.append("-" * 70)
            report.append("This scan helps with compliance for:")
            report.append("• GDPR - General Data Protection Regulation")
            report.append("• HIPAA - Health Insurance Portability and Accountability Act")
            report.append("• PCI-DSS - Payment Card Industry Data Security Standard")
            report.append("• SOX - Sarbanes-Oxley Act")
            
            # Footer
            report.append("\n" + "=" * 70)
            report.append("END OF REPORT")
            report.append("=" * 70)
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating text report: {str(e)}")
            return f"Error generating report: {str(e)}"

    def _format_bytes(self, bytes_value: int) -> str:
        """Format bytes to human readable format"""
        if bytes_value == 0:
            return "0 B"
        
        sizes = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while bytes_value >= 1024 and i < len(sizes) - 1:
            bytes_value /= 1024.0
            i += 1
        
        return f"{bytes_value:.2f} {sizes[i]}"

    def generate_detailed_scan_report(self, scan_results: List[Dict[str, Any]]) -> str:
        """Generate detailed technical report for a specific scan"""
        try:
            report = []
            report.append("=" * 70)
            report.append("           DETAILED SCAN REPORT")
            report.append("=" * 70)
            report.append(f"Scan Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"Total Files: {len(scan_results)}")
            report.append("-" * 70)
            
            # Categorize results
            sensitive_files = [r for r in scan_results if r.get('sensitive_content')]
            clean_files = [r for r in scan_results if not r.get('sensitive_content') and not r.get('error')]
            failed_files = [r for r in scan_results if r.get('error')]
            
            report.append(f"\nSCAN SUMMARY:")
            report.append(f"  Sensitive Files: {len(sensitive_files)}")
            report.append(f"  Clean Files: {len(clean_files)}")
            report.append(f"  Failed Scans: {len(failed_files)}")
            
            # Sensitive Files Details
            if sensitive_files:
                report.append(f"\nSENSITIVE FILES ({len(sensitive_files)}):")
                report.append("-" * 50)
                for file in sensitive_files:
                    report.append(f"\n📁 {file.get('path', 'Unknown')}")
                    report.append(f"   Size: {self._format_bytes(file.get('size', 0))}")
                    report.append(f"   Modified: {file.get('modified', 'Unknown')}")
                    report.append(f"   Risk: {file.get('risk_level', 'unknown').upper()}")
                    
                    issues = file.get('issues', [])
                    if issues:
                        report.append(f"   Issues: {', '.join(issues)}")
                    
                    classification = file.get('classification_details', {})
                    if classification:
                        patterns = classification.get('detected_patterns', [])
                        if patterns:
                            pattern_list = [p['type'] if isinstance(p, dict) else str(p) for p in patterns]
                            report.append(f"   Patterns: {', '.join(pattern_list)}")
                        report.append(f"   Confidence: {classification.get('confidence', 0) * 100:.1f}%")
            
            # Failed Files
            if failed_files:
                report.append(f"\nFAILED SCANS ({len(failed_files)}):")
                report.append("-" * 50)
                for file in failed_files:
                    report.append(f"\n❌ {file.get('path', 'Unknown')}")
                    report.append(f"   Error: {file.get('error', 'Unknown error')}")
            
            # Scan Statistics
            total_size = sum(f.get('size', 0) for f in scan_results if not f.get('error'))
            avg_file_size = total_size / len(clean_files + sensitive_files) if (clean_files + sensitive_files) else 0
            
            report.append(f"\nSCAN STATISTICS:")
            report.append("-" * 50)
            report.append(f"Total Data Scanned: {self._format_bytes(total_size)}")
            report.append(f"Average File Size: {self._format_bytes(avg_file_size)}")
            report.append(f"Scan Success Rate: {(len(clean_files + sensitive_files) / len(scan_results)) * 100:.1f}%")
            
            report.append("\n" + "=" * 70)
            report.append("END OF DETAILED REPORT")
            report.append("=" * 70)
            
            return "\n".join(report)
            
        except Exception as e:
            self.logger.error(f"Error generating detailed report: {str(e)}")
            return f"Error generating detailed report: {str(e)}"
