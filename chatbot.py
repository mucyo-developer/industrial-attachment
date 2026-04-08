#!/usr/bin/env python3
"""
AI Chatbot with Folder Creation Capabilities
Uses Ollama API with Qwen model for natural language processing
"""

import requests
import os
import re
import json
from pathlib import Path
from typing import Optional, Tuple

class FolderChatbot:
    def __init__(self, ollama_url: str = "http://localhost:11434", model: str = "qwen2.5:1.5b"):
        self.ollama_url = ollama_url
        self.model = model
        self.base_dir = Path.cwd()  # Current working directory as base
        
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
    
    def detect_folder_intent(self, user_input: str) -> Optional[str]:
        """Use Qwen to detect if user wants to create a folder and extract the name"""
        prompt = f"""
Analyze this user request and determine if they want to create a folder.
If yes, extract only the folder name. If no, respond with "NO".

User request: "{user_input}"

Rules:
- Respond with just the folder name if creating a folder
- Respond with "NO" if not about folder creation
- Handle variations like "create", "make", "new folder", "directory"
- Clean up invalid characters from names
"""
        
        response = self.call_ollama(prompt)
        
        if response.upper() == "NO":
            return None
            
        # Clean the folder name
        folder_name = re.sub(r'[<>:"/\\|?*]', '', response).strip()
        folder_name = re.sub(r'\s+', ' ', folder_name)
        
        return folder_name if folder_name else None
    
    def validate_folder_name(self, folder_name: str) -> Tuple[bool, str]:
        """Validate folder name for safety"""
        if not folder_name:
            return False, "Folder name cannot be empty"
        
        # Check for reserved names
        reserved_names = {
            'CON', 'PRN', 'AUX', 'NUL',
            'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
            'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        }
        
        if folder_name.upper() in reserved_names:
            return False, f"'{folder_name}' is a reserved system name"
        
        # Check for invalid characters
        if re.search(r'[<>:"/\\|?*]', folder_name):
            return False, "Folder name contains invalid characters"
        
        # Check length
        if len(folder_name) > 255:
            return False, "Folder name too long (max 255 characters)"
        
        return True, "Valid folder name"
    
    def create_folder(self, folder_name: str) -> Tuple[bool, str]:
        """Safely create a folder"""
        is_valid, message = self.validate_folder_name(folder_name)
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
    
    def get_chat_response(self, user_input: str) -> str:
        """Get regular chat response from Qwen"""
        prompt = f"""
You are a helpful AI assistant. Respond naturally to this user request.
Keep responses concise and friendly.

User: {user_input}
Assistant:"""
        
        return self.call_ollama(prompt)
    
    def run(self):
        """Main chat loop"""
        print("AI Folder Chatbot Started!")
        print("You can ask me to create folders or just chat normally")
        print("All folders will be created in:", self.base_dir)
        print("Type 'quit' or 'exit' to stop\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Check for folder creation intent
                folder_name = self.detect_folder_intent(user_input)
                
                if folder_name:
                    print(f"Detected folder creation request: '{folder_name}'")
                    success, message = self.create_folder(folder_name)
                    print(f"Bot: {message}")
                else:
                    # Regular chat response
                    response = self.get_chat_response(user_input)
                    print(f"Bot: {response}")
                    
            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Bot: Oops, something went wrong: {e}")

if __name__ == "__main__":
    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code != 200:
            print("Error: Ollama is not running. Please start Ollama first.")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("Error: Cannot connect to Ollama. Make sure Ollama is running on localhost:11434")
        exit(1)
    
    # Start the chatbot
    chatbot = FolderChatbot()
    chatbot.run()
