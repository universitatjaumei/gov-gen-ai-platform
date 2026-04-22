
import sys

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
indent_level = 0
indent_size = 4

block_starters = ["def ", "class ", "if ", "elif ", "else:", "with ", "try:", "except ", "finally:", "for ", "while ", "async def "]
block_enders = ["return", "pass", "break", "continue"]

def get_indent_count(line):
    return len(line) - len(line.lstrip())

# Heuristic-based indentation repair
for line in lines:
    stripped = line.strip()
    if not stripped:
        new_lines.append("\n")
        continue

    # Dedent for block starters that are part of the same level (elif, else, except, finally)
    if any(stripped.startswith(x) for x in ["elif ", "else:", "except ", "except:", "finally:"]):
        indent_level = max(0, indent_level - 1)

    # Apply current indentation
    new_line = " " * (indent_level * indent_size) + stripped + "\n"
    new_lines.append(new_line)

    # Increment indent level if line starts a block
    # and doesn't end on the same line (like a simple lambda or one-liner if)
    if any(stripped.startswith(x) for x in block_starters) and stripped.endswith(":"):
        indent_level += 1
    
    # Simple heuristic: if we see return/pass, we MIGHT need to dedent? 
    # Not necessarily, could be more lines in the same block.
    # So we don't automatically dedent on 'return'. 
    # Python relies on the *next* line's indentation.
    # This script is naive but should help align things better than the current mess.

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# One more pass to fix decorators
final_lines = []
for i, line in enumerate(new_lines):
    stripped = line.strip()
    if stripped.startswith("@"):
        # Decorators should match the indentation of the next def/class
        if i + 1 < len(new_lines):
            next_line = new_lines[i+1]
            next_indent = get_indent_count(next_line)
            final_lines.append(" " * next_indent + stripped + "\n")
            continue
    final_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(final_lines)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
