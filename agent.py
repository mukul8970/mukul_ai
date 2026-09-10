import json
import os
import re
import subprocess
import webbrowser
from pathlib import Path

import requests

BASE = Path(__file__).parent
PROJECTS = BASE / "projects"
PROJECTS.mkdir(exist_ok=True)

OLLAMA_URL = os.getenv("MUKUL_OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.getenv("MUKUL_OLLAMA_MODEL")

SYSTEM = r"""
You are MUKUL AI PRO, a local autonomous coding agent.
The user gives a natural-language request to build or modify a website/app.

Your job is to create a real project, not merely explain code.

Return ONLY valid JSON:
{
  "project_name": "short_name",
  "summary": "short summary",
  "operations": [
    {"type":"write","path":"relative/file/path","content":"FULL FILE CONTENT"},
    {"type":"delete","path":"relative/file/path"},
    {"type":"command","command":"SAFE_COMMAND"}
  ],
  "start_command": "optional command",
  "preview_url": "optional URL"
}

Rules:
- For a NEW project, include all important files needed to run it.
- For an EXISTING project, inspect the provided current files and modify only what is needed.
- Prefer simple HTML/CSS/JavaScript for small websites.
- Use React/Vite/Next.js, Python/Flask/FastAPI, Node/Express, etc. when the request needs them.
- Make responsive, polished UI.
- Include accessible labels, sensible validation and error handling.
- Never put secrets, passwords or API keys in source code.
- Commands must be ordinary development commands only (npm install, npm run ..., pip install ..., python ..., etc.).
- Never use commands that delete arbitrary files, format disks, change system settings, download executables, or bypass security.
- Never claim a payment, cloud deployment, domain, database account, or external service is configured unless it really is.
- If an external credential is required, create a clear .env.example instead.
- Use forward-slash paths.
"""

ALLOWED_COMMAND_PREFIXES = (
    "npm ", "npx ", "node ", "python ", "py ", "pip ", "pip3 ",
    "pnpm ", "yarn ", "bun ", "vite", "next ", "flask ",
)

MAX_FILE = 500_000
MAX_CONTEXT = 1_500_000

def safe_project_name(name):
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", name.strip().lower())
    return name[:60] or "mukul_project"

def safe_rel_path(value):
    p = Path(value)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"Unsafe path: {value}")
    return p

def read_project(project_dir):
    chunks = []
    total = 0
    ignored = {".git", "node_modules", "venv", "__pycache__", ".next", "dist", "build"}
    for p in project_dir.rglob("*"):
        if not p.is_file() or any(part in ignored for part in p.parts):
            continue
        if p.suffix.lower() not in {
            ".html",".css",".js",".jsx",".ts",".tsx",".json",".py",".md",".txt",
            ".sql",".env.example",".vue",".svelte",".xml",".yml",".yaml"
        }:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        piece = f"\n--- FILE: {p.relative_to(project_dir).as_posix()} ---\n{text}\n"
        if total + len(piece) > MAX_CONTEXT:
            break
        chunks.append(piece)
        total += len(piece)
    return "".join(chunks)

def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("AI ne valid JSON nahi diya.")
    return json.loads(text[start:end+1])


MODEL_PRIORITY = ["qwen3:1.7b", "llama3.2:3b", "mistral:7b"]
SYSTEM_PROMPT = r"""
You are MUKUL AI, a friendly, smart local AI assistant.

STRICT RULES:
- Never show internal reasoning or chain-of-thought.
- Never output <think>...</think> blocks.
- Give direct final answers only.
- Use Hindi, Hinglish, or English depending on user.
- Keep answers short, clean, and useful.
- Never pretend a real backend/database/server exists unless it has actually been set up.

ROLE:
- General assistant, coding help, explanations, writing support.
- Website builder and full-stack planner.
- UI/UX thinking like a professional web developer.
- Database schema design, auth flow, API architecture, admin panel logic.
"""

chat_history = []

BASIC_ANSWERS = {
    "hi": "Namaste! Main Mukul AI hoon. Aapki madad ke liye ready hoon.",
    "hello": "Hello! Main Mukul AI hoon. Aapki madad ke liye ready hoon.",
    "hey": "Hey! Main Mukul AI hoon.",
    "namaste": "Namaste! Main Mukul AI hoon.",
    "how are you": "Main theek hoon. Aap bataiye, aapko kis tarah ki madad chahiye?",
    "python": "Python ek easy aur powerful programming language hai.",
    "html": "HTML webpage ka structure banata hai.",
    "css": "CSS webpage ko design aur style deta hai.",
    "javascript": "JavaScript website ko interactive banata hai.",
    "website": "Website banane ke liye HTML, CSS, JavaScript use hote hain.",
    "backend": "Backend server-side logic aur database ka kaam karta hai.",
    "database": "Database data store karne ke liye use hota hai.",
    "api": "API do systems ko communicate karne ka way hai.",
    "ai": "AI machines ko smart decisions lene ki ability deta hai.",
    "what can you do": "Main coding, website creation, backend logic aur general help kar sakta hoon.",
}


def contains_any(text, words):
    return any(word in text for word in words)


def clean_answer(text):
    if not text:
        return ""
    text = re.sub(r"(?is)<think>.*?</think>", "", text)
    text = re.sub(r"(?is)<think>.*", "", text)
    text = re.sub(r"(?is)<thinking>.*?</thinking>", "", text)
    text = re.sub(r"(?is)<thinking>.*", "", text)
    text = re.sub(r"(?is)^(?:okay|ok|sure|acha|haan|theek hai|chalo)\s*[:\-]?\s*", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_local_reply(message):
    text = message.strip().lower()
    if not text:
        return "Aap kuch likho."

    for keyword, answer in BASIC_ANSWERS.items():
        if keyword in text:
            return answer

    if contains_any(text, ["hi", "hello", "hey", "namaste"]):
        return BASIC_ANSWERS["hi"]

    if contains_any(text, ["kaise ho", "kaise hain", "how are you"]):
        return BASIC_ANSWERS["how are you"]

    if contains_any(text, ["what can you do", "tum kya kar sakte ho", "aap kya kar sakte ho"]):
        return BASIC_ANSWERS["what can you do"]

    return None


def model_exists(model_name):
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=20,
        )
        if result.returncode != 0:
            return False
        return model_name.lower() in result.stdout.lower()
    except Exception:
        return False


def get_model():
    for model in MODEL_PRIORITY:
        if model_exists(model):
            return model
    return MODEL_PRIORITY[0]


MODEL = MODEL or get_model()


def run_ollama(prompt, model):
    try:
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=120,
        )
        if result.returncode != 0:
            error = (result.stderr or result.stdout or "").strip()
            if not error:
                error = "Ollama response failed."
            return {"ok": False, "error": error}

        output = clean_answer(result.stdout)
        if not output:
            return {"ok": False, "error": "Empty model response."}
        return {"ok": True, "output": output}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Response timed out."}
    except FileNotFoundError:
        return {"ok": False, "error": "Ollama is not installed or not running."}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def ask_mukul(user_message):
    quick = get_local_reply(user_message)
    if quick:
        return quick

    chat_history.append("User: " + user_message)
    recent_history = "\n".join(chat_history[-4:])

    prompt = SYSTEM_PROMPT + "\n\nCONVERSATION:\n" + recent_history + "\n\nMukul AI:"
    model = get_model()
    reply = run_ollama(prompt, model)

    if not reply["ok"]:
        for other_model in [m for m in MODEL_PRIORITY if m != model]:
            if model_exists(other_model):
                other_reply = run_ollama(prompt, other_model)
                if other_reply["ok"]:
                    answer = other_reply["output"]
                    chat_history.append("Mukul AI: " + answer)
                    return answer
        return "Error: " + reply["error"]

    answer = reply["output"]
    chat_history.append("Mukul AI: " + answer)
    return answer


class MukulAgent:
    def ask_model(self, prompt):
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {"temperature": 0.15}
        }
        r = requests.post(
            OLLAMA_URL.rstrip("/") + "/api/chat",
            json=payload,
            timeout=600
        )
        r.raise_for_status()
        data = r.json()
        return data["message"]["content"]

    def handle(self, task):
        existing = ""
        # Let the model decide whether this is a new or existing project.
        names = [p.name for p in PROJECTS.iterdir() if p.is_dir()]
        if names:
            existing = "\nEXISTING PROJECTS:\n" + "\n".join(names)
        prompt = (
            f"USER REQUEST:\n{task}\n"
            f"{existing}\n\n"
            "If the user wants to modify an existing project, choose the matching project_name "
            "and use its current files below. Otherwise create a new project.\n"
        )

        # Include current project context when a likely project name appears in the request.
        for name in names:
            if name.lower() in task.lower():
                prompt += f"\nCURRENT FILES FOR PROJECT {name}:\n{read_project(PROJECTS / name)}\n"
                break

        print("\nAI planning and coding...\n")
        data = extract_json(self.ask_model(prompt))
        project = safe_project_name(data.get("project_name", "mukul_project"))
        project_dir = PROJECTS / project
        project_dir.mkdir(parents=True, exist_ok=True)

        for op in data.get("operations", []):
            typ = op.get("type")
            if typ == "write":
                rel = safe_rel_path(op.get("path", ""))
                content = op.get("content", "")
                if len(content) > MAX_FILE:
                    raise ValueError(f"File too large: {rel}")
                target = project_dir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                print(f"[FILE] {rel}")

            elif typ == "delete":
                rel = safe_rel_path(op.get("path", ""))
                target = project_dir / rel
                if target.exists() and target.is_file():
                    target.unlink()
                    print(f"[DELETE] {rel}")

            elif typ == "command":
                command = op.get("command", "").strip()
                self.run_safe(command, project_dir)

        print(f"\n✅ Project ready: {project_dir.resolve()}")
        print(f"Summary: {data.get('summary', 'Done')}")

        start = data.get("start_command")
        if start:
            print(f"Suggested start command: {start}")

        url = data.get("preview_url")
        if url:
            print(f"Preview: {url}")

    def run_safe(self, command, cwd):
        low = command.lower().strip()
        if not any(low.startswith(x) for x in ALLOWED_COMMAND_PREFIXES):
            print(f"[SKIP] Unsafe/unapproved command: {command}")
            return

        print(f"[RUN] {command}")
        result = subprocess.run(
            command,
            cwd=cwd,
            shell=True,
            text=True,
            capture_output=True,
            timeout=600
        )
        if result.stdout:
            print(result.stdout[-5000:])
        if result.returncode != 0:
            print(result.stderr[-5000:])
            print("[WARN] Command failed. Ask Mukul AI to fix the error.")

    def list_projects(self):
        items = [p.name for p in PROJECTS.iterdir() if p.is_dir()]
        print("\nProjects:")
        if not items:
            print("  No projects yet.")
        else:
            for x in items:
                print("  -", x)
        print()

    def open_project(self, name):
        project = PROJECTS / safe_project_name(name)
        if not project.exists():
            print("Project nahi mila.")
            return
        os.startfile(project.resolve())

if __name__ == "__main__":
    MukulAgent().handle(input("Task: "))
