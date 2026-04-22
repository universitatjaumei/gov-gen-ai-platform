
import sys

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

def get_indent_count(l):
    return len(l) - len(l.lstrip())

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
indent_level = 0
indent_size = 4

# Anchors for flows_page.py
anchors = {
    "def flows_page_content": 0,
    "class FlowsState": 1,
    "def __init__": 2,
    "async def load_flows": 1,
    "def new_flow": 1,
    "def edit_flow": 1,
    "async def delete_flow": 1,
    "async def on_atom_selected": 1,
    "def render_root": 1,
    "def open_resource_wizard": 1,
    "async def open_atom_drawer": 1,
    "header_buttons =": 1,
}

block_starters = ["def ", "class ", "if ", "elif ", "else:", "with ", "try:", "except ", "finally:", "for ", "while ", "async def "]
dedenters = ["elif ", "else:", "except ", "except:", "finally:"]

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append("\n")
        continue

    # 1. Handle Anchors
    for anchor, level in anchors.items():
        if stripped.startswith(anchor):
            indent_level = level
            break
    
    # 2. Handle structural keywords (dedent)
    is_structural = any(stripped.startswith(x) for x in dedenters)
    if is_structural:
        indent_level = max(0, indent_level - 1)

    # 3. Apply current indentation
    line = " " * (indent_level * indent_size) + stripped + "\n"
    new_lines.append(line)

    # 4. Handle block starters (increment)
    if stripped.endswith(":") and any(stripped.startswith(x) for x in block_starters):
        indent_level += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# SECOND PASS: Fix the specific drifting bodies
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
final_lines = []
force_next = False
target = 0

for line in lines:
    stripped = line.strip()
    if not stripped:
        final_lines.append("\n")
        continue
    
    if force_next:
         # If the line is NOT a dedenter, it MUST be indented
         if not any(stripped.startswith(x) for x in dedenters):
             if get_indent_count(line) < target:
                 line = " " * target + stripped + "\n"
         force_next = False
         
    if stripped.endswith(":") and any(stripped.startswith(x) for x in block_starters):
        force_next = True
        target = get_indent_count(line) + 4
        
    final_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(final_lines)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
