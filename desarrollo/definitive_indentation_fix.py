
import sys
import re

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

def get_indent_count(l):
    return len(l) - len(l.lstrip())

# List of functions that MUST be at level 1 (4 spaces)
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
indent_level = 0
indent_size = 4
max_indent = 40

# Structural keywords
block_starters = ["def ", "class ", "if ", "elif ", "else:", "with ", "try:", "except ", "finally:", "for ", "while ", "async def ", "async with ", "async for "]
dedenters = ["elif ", "elif(", "else:", "except ", "except:", "finally:"]

# Pass 1: Structural Deduction
structural_stack = []

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append("\n")
        continue

    # Comment-aware check
    code_part = stripped.split('#')[0].strip()
    is_block_starter = code_part.endswith(":") and any(stripped.startswith(x) for x in block_starters)

    is_anchor = False
    if stripped.startswith("def flows_page_content"):
        indent_level = 0
        structural_stack = []
        is_anchor = True
    elif any(stripped.startswith(h) for h in level_1_hooks):
        indent_level = 1
        structural_stack = []
        is_anchor = True
    elif stripped.startswith("@ui.refreshable"):
        for k in range(i+1, min(len(lines), i+3)):
            ns = lines[k].strip()
            if any(ns.startswith(h) for h in level_1_hooks):
                indent_level = 1
                structural_stack = []
                is_anchor = True
                break
    
    if not is_anchor:
        if any(stripped.startswith(x) for x in dedenters):
            if structural_stack:
                indent_level = structural_stack.pop()
            else:
                indent_level = max(1, indent_level - 1)

    # Force strict indent
    current_spaces = min(indent_level * indent_size, max_indent)
    new_line = " " * current_spaces + stripped + "\n"
    new_lines.append(new_line)

    if is_block_starter:
        if stripped.startswith(("if ", "try:", "with ", "async with ", "async for ", "for ", "while ")):
             structural_stack.append(indent_level)
        indent_level += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# Pass 2: Aggressive Partner Matching with large lookback
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

final_repaired = []
must_indent = False
target_indent = 0
lookback = 200

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        final_repaired.append("\n")
        continue

    current_indent = get_indent_count(line)
    
    if must_indent:
        if current_indent <= target_indent - 4:
            line = " " * target_indent + stripped + "\n"
            current_indent = target_indent
        must_indent = False

    code_part = stripped.split('#')[0].strip()

    # Alignment
    if stripped.startswith(("except ", "except:", "finally:")):
        for j in range(i-1, max(0, i - lookback), -1):
            if lines[j].strip().split('#')[0].strip() == "try:":
                line = " " * get_indent_count(lines[j]) + stripped + "\n"
                current_indent = get_indent_count(lines[j])
                break
    elif stripped.startswith(("else:", "elif ", "elif(")):
        for j in range(i-1, max(0, i - lookback), -1):
            prev_s = lines[j].strip().split('#')[0].strip()
            if prev_s.startswith("if ") or prev_s.startswith("elif"):
                line = " " * get_indent_count(lines[j]) + stripped + "\n"
                current_indent = get_indent_count(lines[j])
                break

    if code_part.endswith(":") and any(stripped.startswith(x) for x in block_starters):
        must_indent = True
        target_indent = current_indent + 4
        
    final_repaired.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(final_repaired)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
