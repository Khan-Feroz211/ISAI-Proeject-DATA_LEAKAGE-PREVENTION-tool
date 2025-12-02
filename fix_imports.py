import re

# Read the current app.py
with open('app.py', 'r') as f:
    content = f.read()

# Check if dlp_engine is imported
if 'import dlp_engine' not in content and 'from dlp_engine' not in content:
    print("dlp_engine import is missing!")
    
    # Find where to insert the import (after other imports)
    lines = content.split('\n')
    new_lines = []
    import_added = False
    
    for line in lines:
        new_lines.append(line)
        # Add import after the last import statement
        if (line.startswith('import ') or line.startswith('from ')) and not import_added:
            # Check if next line is not an import
            next_line_index = lines.index(line) + 1
            if next_line_index < len(lines) and not lines[next_line_index].startswith(('import ', 'from ')):
                new_lines.append('from dlp_engine import DLPEngine')
                new_lines.append('')
                import_added = True
    
    # If we didn't find a good spot, add at the top
    if not import_added:
        new_lines.insert(0, 'from dlp_engine import DLPEngine')
        new_lines.insert(1, '')
    
    # Write the fixed content
    with open('app.py', 'w') as f:
        f.write('\n'.join(new_lines))
    print("Fixed app.py - added dlp_engine import")
else:
    print("dlp_engine import already exists")

# Also check if DLPEngine is initialized
if 'dlp_engine = DLPEngine' not in content:
    print("DLPEngine instance creation might be missing")
