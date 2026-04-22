
import sys
import re

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

def get_indent_count(l):
    return len(l) - len(l.lstrip())

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
indent_level = 0
indent_size = 4

# Exhaustive list of functions that SHOULD be at level 1 (inside flows_page_content)
level_1_functions = [
    "def FlowsState",
    "async def load_flows",
    "def new_flow",
    "def edit_flow",
    "async def delete_flow",
    "async def on_atom_selected",
    "def render_root",
    "def open_resource_wizard",
    "async def open_atom_drawer",
    "def load_wizard",
    "def add_step",
    "def remove_step",
    "def header_buttons",
    "def render_tabbed_view",
    "def render_steps",
    "def flow_list",
    "def flow_editor",
    "def on_config_change"
]

# Anchors for Level 0
level_0_anchors = ["def flows_page_content", "class FavoriteFlow"]

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append("\n")
        continue

    # 1. Detect if this line is a function definition and force its level
    forced_level = None
    
    if any(stripped.startswith(f) for f in level_1_functions):
        forced_level = 1
    elif any(stripped.startswith(f) for f in level_0_anchors):
        forced_level = 0
    elif stripped.startswith("@ui.refreshable"):
        # Look ahead for the function it decorates
        for k in range(i+1, min(len(lines), i+3)):
            ns = lines[k].strip()
            if any(ns.startswith(f) for f in level_1_functions):
                forced_level = 1
                break
            if any(ns.startswith(f) for f in level_0_anchors):
                forced_level = 0
                break
    
    if forced_level is not None:
        indent_level = forced_level
    
    # 2. Structural keywords for dedent
    if any(stripped.startswith(x) for x in ["elif ", "else:", "except ", "except:", "finally:"]):
        # Temporarily dedent for the current line
        current_indent = max(0, indent_level - 1)
    else:
        current_indent = indent_level

    # 3. Apply indentation
    new_lines.append(" " * (current_indent * indent_size) + stripped + "\n")

    # 4. Increment indentation for block starters
    if stripped.endswith(":") and any(stripped.startswith(x) for x in ["def ", "class ", "if ", "elif ", "else:", "with ", "try:", "except ", "finally:", "for ", "while ", "async def "]):
        indent_level += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# One last pass for specifically known broken block in load_flows
with open(file_path, 'r', encoding='utf-8') as f:
    final_lines = f.readlines()

very_final_lines = []
for i, line in enumerate(final_lines):
    stripped = line.strip()
    if "async with AsyncSession(client_engine) as session:" in stripped:
        very_final_lines.append(line)
        continue
    
    if i > 0 and "async with AsyncSession(client_engine) as session:" in final_lines[i-1]:
        if get_indent_count(line) <= get_indent_count(final_lines[i-1]):
            very_final_lines.append(" " * (get_indent_count(final_lines[i-1]) + 4) + stripped + "\n")
            continue
            
    very_final_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(very_final_lines)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
