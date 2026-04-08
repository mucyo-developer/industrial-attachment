<<<<<<< HEAD
# industrial-attachment
industrial-attachment-work
=======
# AI Folder Chatbot

An intelligent chatbot powered by Qwen (via Ollama) that can create folders through natural language conversation.

## Features

- 🤖 Natural language conversation using Qwen 1.5B model
- 📁 Create folders by simply asking (e.g., "Create a folder called my-project")
- 🔒 Safe folder creation with validation and security checks
- 💬 Regular chat capabilities when not creating folders
- ⚡ Lightweight and fast

## Setup

1. **Install Ollama** (if not already installed)
   ```bash
   # Download from https://ollama.com
   ```

2. **Pull Qwen model** (if not already done)
   ```bash
   ollama pull qwen2.5:1.5b
   ```

3. **Start Ollama**
   ```bash
   ollama serve
   ```

4. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the chatbot:
```bash
python chatbot.py
```

### Example Interactions

```
You: Create a folder called my-documents
Bot: 🔍 Detected folder creation request: 'my-documents'
Bot: ✅ Folder 'my-documents' created successfully at: /path/to/my-documents

You: Make a new folder for project files
Bot: 🔍 Detected folder creation request: 'project files'
Bot: ✅ Folder 'project files' created successfully at: /path/to/project files

You: What's the weather like?
Bot: I don't have access to weather information, but I can help you with folder creation and other tasks!
```

## Safety Features

- ✅ Validates folder names for invalid characters
- ✅ Prevents creation of system folders
- ✅ Checks for existing folders/files
- ✅ Handles permission errors gracefully
- ✅ Limits folder name length

## Supported Commands

The chatbot understands various ways to ask for folder creation:
- "Create a folder called [name]"
- "Make a new folder named [name]"
- "Create directory [name]"
- "New folder [name]"
- And many more natural variations!

## Requirements

- Python 3.7+
- Ollama running on localhost:11434
- Qwen 1.5B model installed
- requests library
>>>>>>> 120b94a (initialized commit)
