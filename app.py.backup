from flask import Flask, render_template, request, jsonify
return jsonify({'error': 'scan_failed', 'message': str(e)}), 500


return jsonify(results)


@app.route('/api/stats', methods=['GET'])
def api_stats():
return jsonify(dlp_engine.get_stats())


@app.route('/api/alerts/clear', methods=['POST'])
def api_clear_alerts():
dlp_engine.security_alerts.clear()
return jsonify({'success': True, 'message': 'Alerts cleared'})


@app.route('/api/monitor/start', methods=['POST'])
def api_monitor_start():
data = request.json or {}
path = data.get('path')
if not path:
return jsonify({'error': 'missing_path'}), 400


try:
path = normalize_and_verify_path(path)
except Exception as e:
return jsonify({'error': 'invalid_path', 'message': str(e)}), 400


try:
monitor.monitor_path(path)
except FileNotFoundError as e:
return jsonify({'error': 'not_found', 'message': str(e)}), 404
except PermissionError as e:
return jsonify({'error': 'permission_denied', 'message': str(e)}), 403
except Exception as e:
return jsonify({'error': 'monitor_failed', 'message': str(e)}), 500


return jsonify({'success': True, 'message': f'Monitoring started for {path}'})


@app.route('/api/monitor/stop', methods=['POST'])
def api_monitor_stop():
monitor.stop_all()
return jsonify({'success': True, 'message': 'All monitors stopped'})


@app.route('/api/monitor/status', methods=['GET'])
def api_monitor_status():
return jsonify({'running': monitor.is_running()})


# Start a default monitor for user's home directory (non-root) on startup if permission allows
def start_default_monitor():
try:
home = os.path.expanduser('~')
# Do not monitor root or protected dirs automatically
if home and os.path.exists(home):
monitor.monitor_path(home)
except Exception:
pass


if __name__ == '__main__':
# start default monitor in a background thread so Flask can run
t = threading.Thread(target=start_default_monitor, daemon=True)
t.start()
app.run(host='0.0.0.0', port=5000, debug=False)