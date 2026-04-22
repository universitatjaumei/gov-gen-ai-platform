
import sys

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

# Level 1 anchors (Direct children of flows_page_content)
level_1_hooks = [
    "class FlowsState",
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
    "def render_diagram_to_container",
    "def on_config_change",
    "async def open_scheduler_dialog",
    "def execute_flow",
    "def toggle_favorite",
    "def save_current_flow",
    "def generate_ai_proposal",
    "def render_config",
    "async def save_schedule"
]

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
indent_level = 0
indent_size = 4

# Keywords that start a block
starters = ["def ", "async def ", "class ", "if ", "elif ", "else:", "try:", "except ", "except:", "finally:", "with ", "async with ", "for ", "async for ", "while "]
# Keywords that specifically match a partner (dedenters)
dedenters = ["elif ", "else:", "except ", "except:", "finally:"]

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped: continue
    
    code_part = stripped.split('#')[0].strip()
    
    # 1. Identify Level based on Anchors
    if stripped.startswith("def flows_page_content"):
        indent_level = 0
    elif any(stripped.startswith(h) for h in level_1_hooks):
        indent_level = 1
    elif stripped.startswith("@ui.refreshable"):
        # Look ahead for anchor
        for k in range(i+1, min(len(lines), i+3)):
            ns = lines[k].strip()
            if any(ns.startswith(h) for h in level_1_hooks):
                indent_level = 1
                break
    
    # 2. Handle Dedenters (before writing the line)
    if any(stripped.startswith(x) for x in dedenters):
        # We assume dedenters belong to the nearest block above
        # This is a bit simplified but we use anchors to reset to safe levels.
        # Let's see... if it's a dedenter, it should be at indent_level - 1 
        # UNLESS we just reset to an anchor.
        # Actually, let's just use the current indent_level as 'inside block'
        # and if we see a dedenter, we dedent.
        indent_level = max(0, indent_level - 1)

    # 3. Apply indentation
    new_line = " " * (indent_level * indent_size) + stripped + "\n"
    new_lines.append(new_line)

    # 4. Handle block starters (for the NEXT line)
    if code_part.endswith(":"):
        if any(stripped.startswith(x) for x in starters):
            indent_level += 1
        else:
            # Multi-line with context or just a colon at end of line (like dictionaries)?
            # In this file, mostly UI elements like 'with ui.row():'
            if stripped.startswith("with ") or stripped.startswith("async with "):
                 indent_level += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
