
import sys

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

def get_indent_count(l):
    return len(l) - len(l.lstrip())

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
try_stack = [] # To keep track of try levels
if_stack = []  # To keep track of if levels

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append("\n")
        continue

    # Identify structural keywords and their current indentation
    current_indent = get_indent_count(line)
    
    # 1. Handle TRY-EXCEPT-FINALLY
    if stripped.startswith("try:"):
        try_stack.append(current_indent)
    elif stripped.startswith("except ") or stripped.startswith("except:") or stripped.startswith("finally:"):
        if try_stack:
            target_indent = try_stack.pop()
            line = " " * target_indent + stripped + "\n"
        else:
            # If no try on stack, this is a floating except, which is a logic error
            # But let's at least keep it where it was or try to guess.
            pass
            
    # 2. Handle IF-ELIF-ELSE
    # This is more complex because IF blocks can end without an ELIF/ELSE.
    # So we only track IF if we see an ELIF/ELSE.
    # Actually, let's just use the current line as a guide.
    
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# One more pass to fix the specific line 264-270 block which is a known try/except
# using a very dumb but effective line-by-line fix for that area.
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

repaired = []
for i, line in enumerate(lines):
    s = line.strip()
    if s == "except:" and i > 0:
        # Check if preceding lines had a 'try:'
        for j in range(i-1, max(0, i-20), -1):
            if lines[j].strip() == "try:":
                # Found it! Match its indentation
                target = get_indent_count(lines[j])
                repaired.append(" " * target + "except:\n")
                break
        else:
            repaired.append(line)
    elif s == "else:" and i > 0:
        for j in range(i-1, max(0, i-20), -1):
             if lines[j].strip().startswith("if "):
                target = get_indent_count(lines[j])
                repaired.append(" " * target + "else:\n")
                break
        else:
            repaired.append(line)
    elif s.startswith("elif ") and i > 0:
        for j in range(i-1, max(0, i-20), -1):
             if lines[j].strip().startswith("if ") or lines[j].strip().startswith("elif "):
                target = get_indent_count(lines[j])
                repaired.append(" " * target + s + "\n")
                break
        else:
            repaired.append(line)
    else:
        repaired.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(repaired)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
