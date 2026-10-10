"""
ARIA - AI Module
Handles: command planning, chat response, intent classification
Uses: Ollama (local LLM - llama3)
"""

import subprocess
import sys

# ── Auto-install dependencies ─────────────────────────────────────────────────
def _pip(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    import requests
except ImportError:
    _pip("requests==2.31.0")
    import requests

import json

OLLAMA_URL = "YOUR_API_KEY/api/generate"
MODEL = "llama3"


# ── JSON extractor ────────────────────────────────────────────────────────────
def extract_json(text):
    """Safely extract first JSON object from LLM output."""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    return text[start:end]


# ── ACTION PLANNER ────────────────────────────────────────────────────────────
def get_plan(command):
    """
    Convert natural language command → structured JSON action plan.
    This is the BRAIN of ARIA.
    """
    prompt = f"""
You are a strict JSON generator for a desktop AI assistant.

Convert the user command into a JSON action plan.
ONLY return JSON. No explanation. No extra text.

Available Actions:
create_folder, create_file, move, delete, open, list,
search, rename, read_file, disk_info, system_info,
automate, browser_open, browser_search

Location keywords:
- desktop, downloads, documents
- c drive, d drive, e drive

App keywords:
- valorant, brave, edge, spotify, whatsapp, chrome, vscode, notepad, calculator

Automation examples (multi-step):
create project folder then open vscode
→ {{"action":"automate","args":["create_folder:desktop/project","open:vscode"]}}

Rules:
- If no location → use desktop
- Always return valid JSON
- args must always be a list
- For automation: join steps with comma, each step is "action:arg"

Examples:

create folder test in desktop
{{"action":"create_folder","args":["desktop/test"]}}

create file notes.txt in d drive
{{"action":"create_file","args":["d drive/notes.txt"]}}

move notes.txt to e drive
{{"action":"move","args":["desktop/notes.txt","e drive/"]}}

delete notes.txt from desktop
{{"action":"delete","args":["desktop/notes.txt"]}}

open valorant
{{"action":"open","args":["valorant"]}}

list downloads
{{"action":"list","args":["downloads"]}}

search resume.pdf
{{"action":"search","args":["resume.pdf"]}}

rename old.txt to new.txt
{{"action":"rename","args":["desktop/old.txt","new.txt"]}}

read file notes.txt
{{"action":"read_file","args":["desktop/notes.txt"]}}

show disk info
{{"action":"disk_info","args":[]}}

show system info
{{"action":"system_info","args":[]}}

open google.com
{{"action":"browser_open","args":["https://google.com"]}}

search python tutorial on google
{{"action":"browser_search","args":["python tutorial"]}}

create project folder then open vscode
{{"action":"automate","args":["create_folder:desktop/project","open:vscode"]}}

Command:
{command}
"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        raw_text = response.json().get("response", "").strip()
        json_text = extract_json(raw_text)
        if not json_text:
            return {"action": "unknown", "args": []}
        return json.loads(json_text)

    except json.JSONDecodeError:
        return {"action": "unknown", "args": []}
    except Exception as e:
        print(f"[AI Error] {e}")
        return {"action": "unknown", "args": []}


# ── CHAT RESPONSE ─────────────────────────────────────────────────────────────
def chat_response(command):
    """
    Normal conversational reply when no action is detected.
    Dual-mode: ARIA acts as chatbot fallback.
    """
    prompt = f"""You are ARIA, a helpful and friendly AI desktop assistant.
Answer the user concisely and clearly.
User: {command}
ARIA:"""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        return response.json().get("response", "I didn't understand that.").strip()
    except Exception:
        return "⚠️ Ollama is not running. Start it with: ollama serve"


# ── MEMORY SYSTEM ─────────────────────────────────────────────────────────────
class MemorySystem:
    """
    Remembers user actions and learns shortcuts.
    Example: 'open my project' → remembers last project path
    """
    def __init__(self):
        self.memory = {}          # key → value store
        self.action_log = []      # full history

    def remember(self, key, value):
        self.memory[key] = value

    def recall(self, key):
        return self.memory.get(key, None)

    def log_action(self, command, action, result):
        self.action_log.append({
            "command": command,
            "action": action,
            "result": result
        })
        # Auto-learn: if user created/opened something, remember it
        if action in ("create_folder", "open") and result:
            short_name = command.split()[-1]
            self.memory[short_name] = result

    def get_history(self):
        return self.action_log[-20:]  # last 20 actions

    def feedback(self, was_correct: bool):
        """
        Learning system: user says 'that was wrong' → system logs it.
        Can be used for future fine-tuning or rule correction.
        """
        if self.action_log:
            self.action_log[-1]["feedback"] = "correct" if was_correct else "wrong"


# Singleton memory instance shared across app
memory = MemorySystem()
