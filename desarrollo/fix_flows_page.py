
import io

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []

for line in lines:
    stripped = line.strip()
    
    # Force specific lines to have correct indentation
    if "async def open_config_drawer" in stripped:
        new_lines.append("    async def open_config_drawer(step):\n")
        continue

    # Identify lines that likely belong to open_config_drawer and force 8 spaces
    if "app_state.set_editing_step" in stripped:
         new_lines.append("        app_state.set_editing_step(step, fs.current_flow)\n")
         continue
    if "fs.current_editing_step_index =" in stripped:
         new_lines.append(f"        {stripped}\n")
         continue
    if "fs.current_view =" in stripped:
         new_lines.append(f"        {stripped}\n")
         continue
    if "layout_manager.enter_design_mode" in stripped:
         new_lines.append(f"        {stripped}\n")
         continue
    if "render_tabbed_view.refresh()" in stripped:
         new_lines.append(f"        {stripped}\n")
         continue
    if "def on_config_change():" in stripped:
         new_lines.append(f"        {stripped}\n")
         continue
    if "fs.update_validation_state()" in stripped:
         new_lines.append(f"            {stripped}\n")
         continue
    if "header_buttons.refresh()" in stripped:
         new_lines.append(f"            {stripped}\n")
         continue
    if "app_state.on_step_change =" in stripped:
         new_lines.append(f"        {stripped}\n")
         continue
     
    # Pass through other lines
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
