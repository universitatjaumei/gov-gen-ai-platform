
import sys

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
indent_level = 0
indent_size = 4

# Expanded Anchors for flows_page.py
anchors = {
    "def flows_page_content": 0,
    "class FlowsState": 1,
    "def __init__": 2,
    "async def open_atom_drawer": 1,
    "def load_wizard": 1,
    "def open_resource_wizard": 1,
    "async def load_flows": 1,
    "def flow_list": 1,
    "def flow_editor": 1,
    "async def edit_flow": 1,
    "async def delete_flow": 1,
    "def new_flow": 1,
    "async def on_atom_selected": 1,
    "def render_root": 1,
    "render_tabbed_view =": 1, # This is a refreshable, but often at level 1
    "header_buttons =": 1,
    "wizard_container =": 1,
    "class FavoriteFlow": 0,
    "# ---": 1, # Sections are usually at level 1 inside the function
}

# Structural keywords for dedent
dedenters = ["elif ", "else:", "except ", "except:", "finally:"]
block_starters = ["def ", "class ", "if ", "elif ", "else:", "with ", "try:", "except ", "finally:", "for ", "while ", "async def "]

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append("\n")
        continue

    # Fix specific common issues before applying indentation
    if stripped.startswith("@ui.refreshable"):
        # Look ahead for indentation of what it decorates
        next_level = 1
        for k in range(i+1, min(len(lines), i+5)):
            ns = lines[k].strip()
            if not ns or ns.startswith("@"): continue
            for anchor, level in anchors.items():
                if ns.startswith(anchor):
                    next_level = level
                    break
            break
        indent_level = next_level
    
    # Check for anchors
    for anchor, level in anchors.items():
        if stripped.startswith(anchor):
            indent_level = level
            break
    
    # Dedent structural keywords
    if any(stripped.startswith(x) for x in dedenters):
        indent_level = max(0, indent_level - 1)

    # Apply indentation
    new_line = " " * (indent_level * indent_size) + stripped + "\n"
    new_lines.append(new_line)

    # Increment indent for block starters
    if any(stripped.startswith(x) for x in block_starters) and stripped.endswith(":"):
        indent_level += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# One more pass to clean up excessive empty lines
with open(file_path, 'r', encoding='utf-8') as f:
    final_lines = f.readlines()
    
very_final_lines = []
last_empty = False
for line in final_lines:
    if not line.strip():
        if last_empty: continue
        last_empty = True
    else:
        last_empty = False
    very_final_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(very_final_lines)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
