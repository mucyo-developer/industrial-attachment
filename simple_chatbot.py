#!/usr/bin/env python3
"""
Simple AI Chatbot with File Operations
- Normal conversation
- File and folder creation
- Project initialization (React, Python, Flask)
- Virtual environment creation
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

class SimpleChatbot:
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "qwen2.5:0.5b"):
        self.ollama_url = ollama_url
        self.model = model
        self.base_dir = Path.cwd()
        self.system = platform.system().lower()
        
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
    
    def detect_operation(self, user_input: str) -> Dict[str, Any]:
        """Simple operation detection using keywords and patterns"""
        user_lower = user_input.lower()
        
        # File creation patterns - check these FIRST
        if any(word in user_lower for word in ['create file', 'make file', 'new file', 'write file']):
            file_match = re.search(r'file\s+(?:called|named)\s+["\']?([^"\']+)["\']?', user_lower)
            if file_match:
                file_name = file_match.group(1).strip()
                # Extract content if specified
                content_match = re.search(r'(?:with|containing)\s+["\']?([^"\']+)["\']?', user_lower)
                file_content = content_match.group(1).strip() if content_match else ""
                return {"operation": "create_file", "file_name": file_name, "file_content": file_content}
        
        # Folder creation patterns - check these BEFORE generic chat
        elif any(word in user_lower for word in ['create folder', 'make folder', 'new folder', 'create directory', 'folder called', 'directory called']):
            # Try multiple patterns for folder name
            folder_name = ""
            
            # Pattern 1: "folder called project1"
            folder_match = re.search(r'(?:folder|directory)\s+(?:called|named)\s+["\']?([^"\']+)["\']?', user_lower)
            if folder_match:
                folder_name = folder_match.group(1).strip()
            
            # Pattern 2: "create folder project1"
            elif 'create folder' in user_lower:
                after_create = user_lower.split('create folder')[-1].strip()
                if after_create and len(after_create.split()) <= 3:  # Likely just the name
                    folder_name = after_create.strip(' "\'')
            
            # Pattern 3: "make folder project1"
            elif 'make folder' in user_lower:
                after_make = user_lower.split('make folder')[-1].strip()
                if after_make and len(after_make.split()) <= 3:  # Likely just the name
                    folder_name = after_make.strip(' "\'')
            
            # Pattern 4: "new folder project1"
            elif 'new folder' in user_lower:
                after_new = user_lower.split('new folder')[-1].strip()
                if after_new and len(after_new.split()) <= 3:  # Likely just the name
                    folder_name = after_new.strip(' "\'')
            
            if folder_name:
                # Extract location
                location_patterns = [
                    r'(?:in|on|at)\s+(?:the\s+)?(desktop|documents|downloads)',
                    r'(?:in|on|at)\s+([a-zA-Z]:\\[^\\]+)',
                    r'(?:in|on|at)\s+(?:the\s+)?([^\\\s]+)'
                ]
                folder_path = ""
                for pattern in location_patterns:
                    match = re.search(pattern, user_lower)
                    if match:
                        folder_path = match.group(1).strip()
                        break
                
                # Special handling for "desktop" mentions
                if 'desktop' in user_lower:
                    folder_path = "Desktop"
                
                return {"operation": "create_folder", "folder_name": folder_name, "folder_path": folder_path}
        
        # Virtual environment patterns
        elif any(word in user_lower for word in ['venv', 'virtual environment', 'virtualenv']):
            venv_match = re.search(r'(?:venv|virtual environment)\s+(?:called|named)\s+["\']?([^"\']+)["\']?', user_lower)
            if venv_match:
                venv_name = venv_match.group(1).strip()
                return {"operation": "create_venv", "venv_name": venv_name}
        
        # Project creation patterns
        elif any(word in user_lower for word in ['react project', 'python project', 'flask project', 'create project']):
            project_type = None
            if 'react' in user_lower:
                project_type = 'react'
            elif 'flask' in user_lower:
                project_type = 'flask'
            elif 'python' in user_lower:
                project_type = 'python'
            
            if project_type:
                project_match = re.search(r'project\s+(?:called|named)\s+["\']?([^"\']+)["\']?', user_lower)
                if project_match:
                    project_name = project_match.group(1).strip()
                    return {"operation": "create_project", "project_type": project_type, "project_name": project_name}
        
        # Default to chat ONLY if no operation detected
        return {"operation": "chat"}
    
    def resolve_path(self, path_str: str) -> Path:
        """Resolve a path string to an absolute Path object"""
        if not path_str or path_str.strip() == "":
            return self.base_dir
        
        path_str = path_str.strip()
        
        # Handle special user folders
        user_folders = ['Desktop', 'Documents', 'Downloads', 'Pictures', 'Music', 'Videos']
        if path_str in user_folders:
            return Path.home() / path_str
        
        # Handle Windows absolute paths
        if self.system == 'windows' and re.match(r'^[A-Za-z]:', path_str):
            return Path(path_str)
        
        # Handle Unix absolute paths
        if path_str.startswith('/'):
            return Path(path_str)
        
        # Handle relative paths
        return self.base_dir / path_str
    
    def validate_name(self, name: str, name_type: str = "name") -> Tuple[bool, str]:
        """Validate file/folder name"""
        if not name:
            return False, f"{name_type} cannot be empty"
        
        # Check for invalid characters
        if re.search(r'[<>:"/\\|?*]', name):
            return False, f"{name_type} contains invalid characters"
        
        # Check length
        if len(name) > 255:
            return False, f"{name_type} too long"
        
        return True, "Valid name"
    
    def create_file(self, file_name: str, file_content: str = "") -> Tuple[bool, str]:
        """Create a file with content"""
        is_valid, message = self.validate_name(file_name, "File name")
        if not is_valid:
            return False, message
        
        try:
            file_path = self.base_dir / file_name
            
            if file_path.exists():
                return False, f"File '{file_name}' already exists"
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            return True, f"✅ File '{file_name}' created successfully"
            
        except Exception as e:
            return False, f"Error creating file: {e}"
    
    def create_folder(self, folder_name: str, folder_path: str = "") -> Tuple[bool, str]:
        """Create a folder"""
        is_valid, message = self.validate_name(folder_name, "Folder name")
        if not is_valid:
            return False, message
        
        try:
            target_path = self.resolve_path(folder_path)
            final_path = target_path / folder_name
            
            if final_path.exists():
                return False, f"Folder '{folder_name}' already exists"
            
            final_path.mkdir(parents=True, exist_ok=True)
            
            return True, f"✅ Folder '{folder_name}' created successfully at: {final_path}"
            
        except Exception as e:
            return False, f"Error creating folder: {e}"
    
    def create_venv(self, venv_name: str) -> Tuple[bool, str]:
        """Create Python virtual environment"""
        is_valid, message = self.validate_name(venv_name, "Virtual environment name")
        if not is_valid:
            return False, message
        
        try:
            venv_path = self.base_dir / venv_name
            
            if venv_path.exists():
                return False, f"Virtual environment '{venv_name}' already exists"
            
            subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], 
                         check=True, capture_output=True, text=True)
            
            activate_cmd = f"{venv_name}\\Scripts\\activate" if self.system == 'windows' else f"source {venv_name}/bin/activate"
            return True, f"✅ Virtual environment '{venv_name}' created. Activate with: {activate_cmd}"
            
        except Exception as e:
            return False, f"Error creating virtual environment: {e}"
    
    def create_project(self, project_type: str, project_name: str) -> Tuple[bool, str]:
        """Create project templates"""
        is_valid, message = self.validate_name(project_name, "Project name")
        if not is_valid:
            return False, message
        
        try:
            project_path = self.base_dir / project_name
            
            if project_path.exists():
                return False, f"Project '{project_name}' already exists"
            
            if project_type == 'react':
                return self.create_react_project(project_path, project_name)
            elif project_type == 'flask':
                return self.create_flask_project(project_path, project_name)
            elif project_type == 'python':
                return self.create_python_project(project_path, project_name)
            else:
                return False, f"Unknown project type: {project_type}"
                
        except Exception as e:
            return False, f"Error creating project: {e}"
    
    def create_react_project(self, project_path: Path, project_name: str) -> Tuple[bool, str]:
        """Create React project template"""
        project_path.mkdir(parents=True, exist_ok=True)
        
        # package.json
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
                "build": "react-scripts build"
            }
        }
        
        with open(project_path / 'package.json', 'w') as f:
            json.dump(package_json, f, indent=2)
        
        # Create basic structure
        (project_path / 'src').mkdir()
        (project_path / 'public').mkdir()
        
        # App.js
        app_js = '''import React from 'react';

function App() {
  return (
    <div className="App">
      <h1>Hello React!</h1>
    </div>
  );
}

export default App;
'''
        
        with open(project_path / 'src' / 'App.js', 'w') as f:
            f.write(app_js)
        
        # index.js
        index_js = '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
'''
        
        with open(project_path / 'src' / 'index.js', 'w') as f:
            f.write(index_js)
        
        # public/index.html
        index_html = f'''<!DOCTYPE html>
<html>
<head>
    <title>{project_name}</title>
</head>
<body>
    <div id="root"></div>
</body>
</html>
'''
        
        with open(project_path / 'public' / 'index.html', 'w') as f:
            f.write(index_html)
        
        return True, f"✅ React project '{project_name}' created. Run 'npm install' then 'npm start'"
    
    def create_flask_project(self, project_path: Path, project_name: str) -> Tuple[bool, str]:
        """Create Flask project template"""
        project_path.mkdir(parents=True, exist_ok=True)
        
        # app.py
        app_content = '''from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Hello, Flask!"

if __name__ == '__main__':
    app.run(debug=True)
'''
        
        with open(project_path / 'app.py', 'w') as f:
            f.write(app_content)
        
        # requirements.txt
        with open(project_path / 'requirements.txt', 'w') as f:
            f.write('Flask==2.3.3\n')
        
        # templates folder
        (project_path / 'templates').mkdir()
        
        return True, f"✅ Flask project '{project_name}' created. Run 'pip install -r requirements.txt' then 'python app.py'"
    
    def create_python_project(self, project_path: Path, project_name: str) -> Tuple[bool, str]:
        """Create Python project template"""
        project_path.mkdir(parents=True, exist_ok=True)
        
        # main.py
        main_content = '''def main():
    print("Hello, Python Project!")

if __name__ == "__main__":
    main()
'''
        
        with open(project_path / 'main.py', 'w') as f:
            f.write(main_content)
        
        # requirements.txt
        with open(project_path / 'requirements.txt', 'w') as f:
            f.write('# Add your dependencies here\n')
        
        return True, f"✅ Python project '{project_name}' created. Run 'python main.py'"
    
    def get_chat_response(self, user_input: str) -> str:
        """Get normal chat response"""
        prompt = f"""You are a helpful AI assistant. Respond naturally and conversationally to the user.

User: {user_input}
Assistant:"""
        
        return self.call_ollama(prompt)
    
    def process_message(self, user_input: str) -> dict:
        """Process user message"""
        try:
            operation_data = self.detect_operation(user_input)
            operation = operation_data.get("operation", "chat")
            
            # Debug logging
            print(f"DEBUG: User input: '{user_input}'")
            print(f"DEBUG: Detected operation: {operation}")
            print(f"DEBUG: Operation data: {operation_data}")
            
            if operation == "create_file":
                file_name = operation_data.get("file_name", "")
                file_content = operation_data.get("file_content", "")
                success, message = self.create_file(file_name, file_content)
                return {"type": "file_creation", "success": success, "message": message}
            
            elif operation == "create_folder":
                folder_name = operation_data.get("folder_name", "")
                folder_path = operation_data.get("folder_path", "")
                success, message = self.create_folder(folder_name, folder_path)
                return {"type": "folder_creation", "success": success, "message": message}
            
            elif operation == "create_venv":
                venv_name = operation_data.get("venv_name", "")
                success, message = self.create_venv(venv_name)
                return {"type": "venv_creation", "success": success, "message": message}
            
            elif operation == "create_project":
                project_type = operation_data.get("project_type", "")
                project_name = operation_data.get("project_name", "")
                success, message = self.create_project(project_type, project_name)
                return {"type": "project_creation", "success": success, "message": message}
            
            else:  # chat
                response = self.get_chat_response(user_input)
                return {"type": "chat", "message": response}
                
        except Exception as e:
            print(f"DEBUG: Exception in process_message: {e}")
            return {"type": "error", "message": f"Error: {e}"}

# Initialize chatbot
chatbot = SimpleChatbot()

@app.route('/')
def index():
    return render_template('simple.html')

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
    print("Starting Simple AI Chatbot...")
    print("Open your browser and go to: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
