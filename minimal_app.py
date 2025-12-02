from flask import Flask, jsonify, render_template_string
import os

app = Flask(__name__)

# Create basic HTML template
basic_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>DLP Scanner</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        nav { background: #333; padding: 1rem; }
        nav a { color: white; margin: 0 1rem; text-decoration: none; }
        .container { max-width: 1200px; margin: 0 auto; }
    </style>
</head>
<body>
    <nav>
        <a href="/">Home</a>
        <a href="/api/health">Health</a>
    </nav>
    <div class="container">
        <h1>DLP Security Scanner</h1>
        <p>Application is running!</p>
        <p>If you can see this, the Flask server is working.</p>
    </div>
</body>
</html>
'''

@app.route('/')
def home():
    return render_template_string(basic_html)

@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "message": "Server is running"})

if __name__ == '__main__':
    print("Starting minimal Flask application...")
    print("Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=True)
