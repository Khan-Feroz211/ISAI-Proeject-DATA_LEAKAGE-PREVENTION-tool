import sys
import os
sys.path.insert(0, os.getcwd())

print("🔍 Debugging Text Reports Feature")
print("=" * 50)

try:
    # Try to import app_fixed.py
    from app_fixed import app
    
    print("✅ Successfully imported app_fixed.py")
    
    # Check if text_reports route exists
    with app.test_request_context():
        try:
            from flask import url_for
            url = url_for('text_reports')
            print(f"✅ text_reports route found: {url}")
        except Exception as e:
            print(f"❌ text_reports route error: {e}")
    
    # Check if template exists
    import flask
    with app.app_context():
        try:
            template = flask.render_template('text_reports.html')
            print("✅ text_reports.html template exists")
        except Exception as e:
            print(f"❌ Template error: {e}")
    
    # List all routes
    print("\n📋 All routes in app_fixed.py:")
    routes_found = False
    for rule in app.url_map.iter_rules():
        if 'text_reports' in rule.endpoint or 'report' in rule.endpoint:
            print(f"  ✅ {rule.rule} -> {rule.endpoint}")
            routes_found = True
    
    if not routes_found:
        print("  ❌ No text report routes found!")
        
except Exception as e:
    print(f"❌ Failed to import app_fixed.py: {e}")
    print("Trying app.py instead...")
    
    try:
        from app import app
        print("✅ Successfully imported app.py")
    except Exception as e:
        print(f"❌ Failed to import app.py: {e}")

print("\n" + "=" * 50)
print("Run this script with: python3 debug_text_reports.py")
