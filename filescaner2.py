import os
import logging

class FileScanner:
    def __init__(self, config, dlp_engine):
        """
        File scanner responsible for scanning directories and passing
        files to the DLP Engine for inspection.
        """
        self.config = config
        self.dlp_engine = dlp_engine

        file_scan_cfg = config.get("file_scan", {})

        self.allowed_extensions = file_scan_cfg.get("allowed_extensions", [])
        self.recursive = file_scan_cfg.get("recursive", True)

    def is_allowed_file(self, filename):
        """Check if file extension is allowed."""
        if not self.allowed_extensions:
            return True  # Scan everything if no restrictions

        return any(filename.lower().endswith(ext) for ext in self.allowed_extensions)

    def scan_directory(self, directory_path):
        """Scan all files in a directory."""
        if not os.path.exists(directory_path):
            logging.error(f"Directory does not exist: {directory_path}")
            return

        logging.info(f"📁 Scanning directory: {directory_path}")

        if self.recursive:
            for root, _, files in os.walk(directory_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    self.process_file(file_path)
        else:
            # Non-recursive scan
            for file in os.listdir(directory_path):
                file_path = os.path.join(directory_path, file)
                if os.path.isfile(file_path):
                    self.process_file(file_path)

        logging.info("✅ Directory scan completed.")

    def process_file(self, file_path):
        """Handle scanning of a single file."""
        if not self.is_allowed_file(file_path):
            logging.info(f"⏭️ Skipped (extension not allowed): {file_path}")
            return

        logging.info(f"🔍 Scanning file: {file_path}")

        try:
            result = self.dlp_engine.inspect_file(file_path)
            if result:
                logging.warning(f"🚨 Sensitive data found in: {file_path}")
            else:
                logging.info(f"✔ No issues found in: {file_path}")
        except Exception as e:
            logging.error(f"Error scanning file {file_path}: {e}")
