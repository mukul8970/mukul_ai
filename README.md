# Mukul AI Pro

Local text-based AI coding agent for generating and modifying many kinds of websites/apps.

## What it can do

- Create separate projects from text prompts
- Generate HTML/CSS/JS projects
- Generate React/Vite/Node/Python-style projects when the model chooses them
- Modify an existing project
- Create/update/delete project files
- Run normal development commands such as npm/pip/python
- Keep projects in `projects/`
- No cloud API key is required when using local Ollama

## Requirements

- Windows 10/11
- Python 3.11
- VS Code
- Enough RAM/storage for the selected local model

## Recommended local brain

This package defaults to `qwen3-coder:7b`. Ollama lists it as a coding/agentic model and its download is about 1.2 GB. If your laptop cannot handle it, use a smaller model such as:

```powershell
ollama pull qwen3:8b
$env:MUKUL_OLLAMA_MODEL="qwen3:7b"
```

## Setup

1. Install Ollama for Windows:
   https://ollama.com/download/windows

2. Open PowerShell in this folder and run:

```powershell
ollama pull qwen3-coder:30b
```

3. Open this folder in VS Code.

4. Open Terminal and run:

```powershell
py -3.11 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py -3.11 main.py
```

Or double-click `run.bat`.

## Example prompts

```text
Ek professional coaching institute website banao with courses,
admission form, student login, teacher dashboard and admin panel.
```

```text
Ek modern e-commerce website banao with product search,
categories, cart, checkout page and admin dashboard.
```

```text
Ek restaurant website banao with menu, table booking form,
gallery and responsive mobile design.
```

## Important limitation

No AI can guarantee literally every possible website or a production-ready
payment/authentication/database deployment from one sentence. External services
and credentials still need configuration. The agent also only runs a restricted
set of development commands for safety.
