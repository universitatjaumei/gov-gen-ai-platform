
import sys

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

def get_indent_count(l):
    return len(l) - len(l.lstrip())

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
force_indent = False
target_indent = 0

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append("\n")
        continue

    current_indent = get_indent_count(line)
    
    # If we are supposed to be inside a block, force the indent
    if force_indent:
        if current_indent <= target_indent - 4:
            # Re-indent to the expected level
            line = " " * target_indent + stripped + "\n"
        # Reset force_indent if we found a line with some indentation? 
        # No, keep forcing until we hit a structural keyword? 
        # Actually, just the *very next* non-empty line MUST be indented.
        force_indent = False

    # Check if this line starts a block
    if stripped.endswith(":"):
        force_indent = True
        target_indent = current_indent + 4
        
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# One more pass to fix specifically problematic nested blocks like on_extraction_created which might need more depth
# (This is a simplified approach, let's see if it works)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
