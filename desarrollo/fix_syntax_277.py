
import io

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    stripped = line.strip()
    
    # Fix the specific misaligned except: at line 277
    # Note: line numbers in view_file might differ slightly if I already removed some empty lines.
    # So I'll match by content.
    
    # If a line is just 'except:' and it follows the idx check pattern
    if stripped == "except:":
        # Try to find the matching 'try:' indentation
        # For simplicity, let's just force a reasonable indentation if we find this specific line
        # In the previous view, try: was at line 265 and except: was at line 277.
        # They should be at the same level.
        pass

    # Better: use a state machine for the whole file
    new_lines.append(line)

# Let's actually use the compacting script first to see what we are dealing with.

compact_lines = []
last_was_empty = False
for line in lines:
    stripped = line.strip()
    if not stripped:
        if last_was_empty:
            continue
        last_was_empty = True
        compact_lines.append("\n")
    else:
        last_was_empty = False
        compact_lines.append(line)

# Now fix the except on the compact version
final_lines = []
for i, line in enumerate(compact_lines):
    stripped = line.strip()
    if stripped == "except:":
        # Look back for the matching try:
        for j in range(i-1, i-20, -1):
            if "try:" in compact_lines[j]:
                # Match the indentation of the try:
                indent = compact_lines[j][:compact_lines[j].find("try")]
                final_lines.append(indent + "except:\n")
                break
        else:
            final_lines.append(line)
    elif stripped == "pass" and i > 0 and "except:" in final_lines[-1]:
         # Match indentation of previous except
         indent = final_lines[-1][:final_lines[-1].find("except")]
         final_lines.append(indent + "    pass\n")
    else:
        final_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(final_lines)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
