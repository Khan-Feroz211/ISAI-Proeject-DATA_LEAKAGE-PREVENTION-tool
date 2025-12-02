import logging
import re
from typing import Dict, Any, List

class ContentClassifier:
    """
    AI Content Classifier for sensitive data detection
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Sensitive patterns with compiled regex for better performance
        self.sensitive_patterns = {
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'credit_card': re.compile(r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
            'api_key': re.compile(r'\b[A-Za-z0-9]{32,40}\b'),
            'password_mention': re.compile(r'\bpassword\s*[=:]\s*[^\s]+\b', re.IGNORECASE),
            'secret_mention': re.compile(r'\bsecret\s*[=:]\s*[^\s]+\b', re.IGNORECASE)
        }
        
        # High-risk keywords
        self.high_risk_keywords = [
            'password', 'secret', 'confidential', 'private', 'restricted',
            'classified', 'proprietary', 'token', 'key', 'credential',
            'aws_key', 'api_key', 'access_key', 'secret_key', 'private_key'
        ]
    
    def classify_content(self, content: str, file_path: str) -> Dict[str, Any]:
        """
        Classify content for sensitive information
        """
        try:
            results = {
                'is_sensitive': False,
                'confidence': 0.0,
                'detected_patterns': [],
                'risk_level': 'low',
                'details': []
            }
            
            content_lower = content.lower()
            detected_count = 0
            
            # Check for regex patterns
            for pattern_name, pattern in self.sensitive_patterns.items():
                matches = pattern.findall(content)
                if matches:
                    detected_count += len(matches)
                    results['detected_patterns'].append({
                        'type': pattern_name,
                        'count': len(matches),
                        'sample': matches[0] if matches else None
                    })
            
            # Check for high-risk keywords
            keyword_matches = []
            for keyword in self.high_risk_keywords:
                if keyword in content_lower:
                    count = content_lower.count(keyword)
                    detected_count += count
                    keyword_matches.append({
                        'keyword': keyword,
                        'count': count
                    })
            
            if keyword_matches:
                results['detected_patterns'].extend(keyword_matches)
            
            # Calculate risk level
            if detected_count > 0:
                results['is_sensitive'] = True
                results['confidence'] = min(1.0, detected_count * 0.2)
                
                if detected_count >= 5:
                    results['risk_level'] = 'high'
                elif detected_count >= 2:
                    results['risk_level'] = 'medium'
                else:
                    results['risk_level'] = 'low'
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error in content classification: {str(e)}")
            return {
                'is_sensitive': False,
                'confidence': 0.0,
                'detected_patterns': [],
                'risk_level': 'low',
                'details': [f'Classification error: {str(e)}']
            }
