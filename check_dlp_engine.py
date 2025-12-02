try:
    from dlp_engine import DLPEngine
    
    # Test if required methods exist
    config = {}
    engine = DLPEngine(config)
    
    required_methods = ['get_stats', 'scan_target', 'generate_report', 'get_health_status']
    missing_methods = []
    
    for method in required_methods:
        if hasattr(engine, method):
            print(f"✓ {method} exists")
        else:
            missing_methods.append(method)
            print(f"✗ {method} missing")
    
    if missing_methods:
        print(f"\nMissing methods: {missing_methods}")
    else:
        print("\n✓ All required methods exist!")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
