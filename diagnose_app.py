import sys
import os

print("Python Application Diagnostics")
print("=" * 50)

# Check Python version
print(f"Python version: {sys.version}")

# Check current directory
print(f"Current directory: {os.getcwd()}")
print(f"Files in directory: {[f for f in os.listdir('.') if f.endswith('.py')]}")

# Try to import the app
try:
    from app import app
    print("✓ Successfully imported app")
    
    # Check routes
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f"  {rule}")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    # Try to identify the specific import error
    try:
        import app
    except Exception as ex:
        print(f"Detailed error: {ex}")
        
except Exception as e:
    print(f"❌ Other error: {e}")
    import traceback
    traceback.print_exc()

print("\\nTo start the application, run: python3 app.py")
