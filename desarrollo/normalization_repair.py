
import sys

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

def get_indent_count(l):
    return len(l) - len(l.lstrip())

# List of functions that MUST be at level 1 (inside flows_page_content)
level_1_hooks = [
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
    "def on_config_change",
    "async def start_up",
    "async def handle_initial_load",
    "def set_mode",
    "def render_steps_to_container",
    "def render_single_step",
    "def render_diagram_to_container"
]

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
indent_stack = [0]
indent_size = 4

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append("\n")
        continue

    # 1. Anchor Check
    is_anchor = False
    
    # Check for level 0 anchor
    if stripped.startswith("def flows_page_content"):
        indent_stack = [0]
        is_anchor = True
    elif any(stripped.startswith(h) for h in level_1_hooks):
        indent_stack = [4]
        is_anchor = True
    elif stripped.startswith("@ui.refreshable"):
        # Look ahead for anchor
        for k in range(i+1, min(len(lines), i+3)):
            ns = lines[k].strip()
            if any(ns.startswith(h) for h in level_1_hooks):
                indent_stack = [4]
                is_anchor = True
                break
    
    # 2. Structural Deduce (simplified)
    if not is_anchor:
        # Handle structural keywords that dedent
        if any(stripped.startswith(x) for x in ["elif ", "else:", "except ", "except:", "finally:"]):
             if len(indent_stack) > 1:
                 indent_stack.pop()
    
    # 3. Apply Current Indent
    current_indent = indent_stack[-1]
    new_line = " " * current_indent + stripped + "\n"
    new_lines.append(new_line)
    
    # 4. Handle block starters (increment)
    if not is_anchor:
        if stripped.endswith(":") and any(stripped.startswith(x) for x in ["def ", "class ", "if ", "elif ", "else:", "with ", "try:", "except ", "finally:", "for ", "while ", "async def "]):
            indent_stack.append(current_indent + 4)
    else:
        # After an anchor, we increment because we are now INSIDE the anchor
        if stripped.endswith(":"):
            indent_stack.append(indent_stack[-1] + 4)

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
