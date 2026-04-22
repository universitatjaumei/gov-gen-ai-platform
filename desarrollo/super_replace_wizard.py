
import re

file_path = r"C:\Users\fabra\Documents\AutomatIA\client_app\app\ui\flows_page.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Correct version of the function
new_function = """
    def open_resource_wizard(step, wizard_type):
        wizard_container.clear()
        wizard_container.open()
        
        with wizard_container:
            ui.label(t('create_new_resource')).classes('text-xl font-bold mb-4')
            
            # Wizard Context: Previous Step Output (Simple heuristic)
            prev_output = None
            try:
                idx = fs.current_flow.steps.index(step)
                if idx > 0:
                    prev_step = fs.current_flow.steps[idx-1]
                    prev_output = f"Output from {prev_step.name}"
            except:
                pass
            
            if wizard_type == 'EXTRACTION':
                from client_app.app.ui.components.wizards.extraction_wizard import render_extraction_wizard
                
                def on_extraction_created(resource_id):
                    step.config['config_id'] = resource_id
                    ui.notify(t('wizard_success'), type='positive')
                    wizard_container.close()
                    fs.update_validation_state()
                    render_tabbed_view.refresh()
                
                render_extraction_wizard(on_save=on_extraction_created, context=prev_output)
                
            elif wizard_type == 'CUSTOM_SCRIPT':
                from client_app.app.ui.components.wizards.script_wizard import render_script_wizard
                
                def on_script_created(resource_id):
                    step.config['config_id'] = resource_id
                    ui.notify(t('wizard_success'), type='positive')
                    wizard_container.close()
                    fs.update_validation_state()
                    render_tabbed_view.refresh()
                
                render_script_wizard(on_save=on_script_created, context=prev_output)
"""

# Find the start of the function and replace until next major block
# Heuristic pattern to match the mangled start
start_pattern = r"\s*def\s+open_resource_wizard\s*\(step,\s*wizard_type\):"
# End pattern: next async def or top level comment or next anchor
end_pattern = r"\s*# --- ACTIONS ---"

# We split the content and replace the middle part
split_start = re.search(start_pattern, content)
split_end = re.search(end_pattern, content)

if split_start and split_end:
    new_content = content[:split_start.start()] + new_function + content[split_end.start():]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Function replaced successfully")
else:
    print(f"Could not find patterns: Start={bool(split_start)}, End={bool(split_end)}")

import py_compile
try:
    py_compile.compile(file_path, doraise=True)
    print("Compilation successful")
except Exception as e:
    print(f"Compilation failed: {e}")
