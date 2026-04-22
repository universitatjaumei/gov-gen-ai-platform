import os
import ast
import re
from pathlib import Path
from collections import defaultdict

# --- Configuration ---
IGNORE_DIRS = {'.venv', '.git', '__pycache__', 'data', 'tmp', 'docs', 'styles', 'htmlcov', '_legacy_archive'}
IGNORE_EXTS = {'.db', '.log', '.pyc', '.pyo'}
TARGET_DIRS = ['client_app', 'server', 'shared']

class ProjectMapGenerator:
    def __init__(self, root_dir):
        self.root_dir = Path(root_dir)
        self.files = []
        self.symbols = defaultdict(list)
        self.dependencies = defaultdict(set)
        self.models = {}  # {name: file_path}
        self.endpoints = [] # List of (method, path, file)
        self.ui_routes = [] # List of (route, file)
        self.gaps = []
        self.todo_pattern = re.compile(r'#\s*(TODO|FIXME|XXX):?\s*(.*)', re.IGNORECASE)

    def scan_files(self):
        for target in TARGET_DIRS:
            target_path = self.root_dir / target
            if not target_path.exists():
                continue
            for root, dirs, filenames in os.walk(target_path):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for f in filenames:
                    if f.endswith('.py') and f not in IGNORE_EXTS:
                        self.files.append(Path(root) / f)

    def analyze_file(self, file_path):
        rel_path = file_path.relative_to(self.root_dir)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                tree = ast.parse(content)
        except Exception as e:
            self.gaps.append(f"⚠️ Error parsing {rel_path}: {str(e)}")
            return

        # Scan for TODOs/FIXMEs in comments
        for i, line in enumerate(content.splitlines()):
            match = self.todo_pattern.search(line)
            if match:
                self.gaps.append(f"⚠️ {match.group(1)} in `{rel_path}:{i+1}`: {match.group(2).strip()}")

        for node in ast.walk(tree):
            # Extract Functions and Classes
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                docstring = ast.get_docstring(node) or "No docstring"
                self.symbols[rel_path].append({
                    'type': 'class' if isinstance(node, ast.ClassDef) else 'func',
                    'name': node.name,
                    'doc': docstring,
                    'line': node.lineno
                })
                
                # Check for empty logic (pass or NotImplementedError)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if len(node.body) == 1:
                        if isinstance(node.body[0], ast.Pass):
                            self.gaps.append(f"⚠️ Incomplete logic: `{rel_path}:{node.lineno}` function `{node.name}` has only `pass`")
                        elif isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Call) and getattr(node.body[0].value.func, 'id', '') == 'NotImplementedError':
                             # This is not exactly how NotImplementedError is usually raised, it's usually 'raise'
                             pass
                    for subnode in node.body:
                        if isinstance(subnode, ast.Raise) and isinstance(subnode.exc, ast.Call) and getattr(subnode.exc.func, 'id', '') == 'NotImplementedError':
                            self.gaps.append(f"⚠️ Incomplete logic: `{rel_path}:{node.lineno}` function `{node.name}` raises `NotImplementedError`")

            # Extract Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.dependencies[rel_path].add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self.dependencies[rel_path].add(node.module)

            # Detect Pydantic/SQLModel models
            if isinstance(node, ast.ClassDef):
                is_model = False
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id in ('BaseModel', 'SQLModel'):
                        is_model = True
                    elif isinstance(base, ast.Attribute) and base.attr in ('BaseModel', 'SQLModel'):
                        is_model = True
                if is_model:
                    self.models[node.name] = rel_path

            # Detect FastAPI Endpoints
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr in ('get', 'post', 'put', 'delete', 'patch'):
                            # Simple heuristic for route
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                self.endpoints.append({
                                    'method': decorator.func.attr.upper(),
                                    'path': decorator.args[0].value,
                                    'file': rel_path
                                })

            # Detect NiceGUI Routes (heuristic)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                        if decorator.func.attr == 'page':
                            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                self.ui_routes.append({
                                    'path': decorator.args[0].value,
                                    'file': rel_path
                                })

    def generate_report(self):
        output = "# Project Map and Diagnostics (MAP.md)\n\n"
        
        # 1. Dependency Graph (Mermaid)
        output += "## Dependency Graph: Shared Usage\n"
        output += "```mermaid\ngraph TD\n"
        output += "  Shared[shared/automatia_shared]\n"
        
        consumers = set()
        for file, deps in self.dependencies.items():
            if any('automatia_shared' in d for d in deps):
                component = str(file).split(os.sep)[0]
                if component in ('client_app', 'server'):
                    consumers.add(component)
        
        for c in consumers:
            output += f"  {c} --> Shared\n"
        output += "```\n\n"

        # 2. Symbols Mapping
        output += "## Symbols Registry\n"
        for folder in TARGET_DIRS:
            output += f"### {folder.capitalize()}\n"
            folder_files = [f for f in self.symbols if str(f).startswith(folder)]
            for f in sorted(folder_files):
                output += f"#### `{f}`\n"
                for s in self.symbols[f]:
                    emoji = "📦" if s['type'] == 'class' else "⚙️"
                    output += f"- {emoji} **{s['name']}** (line {s['line']}): {s['doc'].splitlines()[0] if s['doc'] else 'No description'}\n"
            output += "\n"

        # 3. Data Flow: Models
        output += "## Data Flow: Models & Schemas\n"
        output += "| Model | Definition File | Usage Samples |\n"
        output += "| :--- | :--- | :--- |\n"
        for model_name, def_file in self.models.items():
            usages = []
            for usage_file, deps in self.dependencies.items():
                # This is a very rough heuristic for usage
                try:
                    with open(self.root_dir / usage_file, 'r', encoding='utf-8') as f:
                        if model_name in f.read():
                            usages.append(f"`{usage_file}`")
                except:
                    pass
            output += f"| {model_name} | `{def_file}` | {', '.join(usages[:3])}{'...' if len(usages) > 3 else ''} |\n"
        output += "\n"

        # 4. Gaps and Inconsistencies
        output += "## ⚠️ Gaps and Inconsistencies\n"
        
        # Incomplete logic
        incomplete = [g for g in self.gaps if 'Incomplete logic' in g or 'TODO' in g or 'FIXME' in g]
        if incomplete:
            output += "### Incomplete Logic\n"
            for g in incomplete:
                output += f"- {g}\n"
        
        # UI/Backend Disconnect
        output += "### UI/Backend Connectivity\n"
        # Heuristic: match paths between self.endpoints and self.ui_routes
        # In the client, it's more likely calling the API via a client, not having same paths.
        # But the prompt says: "endpoints in server that don't have a route/component in client"
        # This is hard to detect perfectly. I'll list server endpoints and see if they appear in any client_app file.
        
        disconnected = []
        client_files_content = ""
        for cf in [f for f in self.files if str(f.relative_to(self.root_dir)).startswith('client_app')]:
            try:
                with open(cf, 'r', encoding='utf-8') as f:
                    client_files_content += f.read()
            except:
                pass
        
        for ep in self.endpoints:
            # Check if path is used in client_app
            if ep['path'] not in client_files_content:
                disconnected.append(f"⚠️ Endpoint `{ep['method']} {ep['path']}` (in `{ep['file']}`) seems to have no caller in `client_app`")
        
        if disconnected:
            for d in disconnected:
                output += f"- {d}\n"
        else:
            output += "No obvious UI/Backend disconnects found (based on path string matching).\n"

        # Vacant contracts
        vacant = []
        for model_name, def_file in self.models.items():
            if str(def_file).startswith('shared'):
                is_used = False
                for usage_file, deps in self.dependencies.items():
                    if str(usage_file).startswith(('client_app', 'server')):
                         try:
                            with open(self.root_dir / usage_file, 'r', encoding='utf-8') as f:
                                if model_name in f.read():
                                    is_used = True
                                    break
                         except:
                            pass
                if not is_used:
                    vacant.append(f"⚠️ Vacant model `{model_name}` in `{def_file}` (defined in shared but unused by apps)")

        if vacant:
            output += "### Vacant Contracts\n"
            for v in vacant:
                output += f"- {v}\n"

        return output

    def run(self):
        print("Scanning files...")
        self.scan_files()
        print(f"Found {len(self.files)} files. Analyzing...")
        for f in self.files:
            self.analyze_file(f)
        print("Generating report...")
        report = self.generate_report()
        with open(self.root_dir / 'MAP.md', 'w', encoding='utf-8') as f:
            f.write(report)
        print("Done! MAP.md generated.")

if __name__ == "__main__":
    generator = ProjectMapGenerator(os.getcwd())
    generator.run()
