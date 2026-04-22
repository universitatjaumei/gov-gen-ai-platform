
import io

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
inside_extraction_block = False
base_indent = ""

for i, line in enumerate(lines):
    # Detect start of extraction block
    if "if wizard_type == 'EXTRACTION':" in line:
        inside_extraction_block = True
        # Calculate base indentation from the 'if' line
        # Assuming space indentation
        leading_spaces = len(line) - len(line.lstrip())
        base_indent = " " * leading_spaces
        
        new_lines.append(line) # Keep the 'if' line as is
        
        # Inject the entire corrected block content here
        new_lines.append(f"{base_indent}    from client_app.app.ui.components.wizards.extraction_wizard import render_extraction_wizard\n")
        new_lines.append(f"\n")
        new_lines.append(f"{base_indent}    def on_extraction_created(resource_id):\n")
        new_lines.append(f"{base_indent}        step.config['config_id'] = resource_id\n")
        new_lines.append(f"{base_indent}        ui.notify(t('wizard_success'), type='positive')\n")
        new_lines.append(f"{base_indent}        wizard_container.close()\n")
        new_lines.append(f"{base_indent}        fs.update_validation_state()\n")
        new_lines.append(f"{base_indent}        render_tabbed_view.refresh()\n")
        new_lines.append(f"\n")
        new_lines.append(f"{base_indent}    render_extraction_wizard(on_save=on_extraction_created, context=prev_output)\n")
        
        continue
        
    if inside_extraction_block:
        # Check if we have exited the block
        # Heuristic: looking for the next 'elif' or equivalent dedent
        stripped = line.strip()
        if "elif wizard_type == 'CUSTOM_SCRIPT':" in line:
            inside_extraction_block = False
            # Force correct indentation for elif
            new_lines.append(f"{base_indent}elif wizard_type == 'CUSTOM_SCRIPT':\n")
        
        # If still inside, we SKIP the original lines because we injected the corrected block above
        continue

    # Outside block, keep lines as is
    new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
