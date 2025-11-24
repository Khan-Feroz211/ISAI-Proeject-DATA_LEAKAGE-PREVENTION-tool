from flask import Flask, request, render_template_string
import subprocess, sys
from pathlib import Path

DEFAULT_PATH = Path("./requirements.txt")

app = Flask(__name__)
req_path = DEFAULT_PATH

def load_requirements():
    if not req_path.exists():
        return []
    with req_path.open() as f:
        return [line.strip() for line in f if line.strip()]

def save_requirements(packages):
    req_path.write_text("\n".join(packages))

def install_packages(packages):
    if packages:
        cmd = [sys.executable, "-m", "pip", "install"] + packages
        subprocess.run(cmd)

TEMPLATE = """
<!doctype html>
<title>DLP Requirements Editor</title>
<h2>DLP Requirements Editor</h2>

<form method="post" action="/add">
  Add package: <input name="package">
  <input type="submit" value="Add">
</form>

<form method="post" action="/remove">
  <select name="remove_pkg" multiple size="10">
    {% for pkg in packages %}
      <option value="{{ pkg }}">{{ pkg }}</option>
    {% endfor %}
  </select>
  <input type="submit" value="Remove">
</form>

{% if message %}
<p><b>{{ message }}</b></p>
{% endif %}
"""

@app.route("/")
def home():
    return render_template_string(TEMPLATE, packages=load_requirements(), message=None)

@app.route("/add", methods=["POST"])
def add():
    pkg = request.form.get("package", "").strip()
    pkgs = load_requirements()
    if pkg:
        pkgs.append(pkg)
        save_requirements(pkgs)
    return render_template_string(TEMPLATE, packages=pkgs, message=f"Added: {pkg}")

@app.route("/remove", methods=["POST"])
def remove():
    to_remove = request.form.getlist("remove_pkg")
    pkgs = [p for p in load_requirements() if p not in to_remove]
    save_requirements(pkgs)
    return render_template_string(TEMPLATE, packages=pkgs, message="Removed selected.")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

