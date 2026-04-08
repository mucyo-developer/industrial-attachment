#!/usr/bin/env python3
"""
Enhanced Web-based AI Chatbot with Multiple Capabilities
- Folder creation
- File creation with content
- Python virtual environment initialization
- Project template creation
"""

from flask import Flask, render_template, request, jsonify
import requests
import os
import re
import json
import subprocess
import sys
import platform
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

app = Flask(__name__)

class EnhancedChatbot:
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "qwen2.5:0.5b"):
        self.ollama_url = ollama_url
        self.model = model
        self.base_dir = Path.cwd()
        self.system = platform.system().lower()
        
        # Define dangerous system directories to protect
        self.protected_dirs = {
            'windows': [
                'C:\\Windows', 'C:\\Windows\\System32', 'C:\\Windows\\SysWOW64',
                'C:\\Program Files', 'C:\\Program Files (x86)', 'C:\\ProgramData',
                'C:\\Users\\All Users', 'C:\\Users\\Default', 'C:\\Users\\Default User'
            ],
            'linux': [
                '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/etc', '/boot', '/dev', '/proc', '/sys',
                '/lib', '/lib64', '/usr/lib', '/usr/lib64', '/root', '/var/log'
            ],
            'darwin': [  # macOS
                '/System', '/Library', '/usr/bin', '/usr/sbin', '/etc', '/bin', '/sbin',
                '/private/etc', '/private/var', '/cores'
            ]
        }
        
        # Common user directories that are generally safe
        self.safe_user_dirs = [
            'Desktop', 'Documents', 'Downloads', 'Pictures', 'Music', 'Videos',
            'Projects', 'Code', 'Development', 'Work', 'Personal'
        ]
        
    def call_ollama(self, prompt: str) -> str:
        """Make API call to Ollama"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            return f"Error connecting to Ollama: {e}"
    
    def detect_intent_and_extract_details(self, user_input: str) -> Optional[Dict[str, Any]]:
        """Use Qwen to detect intent and extract operation details"""
        prompt = f"""
Analyze this user request and determine what operation they want to perform.
Respond with JSON format containing the operation type and details.

User request: "{user_input}"

Possible operations:
1. "create_folder" - extract folder_name and folder_path (if specified)
2. "create_file" - extract file_name and file_content (if specified)
3. "create_venv" - extract venv_name and venv_path (if specified)
4. "create_project" - extract project_type and project_name and project_path (if specified)
5. "create_folder_structure" - extract structure_type and base_path
6. "chat" - if none of the above

Examples:
- "Create a folder called my-project" -> {{"operation": "create_folder", "folder_name": "my-project", "folder_path": ""}}
- "Create a folder called data in C:\\Users\\Student\\Documents" -> {{"operation": "create_folder", "folder_name": "data", "folder_path": "C:\\Users\\Student\\Documents"}}
- "Create a folder called projects on my Desktop" -> {{"operation": "create_folder", "folder_name": "projects", "folder_path": "Desktop"}}
- "Create a file called app.py with hello world code" -> {{"operation": "create_file", "file_name": "app.py", "file_content": "hello world code"}}
- "Initialize a Python virtual environment called venv" -> {{"operation": "create_venv", "venv_name": "venv", "venv_path": ""}}
- "Create a React project called my-app" -> {{"operation": "create_project", "project_type": "react", "project_name": "my-app", "project_path": ""}}
- "Create a web project structure in C:\\Projects" -> {{"operation": "create_folder_structure", "structure_type": "web", "base_path": "C:\\Projects"}}
- "What's the weather like?" -> {{"operation": "chat"}}

Rules:
- Always respond with valid JSON
- If file content is not specified, make it empty string
- For chat operations, only include operation type
- Clean up invalid characters from names
- Handle Windows paths (C:\\folder) and Unix paths (/home/user/folder)
- Handle relative paths (Desktop, Documents, Downloads)
- If path is not specified, use current directory

Respond with JSON only:
"""
        
        response = self.call_ollama(prompt)
        
        try:
            # Clean the response to extract JSON
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return result
        except json.JSONDecodeError:
            pass
        
        return {"operation": "chat"}
    
    def resolve_path(self, path_str: str) -> Path:
        """Resolve a path string to an absolute Path object"""
        if not path_str or path_str.strip() == "":
            return self.base_dir
        
        path_str = path_str.strip()
        
        # Handle special user folder names
        if path_str in self.safe_user_dirs:
            if self.system == 'windows':
                user_home = Path.home()
                return user_home / path_str
            else:
                user_home = Path.home()
                return user_home / path_str
        
        # Handle Windows paths
        if self.system == 'windows':
            # Handle absolute paths like C:\folder
            if re.match(r'^[A-Za-z]:', path_str):
                return Path(path_str)
            # Handle UNC paths like \\server\share
            elif path_str.startswith('\\\\'):
                return Path(path_str)
            # Handle relative paths
            else:
                return self.base_dir / path_str
        else:
            # Handle Unix/Linux/macOS absolute paths
            if path_str.startswith('/'):
                return Path(path_str)
            # Handle relative paths
            else:
                return self.base_dir / path_str
    
    def is_path_safe(self, path: Path) -> Tuple[bool, str]:
        """Check if a path is safe for folder creation"""
        try:
            # Convert to absolute path
            abs_path = path.resolve()
            
            # Check if path is in protected directories
            protected = self.protected_dirs.get(self.system, [])
            for protected_dir in protected:
                if abs_path.is_relative_to(Path(protected_dir)):
                    return False, f"Access denied: Cannot create folders in system directory '{protected_dir}'"
            
            # Check if we're trying to create in root directories (unless explicitly requested)
            if self.system == 'windows':
                # Allow creation in C:\ if explicitly requested, but warn
                if abs_path.parent == Path('C:\\'):
                    return True, "Warning: Creating directly in C:\\ drive"
            else:
                # Don't allow creation in / on Unix systems
                if abs_path.parent == Path('/'):
                    return False, "Access denied: Cannot create folders in root directory"
            
            return True, "Path is safe"
            
        except Exception as e:
            return False, f"Error validating path: {e}"
    
    def create_folder_enhanced(self, folder_name: str, folder_path: str = "") -> Tuple[bool, str]:
        """Create a folder with enhanced path handling"""
        is_valid, message = self.validate_name(folder_name, "Folder name")
        if not is_valid:
            return False, message
        
        try:
            # Resolve the target path
            target_path = self.resolve_path(folder_path)
            final_path = target_path / folder_name
            
            # Check if the path is safe
            is_safe, safety_message = self.is_path_safe(final_path)
            if not is_safe:
                return False, safety_message
            
            # Check if folder already exists
            if final_path.exists():
                if final_path.is_dir():
                    return False, f"Folder '{folder_name}' already exists at: {final_path}"
                else:
                    return False, f"A file with name '{folder_name}' already exists at: {final_path}"
            
            # Create parent directories if they don't exist
            final_path.mkdir(parents=True, exist_ok=False)
            
            return True, f"✅ Folder '{folder_name}' created successfully at: {final_path}"
            
        except PermissionError:
            return False, f"Permission denied: Cannot create folder '{folder_name}' at {target_path}"
        except Exception as e:
            return False, f"Error creating folder '{folder_name}': {e}"
    
    def create_folder_structure(self, structure_type: str, base_path: str) -> Tuple[bool, str]:
        """Create predefined folder structures"""
        base = self.resolve_path(base_path)
        
        # Check if base path is safe
        is_safe, safety_message = self.is_path_safe(base)
        if not is_safe:
            return False, safety_message
        
        structures = {
            'web': {
                'folders': ['src', 'public', 'assets', 'styles', 'scripts'],
                'description': 'Web development structure'
            },
            'python': {
                'folders': ['src', 'tests', 'docs', 'config', 'data'],
                'description': 'Python project structure'
            },
            'fullstack': {
                'folders': ['frontend', 'backend', 'shared', 'docs', 'deploy'],
                'description': 'Full-stack application structure'
            },
            'data': {
                'folders': ['raw_data', 'processed_data', 'models', 'notebooks', 'scripts'],
                'description': 'Data science project structure'
            }
        }
        
        if structure_type.lower() not in structures:
            available = ', '.join(structures.keys())
            return False, f"Unknown structure type '{structure_type}'. Available: {available}"
        
        structure = structures[structure_type.lower()]
        created_folders = []
        
        try:
            for folder in structure['folders']:
                folder_path = base / folder
                if not folder_path.exists():
                    folder_path.mkdir(parents=True, exist_ok=False)
                    created_folders.append(str(folder_path))
            
            return True, f"✅ {structure['description']} created at {base}\nFolders: {', '.join(structure['folders'])}"
            
        except Exception as e:
            return False, f"Error creating folder structure: {e}"
    
    def validate_name(self, name: str, name_type: str = "name") -> Tuple[bool, str]:
        """Validate folder/file/venv name for safety"""
        if not name:
            return False, f"{name_type} cannot be empty"
        
        # Check for reserved names
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        if name.upper() in reserved_names:
            return False, f"'{name}' is a reserved system name"
        
        # Check for invalid characters
        if re.search(r'[<>:"/\\|?*]', name):
            return False, f"{name_type} contains invalid characters"
        
        # Check length
        if len(name) > 255:
            return False, f"{name_type} too long (max 255 characters)"
        
        return True, "Valid name"
    
    def create_folder(self, folder_name: str) -> Tuple[bool, str]:
        """Safely create a folder"""
        is_valid, message = self.validate_name(folder_name, "Folder name")
        if not is_valid:
            return False, message
        
        try:
            folder_path = self.base_dir / folder_name
            
            if folder_path.exists():
                if folder_path.is_dir():
                    return False, f"Folder '{folder_name}' already exists"
                else:
                    return False, f"A file with name '{folder_name}' already exists"
            
            folder_path.mkdir(parents=True, exist_ok=False)
            return True, f"✅ Folder '{folder_name}' created successfully at: {folder_path}"
            
        except PermissionError:
            return False, f"Permission denied: Cannot create folder '{folder_name}'"
        except Exception as e:
            return False, f"Error creating folder '{folder_name}': {e}"
    
    def create_file(self, file_name: str, file_content: str = "") -> Tuple[bool, str]:
        """Create a file with content"""
        is_valid, message = self.validate_name(file_name, "File name")
        if not is_valid:
            return False, message
        
        try:
            file_path = self.base_dir / file_name
            
            if file_path.exists():
                return False, f"File '{file_name}' already exists"
            
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            return True, f"✅ File '{file_name}' created successfully at: {file_path}"
            
        except PermissionError:
            return False, f"Permission denied: Cannot create file '{file_name}'"
        except Exception as e:
            return False, f"Error creating file '{file_name}': {e}"
    
    def create_venv(self, venv_name: str) -> Tuple[bool, str]:
        """Create a Python virtual environment"""
        is_valid, message = self.validate_name(venv_name, "Virtual environment name")
        if not is_valid:
            return False, message
        
        try:
            venv_path = self.base_dir / venv_name
            
            if venv_path.exists():
                return False, f"Virtual environment '{venv_name}' already exists"
            
            # Create virtual environment
            subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], 
                         check=True, capture_output=True, text=True)
            
            return True, f"✅ Virtual environment '{venv_name}' created successfully at: {venv_path}\n💡 Activate it with: {venv_name}\\Scripts\\activate"
            
        except subprocess.CalledProcessError as e:
            return False, f"Error creating virtual environment: {e.stderr}"
        except Exception as e:
            return False, f"Error creating virtual environment '{venv_name}': {e}"
    
    def create_project(self, project_type: str, project_name: str) -> Tuple[bool, str]:
        """Create project templates"""
        is_valid, message = self.validate_name(project_name, "Project name")
        if not is_valid:
            return False, message
        
        try:
            project_path = self.base_dir / project_name
            
            if project_path.exists():
                return False, f"Project '{project_name}' already exists"
            
            if project_type.lower() == "flask":
                return self.create_flask_project(project_path, project_name)
            elif project_type.lower() == "react":
                return self.create_react_project(project_path, project_name)
            elif project_type.lower() == "python":
                return self.create_python_project(project_path, project_name)
            else:
                return False, f"Unknown project type: {project_type}. Supported: flask, react, python"
                
        except Exception as e:
            return False, f"Error creating project '{project_name}': {e}"
    
    def create_flask_project(self, project_path: Path, project_name: str) -> Tuple[bool, str]:
        """Create a Flask project template"""
        project_path.mkdir(parents=True, exist_ok=False)
        
        # Create app.py
        app_content = '''from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Flask!"

if __name__ == '__main__':
    app.run(debug=True)
'''
        
        with open(project_path / 'app.py', 'w') as f:
            f.write(app_content)
        
        # Create requirements.txt
        with open(project_path / 'requirements.txt', 'w') as f:
            f.write('Flask==2.3.3\n')
        
        # Create templates folder
        (project_path / 'templates').mkdir()
        
        return True, f"✅ Flask project '{project_name}' created successfully at: {project_path}"
    
    def create_react_project(self, project_path: Path, project_name: str) -> Tuple[bool, str]:
        """Create a React project template"""
        project_path.mkdir(parents=True, exist_ok=False)
        
        # Create package.json
        package_json = {
            "name": project_name,
            "version": "0.1.0",
            "private": True,
            "dependencies": {
                "react": "^18.2.0",
                "react-dom": "^18.2.0",
                "react-scripts": "5.0.1"
            },
            "scripts": {
                "start": "react-scripts start",
                "build": "react-scripts build",
                "test": "react-scripts test",
                "eject": "react-scripts eject"
            }
        }
        
        with open(project_path / 'package.json', 'w') as f:
            json.dump(package_json, f, indent=2)
        
        # Create src folder and basic files
        src_path = project_path / 'src'
        src_path.mkdir()
        
        # Create App.js
        app_js = '''import React from 'react';
import './App.css';

function App() {
  return (
    <div className="App">
      <header className="App-header">
        <h1>Hello, React!</h1>
      </header>
    </div>
  );
}

export default App;
'''
        
        with open(src_path / 'App.js', 'w') as f:
            f.write(app_js)
        
        # Create index.js
        index_js = '''import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
'''
        
        with open(src_path / 'index.js', 'w') as f:
            f.write(index_js)
        
        # Create basic CSS files
        with open(src_path / 'App.css', 'w') as f:
            f.write('.App { text-align: center; }\n.App-header { background-color: #282c34; padding: 20px; color: white; }\n')
        
        with open(src_path / 'index.css', 'w') as f:
            f.write('body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", sans-serif; }\n')
        
        # Create public folder and index.html
        public_path = project_path / 'public'
        public_path.mkdir()
        
        index_html = f'''<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{project_name}</title>
  </head>
  <body>
    <div id="root"></div>
  </body>
</html>
'''
        
        with open(public_path / 'index.html', 'w') as f:
            f.write(index_html)
        
        return True, f"✅ React project '{project_name}' created successfully at: {project_path}\n💡 Run 'npm install' and 'npm start' to begin"
    
    def create_python_project(self, project_path: Path, project_name: str) -> Tuple[bool, str]:
        """Create a basic Python project"""
        project_path.mkdir(parents=True, exist_ok=False)
        
        # Create main.py
        main_content = '''#!/usr/bin/env python3
"""
Main entry point for the application
"""

def main():
    print("Hello, Python Project!")

if __name__ == "__main__":
    main()
'''
        
        with open(project_path / 'main.py', 'w') as f:
            f.write(main_content)
        
        # Create requirements.txt
        with open(project_path / 'requirements.txt', 'w') as f:
            f.write('# Add your dependencies here\n')
        
        # Create README.md
        readme_content = f'''# {project_name}

A Python project.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```
'''
        
        with open(project_path / 'README.md', 'w') as f:
            f.write(readme_content)
        
        return True, f"✅ Python project '{project_name}' created successfully at: {project_path}"
    
    def get_chat_response(self, user_input: str) -> str:
        """Get regular chat response from Qwen"""
        prompt = f"""
You are a helpful AI assistant with file system and development capabilities. 
Respond naturally to this user request. Keep responses concise and friendly.

User: {user_input}
Assistant:"""
        
        return self.call_ollama(prompt)
    
    def process_message(self, user_input: str) -> dict:
        """Process user message and return response"""
        try:
            # Detect intent and extract details
            intent_data = self.detect_intent_and_extract_details(user_input)
            operation = intent_data.get("operation", "chat")
            
            if operation == "create_folder":
                folder_name = intent_data.get("folder_name", "")
                folder_path = intent_data.get("folder_path", "")
                success, message = self.create_folder_enhanced(folder_name, folder_path)
                return {
                    "type": "folder_creation",
                    "success": success,
                    "message": message,
                    "operation": "create_folder"
                }
            
            elif operation == "create_folder_structure":
                structure_type = intent_data.get("structure_type", "")
                base_path = intent_data.get("base_path", "")
                success, message = self.create_folder_structure(structure_type, base_path)
                return {
                    "type": "folder_structure_creation",
                    "success": success,
                    "message": message,
                    "operation": "create_folder_structure"
                }
            
            elif operation == "create_file":
                file_name = intent_data.get("file_name", "")
                file_content = intent_data.get("file_content", "")
                success, message = self.create_file(file_name, file_content)
                return {
                    "type": "file_creation",
                    "success": success,
                    "message": message,
                    "operation": "create_file"
                }
            
            elif operation == "create_venv":
                venv_name = intent_data.get("venv_name", "")
                success, message = self.create_venv(venv_name)
                return {
                    "type": "venv_creation",
                    "success": success,
                    "message": message,
                    "operation": "create_venv"
                }
            
            elif operation == "create_project":
                project_type = intent_data.get("project_type", "")
                project_name = intent_data.get("project_name", "")
                success, message = self.create_project(project_type, project_name)
                return {
                    "type": "project_creation",
                    "success": success,
                    "message": message,
                    "operation": "create_project"
                }
            
            else:  # chat
                response = self.get_chat_response(user_input)
                return {
                    "type": "chat",
                    "message": response,
                    "operation": "chat"
                }
                
        except Exception as e:
            return {
                "type": "error",
                "message": f"Error: {e}",
                "operation": "error"
            }

# Initialize chatbot
chatbot = EnhancedChatbot()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400
    
    response = chatbot.process_message(user_message)
    return jsonify(response)

@app.route('/health')
def health():
    """Check if Ollama is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            return jsonify({"status": "healthy", "ollama": "connected"})
        else:
            return jsonify({"status": "unhealthy", "ollama": "not_responding"}), 503
    except requests.exceptions.ConnectionError:
        return jsonify({"status": "unhealthy", "ollama": "not_connected"}), 503

if __name__ == '__main__':
    print("Starting AI Folder Chatbot Web Server...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
