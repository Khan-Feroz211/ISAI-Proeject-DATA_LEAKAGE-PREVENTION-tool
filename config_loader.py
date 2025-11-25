import yaml
import os
from pathlib import Path
import logging

class ConfigLoader:
    @staticmethod
    def load_config(config_path: str = None) -> dict:
        """Load configuration from YAML file"""
        if config_path is None:
            config_path = "config/dlp_config.yaml"
        
        config_file = Path(config_path)
        
        if not config_file.exists():
            # Return default config if file doesn't exist
            return ConfigLoader.get_default_config()
        
        try:
            with open(config_file, 'r') as file:
                config = yaml.safe_load(file)
            
            # Validate and set defaults
            config = ConfigLoader.validate_config(config)
            return config
            
        except Exception as e:
            logging.error(f"Error loading config from {config_path}: {str(e)}")
            return ConfigLoader.get_default_config()
    
    @staticmethod
    def get_default_config() -> dict:
        """Get default configuration"""
        return {
            'app': {
                'name': 'DLP Linux Tool',
                'version': '1.0.0',
                'verbose': False
            },
            'scan': {
                'target_path': '/data/scan',
                'max_file_size': 104857600,
                'enabled_file_types': ['.txt', '.pdf', '.doc', '.docx', '.csv'],
                'excluded_directories': ['.git', 'node_modules', '__pycache__']
            },
            'monitor': {
                'watch_directories': ['/home', '/var/www', '/opt'],
                'network_monitoring': False,
                'scan_interval': 30,
                'real_time_scanning': True
            },
            'patterns': {
                'credit_card': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
                'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
                'email': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            },
            'ai': {
                'model_name': 'distilbert-base-uncased',
                'model_path': './models/',
                'confidence_threshold': 0.75,
                'training_data_path': './data/training/',
                'use_gpu': True
            },
            'reporting': {
                'output_format': 'json',
                'output_path': './data/output/',
                'generate_summary': True,
                'save_evidence': True
            },
            'alerts': {
                'enabled': True,
                'confidence_threshold': 0.85,
                'email_alerts': False,
                'email_recipient': 'admin@company.com',
                'console_alerts': True,
                'log_alerts': True
            },
            'database': {
                'type': 'sqlite',
                'path': './data/dlp_database.db'
            }
        }
    
    @staticmethod
    def validate_config(config: dict) -> dict:
        """Validate and fill in missing configuration values"""
        default_config = ConfigLoader.get_default_config()
        
        def deep_update(default, user):
            for key, value in user.items():
                if isinstance(value, dict) and key in default and isinstance(default[key], dict):
                    deep_update(default[key], value)
                else:
                    default[key] = value
            return default
        
        return deep_update(default_config.copy(), config)
