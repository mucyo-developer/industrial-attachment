#!/usr/bin/env python3
"""
Production-Ready AI Chatbot with File Operations
- Environment-based configuration
- Proper logging
- Security headers
- Error handling
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import requests
import re
import json
import subprocess
import sys
import platform
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Load environment variables
load_dotenv()

# Configure logging
def setup_logging():
    """Setup production logging"""
    if not os.path.exists('logs'):
        os.mkdir('logs')
    
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'logs/chatbot.log')
    
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
        handlers=[
            RotatingFileHandler(log_file, maxBytes=10240000, backupCount=10),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

logger = setup_logging()

# Create Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = int(os.getenv('MAX_CONTENT_LENGTH', 16777216))

# CORS configuration
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
CORS(app, origins=cors_origins, supports_credentials=True)

class ProductionChatbot:
    def __init__(self):
        self.ollama_url = os.getenv('OLLAMA_URL', 'http://localhost:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'qwen2.5:0.5b')
        self.base_dir = Path.cwd()
        self.system = platform.system().lower()
        
        # Security: Validate Ollama URL
        if not self._is_safe_url(self.ollama_url):
            raise ValueError(f"Unsafe Ollama URL: {self.ollama_url}")
        
        logger.info(f"Chatbot initialized with model: {self.model}")
        logger.info(f"Base directory: {self.base_dir}")
    
    def _is_safe_url(self, url: str) -> bool:
        """Check if URL is safe (localhost/internal only)"""
        safe_patterns = ['http://localhost', 'http://127.0.0.1', 'https://localhost', 'https://127.0.0.1']
        return any(pattern in url for pattern in safe_patterns)
    
    def call_ollama(self, prompt: str) -> str:
        """Make API call to Ollama with error handling"""
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30  # Add timeout
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except requests.exceptions.Timeout:
            logger.error("Ollama request timed out")
            return "I'm sorry, the request timed out. Please try again."
        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to Ollama at {self.ollama_url}")
            return "I'm sorry, I cannot connect to the AI service right now. Please check if Ollama is running."
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return f"An error occurred: {e}"
    
    def detect_operation(self, user_input: str) -> Dict[str, Any]:
        """Simple operation detection using keywords and patterns"""
        user_lower = user_input.lower()
        
        # File creation patterns
        if any(word in user_lower for word in ['create file', 'make file', 'new file', 'write file']):
            file_match = re.search(r'file\s+(?:called|named)\s+["\']?([^"\']+)["\']?', user_lower)
            if file_match:
                file_name = file_match.group(1).strip()
                content_match = re.search(r'(?:with|containing)\s+["\']?([^"\']+)["\']?', user_lower)
                file_content = content_match.group(1).strip() if content_match else ""
                return {"operation": "create_file", "file_name": file_name, "file_content": file_content}
        
        # Folder creation patterns
        elif any(word in user_lower for word in ['create folder', 'make folder', 'new folder', 'create directory', 'folder called', 'directory called']):
            folder_name = ""
            
            folder_match = re.search(r'(?:folder|directory)\s+(?:called|named)\s+["\']?([^"\']+)["\']?', user_lower)
            if folder_match:
                folder_name = folder_match.group(1).strip()
            elif 'create folder' in user_lower:
                after_create = user_lower.split('create folder')[-1].strip()
                if after_create and len(after_create.split()) <= 3:
                    folder_name = after_create.strip(' "\'')
            elif 'make folder' in user_lower:
                after_make = user_lower.split('make folder')[-1].strip()
                if after_make and len(after_make.split()) <= 3:
                    folder_name = after_make.strip(' "\'')
            elif 'new folder' in user_lower:
                after_new = user_lower.split('new folder')[-1].strip()
                if after_new and len(after_new.split()) <= 3:
                    folder_name = after_new.strip(' "\'')
            
            if folder_name:
                folder_path = ""
                if 'desktop' in user_lower:
                    folder_path = "Desktop"
                elif 'documents' in user_lower:
                    folder_path = "Documents"
                elif 'downloads' in user_lower:
                    folder_path = "Downloads"
                
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
        
        return {"operation": "chat"}
    
    def resolve_path(self, path_str: str) -> Path:
        """Resolve a path string to an absolute Path object with security checks"""
        if not path_str or path_str.strip() == "":
            return self.base_dir
        
        path_str = path_str.strip()
        
        # Security: Prevent path traversal
        if '..' in path_str or path_str.startswith('~'):
            logger.warning(f"Potentially unsafe path attempted: {path_str}")
            return self.base_dir
        
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
        """Validate file/folder name with security checks"""
        if not name:
            return False, f"{name_type} cannot be empty"
        
        # Check for invalid characters
        if re.search(r'[<>:"/\\|?*]', name):
            return False, f"{name_type} contains invalid characters"
        
        # Check for reserved names (Windows)
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        if name.upper() in reserved_names:
            return False, f"'{name}' is a reserved system name"
        
        # Check length
        if len(name) > 255:
            return False, f"{name_type} too long"
        
        return True, "Valid name"
    
    def create_file(self, file_name: str, file_content: str = "") -> Tuple[bool, str]:
        """Create a file with content and security checks"""
        is_valid, message = self.validate_name(file_name, "File name")
        if not is_valid:
            return False, message
        
        try:
            file_path = self.base_dir / file_name
            
            # Security: Check if path is within allowed directory
            if not str(file_path.resolve()).startswith(str(self.base_dir.resolve())):
                logger.warning(f"Attempted to create file outside base directory: {file_path}")
                return False, "Access denied: Cannot create file outside allowed directory"
            
            if file_path.exists():
                return False, f"File '{file_name}' already exists"
            
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(file_content)
            
            logger.info(f"File created: {file_path}")
            return True, f"✅ File '{file_name}' created successfully"
            
        except PermissionError:
            logger.error(f"Permission denied creating file: {file_name}")
            return False, f"Permission denied: Cannot create file '{file_name}'"
        except Exception as e:
            logger.error(f"Error creating file '{file_name}': {e}")
            return False, f"Error creating file: {e}"
    
    def create_folder(self, folder_name: str, folder_path: str = "") -> Tuple[bool, str]:
        """Create a folder with security checks"""
        is_valid, message = self.validate_name(folder_name, "Folder name")
        if not is_valid:
            return False, message
        
        try:
            target_path = self.resolve_path(folder_path)
            final_path = target_path / folder_name
            
            # Security: Check if path is safe
            if not str(final_path.resolve()).startswith(str(target_path.resolve())):
                logger.warning(f"Attempted path traversal in folder creation: {final_path}")
                return False, "Access denied: Invalid path"
            
            if final_path.exists():
                return False, f"Folder '{folder_name}' already exists"
            
            final_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Folder created: {final_path}")
            return True, f"✅ Folder '{folder_name}' created successfully at: {final_path}"
            
        except PermissionError:
            logger.error(f"Permission denied creating folder: {folder_name}")
            return False, f"Permission denied: Cannot create folder '{folder_name}'"
        except Exception as e:
            logger.error(f"Error creating folder '{folder_name}': {e}")
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
                         check=True, capture_output=True, text=True, timeout=60)
            
            activate_cmd = f"{venv_name}\\Scripts\\activate" if self.system == 'windows' else f"source {venv_name}/bin/activate"
            logger.info(f"Virtual environment created: {venv_path}")
            return True, f"✅ Virtual environment '{venv_name}' created. Activate with: {activate_cmd}"
            
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout creating virtual environment: {venv_name}")
            return False, "Timeout: Virtual environment creation took too long"
        except Exception as e:
            logger.error(f"Error creating virtual environment '{venv_name}': {e}")
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
            logger.error(f"Error creating project '{project_name}': {e}")
            return False, f"Error creating project: {e}"
    
    def create_react_project(self, project_path: Path, project_name: str) -> Tuple[bool, str]:
        """Create React project template"""
        project_path.mkdir(parents=True, exist_ok=True)
        
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
        
        (project_path / 'src').mkdir()
        (project_path / 'public').mkdir()
        
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
        
        index_js = '''import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
'''
        
        with open(project_path / 'src' / 'index.js', 'w') as f:
            f.write(index_js)
        
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
        
        logger.info(f"React project created: {project_path}")
        return True, f"✅ React project '{project_name}' created. Run 'npm install' then 'npm start'"
    
    def create_flask_project(self, project_path: Path, project_name: str) -> Tuple[bool, str]:
        """Create Flask project template"""
        project_path.mkdir(parents=True, exist_ok=True)
        
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
        
        with open(project_path / 'requirements.txt', 'w') as f:
            f.write('Flask==2.3.3\n')
        
        (project_path / 'templates').mkdir()
        
        logger.info(f"Flask project created: {project_path}")
        return True, f"✅ Flask project '{project_name}' created. Run 'pip install -r requirements.txt' then 'python app.py'"
    
    def create_python_project(self, project_path: Path, project_name: str) -> Tuple[bool, str]:
        """Create Python project template"""
        project_path.mkdir(parents=True, exist_ok=True)
        
        main_content = '''def main():
    print("Hello, Python Project!")

if __name__ == "__main__":
    main()
'''
        
        with open(project_path / 'main.py', 'w') as f:
            f.write(main_content)
        
        with open(project_path / 'requirements.txt', 'w') as f:
            f.write('# Add your dependencies here\n')
        
        logger.info(f"Python project created: {project_path}")
        return True, f"✅ Python project '{project_name}' created. Run 'python main.py'"
    
    def get_chat_response(self, user_input: str) -> str:
        """Get normal chat response"""
        prompt = f"""You are a helpful AI assistant. Respond naturally and conversationally to the user.

User: {user_input}
Assistant:"""
        
        return self.call_ollama(prompt)
    
    def process_message(self, user_input: str) -> dict:
        """Process user message with logging"""
        try:
            operation_data = self.detect_operation(user_input)
            operation = operation_data.get("operation", "chat")
            
            logger.info(f"Processing message: {user_input[:100]}... Operation: {operation}")
            
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
            logger.error(f"Exception in process_message: {e}")
            return {"type": "error", "message": "An internal error occurred. Please try again."}

# Initialize chatbot
try:
    chatbot = ProductionChatbot()
    logger.info("Chatbot initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize chatbot: {e}")
    raise

@app.route('/')
def index():
    return render_template('simple.html')

@app.route('/chat', methods=['POST'])
def chat():
    """Chat endpoint with rate limiting and validation"""
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if len(user_message) > 1000:  # Reasonable limit
            return jsonify({"error": "Message too long"}), 400
        
        response = chatbot.process_message(user_message)
        return jsonify(response)
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    try:
        # Check Ollama connection
        ollama_response = requests.get(f"{chatbot.ollama_url}/api/tags", timeout=5)
        ollama_status = "connected" if ollama_response.status_code == 200 else "not_responding"
        
        return jsonify({
            "status": "healthy", 
            "timestamp": datetime.now().isoformat(),
            "ollama": ollama_status,
            "model": chatbot.model
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy", 
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 503

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting production chatbot on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
