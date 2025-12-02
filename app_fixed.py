from flask import Flask, render_template, request, jsonify
import os
import logging
from pathlib import Path
from dlp_engine import DLPEngine

# Initialize Flask app
app = Flask(__name__)
app.logger.setLevel(logging.INFO)

# DLP Engine Configuration
dlp_config = {
    "max_file_size": 10 * 1024 * 1024,
    "allowed_extensions": [".txt", ".log", ".csv", ".json", ".xml", ".yml", ".yaml", ".py", ".js", ".html"],
    "blacklisted_dirs": [".git", "__pycache__", "node_modules", ".env", "venv"],
    "blacklisted_files": [".env", ".pem", ".key", "credentials.json"],
    "reporting": {"output_path": "./reports"}
}

# Initialize DLP Engine
try:
    dlp_engine = DLPEngine(dlp_config)
    print("✓ DLP Engine initialized successfully")
except Exception as e:
    print(f"❌ DLP Engine initialization failed: {e}")
    dlp_engine = None

def normalize_and_verify_path(path):
    """Normalize and verify file path security"""
    try:
        path_obj = Path(path).resolve()
        current_dir = Path.cwd().resolve()
        
        # Prevent directory traversal
        if not path_obj.is_relative_to(current_dir):
            raise ValueError("Invalid path: directory traversal attempt")
            
        return str(path_obj)
    except Exception as e:
        raise ValueError(f"Invalid path: {str(e)}")

# Routes
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/scanner')
def scanner():
    return render_template('scanner.html')

@app.route('/monitor')
def monitor():
    return render_template('monitor.html')

@app.route('/alerts')
def alerts():
    return render_template('alerts.html')

@app.route('/reports')
def reports():
    return render_template('reports.html')

@app.route('/policies')
def policies():
    return render_template('policies.html')

# API Routes
@app.route('/api/scan', methods=['POST'])
def api_scan():
    if not dlp_engine:
        return jsonify({'error': 'dlp_engine_not_initialized'}), 500
        
    try:
        data = request.json or {}
        path = data.get('path')
        
        if not path:
            return jsonify({'error': 'missing_path', 'message': 'Path is required'}), 400
        
        # Validate path
        normalized_path = normalize_and_verify_path(path)
        
        # Perform scan
        results = dlp_engine.scan_target(normalized_path)
        
        return jsonify({
            'success': True,
            'results': results,
            'scanned_path': normalized_path
        })
        
    except Exception as e:
        app.logger.error(f"Scan error: {str(e)}")
        return jsonify({'error': 'scan_failed', 'message': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    if not dlp_engine:
        return jsonify({'error': 'dlp_engine_not_initialized'}), 500
        
    try:
        stats = dlp_engine.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/clear', methods=['POST'])
def api_clear_alerts():
    if not dlp_engine:
        return jsonify({'error': 'dlp_engine_not_initialized'}), 500
        
    try:
        if hasattr(dlp_engine, 'security_alerts'):
            dlp_engine.security_alerts.clear()
        return jsonify({'success': True, 'message': 'Alerts cleared'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/monitor/start', methods=['POST'])
def api_monitor_start():
    try:
        data = request.json or {}
        path = data.get('path')
        
        if not path:
            return jsonify({'error': 'missing_path', 'message': 'Path is required'}), 400
        
        normalized_path = normalize_and_verify_path(path)
        
        return jsonify({
            'success': True,
            'message': f'Monitoring started for {normalized_path}',
            'monitored_path': normalized_path
        })
        
    except Exception as e:
        return jsonify({'error': 'monitor_failed', 'message': str(e)}), 500

@app.route('/api/report/generate', methods=['POST'])
def api_generate_report():
    if not dlp_engine:
        return jsonify({'error': 'dlp_engine_not_initialized'}), 500
        
    try:
        report = dlp_engine.generate_report()
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def api_health():
    return jsonify({
        "status": "healthy", 
        "message": "Server is running",
        "dlp_engine": "initialized" if dlp_engine else "not_initialized"
    })

# Fallback route for missing templates
@app.errorhandler(404)
def not_found(e):
    return """
    <html>
    <head><title>DLP Scanner - Page Not Found</title></head>
    <body>
        <h1>DLP Security Scanner</h1>
        <p>Page not found, but the server is running!</p>
        <p>Available pages:</p>
        <ul>
            <li><a href="/dashboard">Dashboard</a></li>
            <li><a href="/scanner">Scanner</a></li>
            <li><a href="/monitor">Monitor</a></li>
            <li><a href="/alerts">Alerts</a></li>
            <li><a href="/reports">Reports</a></li>
            <li><a href="/api/health">API Health</a></li>
        </ul>
    </body>
    </html>
    """, 404

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('reports', exist_ok=True)
    os.makedirs('data/input', exist_ok=True)
    os.makedirs('data/output', exist_ok=True)
    
    print("Starting DLP Security Scanner...")
    print("Open http://localhost:5000 in your browser")
    print("Available routes:")
    print("  /dashboard - Main dashboard")
    print("  /scanner - File scanner")
    print("  /monitor - Monitoring")
    print("  /alerts - Security alerts")
    print("  /reports - Reports")
    print("  /api/health - API health check")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

@app.route('/text_reports')
def text_reports():
    return render_template('text_reports.html')

@app.route('/api/report/text', methods=['POST'])
def api_generate_text_report():
    """Generate and return a text format security report"""
    try:
        if not dlp_engine:
            return jsonify({'error': 'dlp_engine_not_initialized'}), 500
        
        data = request.json or {}
        scan_results = data.get('scan_results')
        
        text_report = dlp_engine.generate_text_report(scan_results)
        
        return jsonify({
            'success': True,
            'report': text_report,
            'format': 'text',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/report/text/detailed', methods=['POST'])
def api_generate_detailed_text_report():
    """Generate detailed text report for a specific scan"""
    try:
        if not dlp_engine:
            return jsonify({'error': 'dlp_engine_not_initialized'}), 500
        
        data = request.json or {}
        scan_results = data.get('scan_results', [])
        
        if not scan_results:
            return jsonify({'error': 'No scan results provided'}), 400
        
        detailed_report = dlp_engine.generate_detailed_scan_report(scan_results)
        
        return jsonify({
            'success': True,
            'report': detailed_report,
            'format': 'text',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/report/text/download', methods=['POST'])
def api_download_text_report():
    """Generate and download text report as file"""
    try:
        if not dlp_engine:
            return jsonify({'error': 'dlp_engine_not_initialized'}), 500
        
        data = request.json or {}
        scan_results = data.get('scan_results')
        report_type = data.get('type', 'summary')
        
        if report_type == 'detailed':
            report_content = dlp_engine.generate_detailed_scan_report(scan_results or [])
            filename = f"dlp_detailed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        else:
            report_content = dlp_engine.generate_text_report(scan_results)
            filename = f"dlp_security_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Create response with text file
        from flask import Response
        response = Response(
            report_content,
            mimetype="text/plain",
            headers={
                "Content-Disposition": f"attachment;filename={filename}",
                "Content-Type": "text/plain; charset=utf-8"
            }
        )
        
        return response
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return """
    <html>
    <head><title>Text Reports - DLP Scanner</title></head>
    <body>
        <h1>Text Reports</h1>
        <p>This page is working! Text report functionality will be available soon.</p>
        <a href="/">Back to Dashboard</a>
    </body>
    </html>
    """
