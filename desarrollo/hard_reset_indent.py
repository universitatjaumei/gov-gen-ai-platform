
import sys

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
indent_level = 0
indent_size = 4

# Anchors: these strings indicate a specific indentation level regardless of previous lines.
anchors = {
    "def flows_page_content": 0,
    "class FlowsState": 1,
    "def __init__": 2,
    "async def load_flows": 1,
    "def flow_list": 1,
    "def flow_editor": 1,
    "async def edit_flow": 1,
    "async def delete_flow": 1,
    "def new_flow": 1,
    "async def on_atom_selected": 1,
    "@ui.refreshable": -1, # special case: match next line
    "def render_root": 1
}

# Block starters that increment indent
block_starters = ["def ", "class ", "if ", "elif ", "else:", "with ", "try:", "except ", "finally:", "for ", "while ", "async def "]

for i, line in enumerate(lines):
    stripped = line.strip()
    if not stripped:
        new_lines.append("\n")
        continue

    # Search for anchors
    found_anchor = False
    for anchor, level in anchors.items():
        if stripped.startswith(anchor):
            if level == -1: # Decorator
                # Look ahead for next actual code line's level
                for k in range(i+1, len(lines)):
                    next_stripped = lines[k].strip()
                    if not next_stripped or next_stripped.startswith("@"): continue
                    # Find if the next line is an anchor
                    found_next_anchor = False
                    for next_anchor, next_level in anchors.items():
                        if next_stripped.startswith(next_anchor):
                            indent_level = next_level
                            found_next_anchor = True
                            break
                    if not found_next_anchor:
                        # Fallback: if next line is a block starter but not an anchor, keep current?
                        # This is tricky. Let's assume most decorated things are anchors here.
                        pass
                    break
            else:
                indent_level = level
            found_anchor = True
            break
    
    # Handle dedent for structural keywords
    if any(stripped.startswith(x) for x in ["elif ", "else:", "except ", "except:", "finally:"]):
        indent_level = max(0, indent_level - 1)

    # Re-indent
    reindented = " " * (indent_level * indent_size) + stripped + "\n"
    new_lines.append(reindented)

    # Increment level if this is a block starter
    if any(stripped.startswith(x) for x in block_starters) and stripped.endswith(":"):
        indent_level += 1

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
