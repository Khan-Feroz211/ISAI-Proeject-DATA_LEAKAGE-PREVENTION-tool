from flask import Flask, render_template, request, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'dlp-secure-key-2024'

# Simple DLP functionality
class SimpleDLP:
    @staticmethod
    def scan_file(filepath):
        """Basic file scanning"""
        try:
            if not os.path.exists(filepath):
                return {'error': 'File not found'}
            
            stat = os.stat(filepath)
            return {
                'path': filepath,
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'sensitive': False,
                'issues': []
            }
        except Exception as e:
            return {'error': str(e), 'path': filepath}

    @staticmethod
    def scan_directory(path):
        """Scan directory"""
        results = {
            'path': path,
            'scanned_at': datetime.now().isoformat(),
            'total_files': 0,
            'sensitive_files': 0,
            'findings': []
        }
        
        try:
            for root, dirs, files in os.walk(path):
                for file in files[:10]:  # Limit to 10 files
                    filepath = os.path.join(root, file)
                    file_result = SimpleDLP.scan_file(filepath)
                    results['total_files'] += 1
                    
                    if 'error' not in file_result:
                        results['findings'].append(file_result)
                
                break  # Only top level
                
        except Exception as e:
            results['error'] = str(e)
            
        return results

# Routes
@app.route('/')
def dashboard():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>DLP Security Tool</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
            .card { background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .btn { background: #007bff; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; margin: 5px; }
            .nav { display: flex; gap: 10px; margin-bottom: 20px; }
            .nav a { padding: 10px; background: white; text-decoration: none; border-radius: 4px; color: #333; }
        </style>
    </head>
    <body>
        <h1>🔐 DLP Security Scanner</h1>
        
        <div class="nav">
            <a href="/">Dashboard</a>
            <a href="/scan">Scanner</a>
            <a href="/monitor">Monitor</a>
        </div>
        
        <div class="card">
            <h3>Quick Actions</h3>
            <button class="btn" onclick="scanHome()">Scan Home Directory</button>
            <button class="btn" onclick="scanCurrent()">Scan Current Folder</button>
        </div>
        
        <div class="card">
            <h3>Scan Results</h3>
            <div id="results">No scans performed yet.</div>
        </div>

        <script>
            function scanHome() {
                fetch('/api/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: '~'})
                })
                .then(r => r.json())
                .then(data => {
                    document.getElementById('results').innerHTML = 
                        `<h4>Scan Results:</h4>
                         <p>Files scanned: ${data.total_files}</p>
                         <pre>${JSON.stringify(data.findings, null, 2)}</pre>`;
                });
            }
            
            function scanCurrent() {
                fetch('/api/scan', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({path: '.'})
                })
                .then(r => r.json())
                .then(data => {
                    document.getElementById('results').innerHTML = 
                        `<h4>Scan Results:</h4>
                         <p>Files scanned: ${data.total_files}</p>
                         <pre>${JSON.stringify(data.findings, null, 2)}</pre>`;
                });
            }
        </script>
    </body>
    </html>
    '''

@app.route('/scan')
def scan_page():
    return '''
    <div style="margin: 20px;">
        <h2>File Scanner</h2>
        <input type="text" id="scanPath" placeholder="/path/to/scan" value=".">
        <button onclick="startScan()">Start Scan</button>
        <div id="scanResults"></div>
    </div>
    <script>
        function startScan() {
            const path = document.getElementById('scanPath').value;
            fetch('/api/scan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({path: path})
            })
            .then(r => r.json())
            .then(data => {
                document.getElementById('scanResults').innerHTML = 
                    '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            });
        }
    </script>
    '''

@app.route('/monitor')
def monitor_page():
    return '''
    <div style="margin: 20px;">
        <h2>File Monitoring</h2>
        <p>File monitoring dashboard coming soon...</p>
    </div>
    '''

# API Routes
@app.route('/api/scan', methods=['POST'])
def api_scan():
    data = request.json
    path = data.get('path', '.')
    
    # Expand home directory
    if path == '~':
        path = os.path.expanduser('~')
    
    results = SimpleDLP.scan_directory(path)
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
