"""
ARIA - AI Desktop Assistant
Main GUI Application using CustomTkinter
Run: python main.py
"""

# ══════════════════════════════════════════════════════════════════════════════
# AUTO-INSTALL ALL DEPENDENCIES BEFORE ANYTHING ELSE
# ══════════════════════════════════════════════════════════════════════════════
import subprocess
import sys
import os

def pip_install(package):
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", package, "--quiet"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

REQUIRED = [
    ("customtkinter",    "customtkinter==5.2.2"),
    ("requests",         "requests==2.31.0"),
    ("PIL",              "Pillow==10.3.0"),
    ("psutil",           "psutil==5.9.8"),
    ("pyttsx3",          "pyttsx3==2.90"),
    ("speech_recognition","SpeechRecognition==3.10.0"),
]

print("ARIA Starting — checking dependencies...")
for module, pkg in REQUIRED:
    try:
        __import__(module)
    except ImportError:
        print(f"  Installing {pkg}...")
        try:
            pip_install(pkg)
        except Exception as e:
            print(f"  Warning: Could not install {pkg}: {e}")

# PyAudio separately (tricky on some systems)
try:
    import pyaudio  # noqa
except ImportError:
    try:
        pip_install("pyaudio==0.2.14")
    except Exception:
        pass  # Voice still works with a helpful error message

print("  Dependencies OK")

# ══════════════════════════════════════════════════════════════════════════════
# IMPORTS
# ══════════════════════════════════════════════════════════════════════════════
import customtkinter as ctk
import threading
import time
from datetime import datetime

from engine import process_command
from ai import memory
from voice import speak, listen, is_voice_available
import tools

# ══════════════════════════════════════════════════════════════════════════════
# THEME CONFIG
# ══════════════════════════════════════════════════════════════════════════════
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ── Color palette ─────────────────────────────────────────────────────────────
BG_MAIN    = "#0d0d0d"
BG_SIDEBAR = "#111111"
BG_CHAT    = "#141414"
BG_INPUT   = "#1a1a1a"
BG_BUBBLE_AI   = "#1e2a3a"
BG_BUBBLE_USER = "#1a2a1a"
ACCENT     = "#00d4ff"
ACCENT2    = "#00ff88"
TEXT_MAIN  = "#e8e8e8"
TEXT_DIM   = "#888888"
TEXT_ERROR = "#ff4444"
BORDER     = "#2a2a2a"

# ══════════════════════════════════════════════════════════════════════════════
# HELPER: timestamp
# ══════════════════════════════════════════════════════════════════════════════
def now():
    return datetime.now().strftime("%H:%M")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APP WINDOW
# ══════════════════════════════════════════════════════════════════════════════
class ARIAApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window setup
        self.title("ARIA — AI Desktop Assistant")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(fg_color=BG_MAIN)

        # State
        self.voice_mode  = False
        self.tts_enabled = ctk.BooleanVar(value=True)
        self.listening   = False
        self.current_tab = "chat"

        self._build_ui()
        self._welcome_message()

    # ── BUILD UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Grid: sidebar | main
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_main()

    # ── SIDEBAR ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, fg_color=BG_SIDEBAR, corner_radius=0, width=220,
                          border_width=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(10, weight=1)

        # Logo
        logo = ctk.CTkLabel(sb, text="◈  ARIA",
                            font=ctk.CTkFont("Courier New", 22, "bold"),
                            text_color=ACCENT)
        logo.grid(row=0, column=0, padx=20, pady=(22, 4), sticky="w")

        sub = ctk.CTkLabel(sb, text="AI Desktop Assistant",
                           font=ctk.CTkFont("Courier New", 10),
                           text_color=TEXT_DIM)
        sub.grid(row=1, column=0, padx=22, pady=(0, 20), sticky="w")

        # Separator
        sep = ctk.CTkFrame(sb, height=1, fg_color=BORDER)
        sep.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        # Nav buttons
        nav_items = [
            ("💬  Chat",         "chat"),
            ("🔍  File Search",  "search"),
            ("💽  Disk Info",    "disk"),
            ("🖥️  System Info",  "system"),
            ("📜  History",      "history"),
        ]
        self._nav_btns = {}
        for i, (label, key) in enumerate(nav_items):
            btn = ctk.CTkButton(
                sb, text=label,
                font=ctk.CTkFont("Courier New", 13),
                fg_color="transparent",
                hover_color="#1e2e1e",
                text_color=TEXT_MAIN,
                anchor="w",
                height=38,
                corner_radius=8,
                command=lambda k=key: self._switch_tab(k)
            )
            btn.grid(row=3+i, column=0, padx=10, pady=2, sticky="ew")
            self._nav_btns[key] = btn

        # Separator
        sep2 = ctk.CTkFrame(sb, height=1, fg_color=BORDER)
        sep2.grid(row=9, column=0, sticky="ew", padx=10, pady=10)

        # TTS toggle
        tts_frame = ctk.CTkFrame(sb, fg_color="transparent")
        tts_frame.grid(row=10, column=0, padx=14, pady=4, sticky="sw")
        ctk.CTkLabel(tts_frame, text="🔊 Voice Reply",
                     font=ctk.CTkFont("Courier New", 11),
                     text_color=TEXT_DIM).pack(side="left", padx=(0,6))
        ctk.CTkSwitch(tts_frame, text="", variable=self.tts_enabled,
                      width=40, height=20,
                      progress_color=ACCENT2,
                      button_color=ACCENT).pack(side="left")

        # Status dot
        self.status_label = ctk.CTkLabel(
            sb, text="● Ollama: checking…",
            font=ctk.CTkFont("Courier New", 10),
            text_color=TEXT_DIM
        )
        self.status_label.grid(row=11, column=0, padx=14, pady=(10,16), sticky="sw")
        threading.Thread(target=self._check_ollama, daemon=True).start()

    # ── MAIN AREA ─────────────────────────────────────────────────────────────
    def _build_main(self):
        self.main_frame = ctk.CTkFrame(self, fg_color=BG_MAIN, corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # ── Tab: Chat ─────────────────────────────────────────────────────────
        self.tab_chat = ctk.CTkFrame(self.main_frame, fg_color=BG_MAIN)
        self.tab_chat.grid(row=0, column=0, sticky="nsew")
        self.tab_chat.grid_rowconfigure(0, weight=1)
        self.tab_chat.grid_columnconfigure(0, weight=1)
        self._build_chat_tab()

        # ── Tab: Search ───────────────────────────────────────────────────────
        self.tab_search = ctk.CTkFrame(self.main_frame, fg_color=BG_MAIN)
        self.tab_search.grid(row=0, column=0, sticky="nsew")
        self._build_search_tab()

        # ── Tab: Disk ─────────────────────────────────────────────────────────
        self.tab_disk = ctk.CTkFrame(self.main_frame, fg_color=BG_MAIN)
        self.tab_disk.grid(row=0, column=0, sticky="nsew")
        self._build_disk_tab()

        # ── Tab: System ───────────────────────────────────────────────────────
        self.tab_system = ctk.CTkFrame(self.main_frame, fg_color=BG_MAIN)
        self.tab_system.grid(row=0, column=0, sticky="nsew")
        self._build_system_tab()

        # ── Tab: History ──────────────────────────────────────────────────────
        self.tab_history = ctk.CTkFrame(self.main_frame, fg_color=BG_MAIN)
        self.tab_history.grid(row=0, column=0, sticky="nsew")
        self._build_history_tab()

        self._switch_tab("chat")

    # ── CHAT TAB ──────────────────────────────────────────────────────────────
    def _build_chat_tab(self):
        self.tab_chat.grid_rowconfigure(0, weight=1)
        self.tab_chat.grid_columnconfigure(0, weight=1)

        # Header
        hdr = ctk.CTkFrame(self.tab_chat, fg_color=BG_SIDEBAR, height=54, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="💬  Chat with ARIA",
                     font=ctk.CTkFont("Courier New", 15, "bold"),
                     text_color=ACCENT).pack(side="left", padx=20, pady=12)
        self.thinking_label = ctk.CTkLabel(hdr, text="",
                                           font=ctk.CTkFont("Courier New", 11),
                                           text_color=ACCENT2)
        self.thinking_label.pack(side="right", padx=20)

        # Chat scroll area
        self.chat_scroll = ctk.CTkScrollableFrame(
            self.tab_chat, fg_color=BG_CHAT, corner_radius=0
        )
        self.chat_scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.chat_scroll.grid_columnconfigure(0, weight=1)
        self.tab_chat.grid_rowconfigure(1, weight=1)

        # Input bar
        input_bar = ctk.CTkFrame(self.tab_chat, fg_color=BG_INPUT, height=64,
                                 corner_radius=0)
        input_bar.grid(row=2, column=0, sticky="ew")
        input_bar.grid_propagate(False)
        input_bar.grid_columnconfigure(0, weight=1)

        self.cmd_entry = ctk.CTkEntry(
            input_bar,
            placeholder_text="Type a command or ask anything…",
            font=ctk.CTkFont("Courier New", 13),
            fg_color="#1e1e1e",
            border_color=BORDER,
            text_color=TEXT_MAIN,
            height=40,
            corner_radius=8,
        )
        self.cmd_entry.grid(row=0, column=0, padx=(14, 8), pady=12, sticky="ew")
        self.cmd_entry.bind("<Return>", self._on_enter)

        self.send_btn = ctk.CTkButton(
            input_bar, text="Send",
            font=ctk.CTkFont("Courier New", 12, "bold"),
            fg_color=ACCENT, text_color="#000000",
            hover_color="#00b0d8",
            width=74, height=40, corner_radius=8,
            command=self._send_command
        )
        self.send_btn.grid(row=0, column=1, padx=(0, 8), pady=12)

        self.mic_btn = ctk.CTkButton(
            input_bar, text="🎙",
            font=ctk.CTkFont("Segoe UI Emoji", 16),
            fg_color="#1e1e1e", text_color=TEXT_MAIN,
            hover_color="#2e2e2e",
            width=46, height=40, corner_radius=8,
            command=self._voice_input
        )
        self.mic_btn.grid(row=0, column=2, padx=(0, 14), pady=12)

    # ── SEARCH TAB ────────────────────────────────────────────────────────────
    def _build_search_tab(self):
        self.tab_search.grid_rowconfigure(2, weight=1)
        self.tab_search.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self.tab_search, fg_color=BG_SIDEBAR, height=54, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🔍  Smart File Search",
                     font=ctk.CTkFont("Courier New", 15, "bold"),
                     text_color=ACCENT).pack(side="left", padx=20, pady=12)

        # Search bar
        sf = ctk.CTkFrame(self.tab_search, fg_color=BG_INPUT, height=62, corner_radius=0)
        sf.grid(row=1, column=0, sticky="ew")
        sf.grid_propagate(False)
        sf.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(
            sf, placeholder_text="Enter file or folder name to search…",
            font=ctk.CTkFont("Courier New", 13),
            fg_color="#1e1e1e", border_color=BORDER,
            text_color=TEXT_MAIN, height=38, corner_radius=8
        )
        self.search_entry.grid(row=0, column=0, padx=(14,8), pady=12, sticky="ew")
        self.search_entry.bind("<Return>", self._do_search)

        ctk.CTkButton(
            sf, text="Search", width=90, height=38,
            font=ctk.CTkFont("Courier New", 12, "bold"),
            fg_color=ACCENT, text_color="#000",
            hover_color="#00b0d8", corner_radius=8,
            command=self._do_search
        ).grid(row=0, column=1, padx=(0,14), pady=12)

        # Results
        self.search_result = ctk.CTkTextbox(
            self.tab_search, fg_color=BG_CHAT,
            font=ctk.CTkFont("Courier New", 12),
            text_color=TEXT_MAIN, corner_radius=0,
            border_width=0
        )
        self.search_result.grid(row=2, column=0, sticky="nsew")
        self.search_result.configure(state="disabled")

    # ── DISK TAB ──────────────────────────────────────────────────────────────
    def _build_disk_tab(self):
        self.tab_disk.grid_rowconfigure(1, weight=1)
        self.tab_disk.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self.tab_disk, fg_color=BG_SIDEBAR, height=54, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="💽  Disk Information",
                     font=ctk.CTkFont("Courier New", 15, "bold"),
                     text_color=ACCENT).pack(side="left", padx=20, pady=12)
        ctk.CTkButton(hdr, text="⟳ Refresh", width=90, height=30,
                      font=ctk.CTkFont("Courier New", 11),
                      fg_color="transparent", border_color=ACCENT,
                      border_width=1, text_color=ACCENT,
                      hover_color="#001e2a", corner_radius=6,
                      command=self._load_disk).pack(side="right", padx=20, pady=12)

        self.disk_box = ctk.CTkTextbox(
            self.tab_disk, fg_color=BG_CHAT,
            font=ctk.CTkFont("Courier New", 13),
            text_color=TEXT_MAIN, corner_radius=0
        )
        self.disk_box.grid(row=1, column=0, sticky="nsew")
        self.disk_box.configure(state="disabled")

    # ── SYSTEM TAB ────────────────────────────────────────────────────────────
    def _build_system_tab(self):
        self.tab_system.grid_rowconfigure(1, weight=1)
        self.tab_system.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self.tab_system, fg_color=BG_SIDEBAR, height=54, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="🖥️  System Information",
                     font=ctk.CTkFont("Courier New", 15, "bold"),
                     text_color=ACCENT).pack(side="left", padx=20, pady=12)
        ctk.CTkButton(hdr, text="⟳ Refresh", width=90, height=30,
                      font=ctk.CTkFont("Courier New", 11),
                      fg_color="transparent", border_color=ACCENT,
                      border_width=1, text_color=ACCENT,
                      hover_color="#001e2a", corner_radius=6,
                      command=self._load_system).pack(side="right", padx=20, pady=12)

        self.system_box = ctk.CTkTextbox(
            self.tab_system, fg_color=BG_CHAT,
            font=ctk.CTkFont("Courier New", 13),
            text_color=TEXT_MAIN, corner_radius=0
        )
        self.system_box.grid(row=1, column=0, sticky="nsew")
        self.system_box.configure(state="disabled")

    # ── HISTORY TAB ───────────────────────────────────────────────────────────
    def _build_history_tab(self):
        self.tab_history.grid_rowconfigure(1, weight=1)
        self.tab_history.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(self.tab_history, fg_color=BG_SIDEBAR, height=54, corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)
        ctk.CTkLabel(hdr, text="📜  Command History",
                     font=ctk.CTkFont("Courier New", 15, "bold"),
                     text_color=ACCENT).pack(side="left", padx=20, pady=12)
        ctk.CTkButton(hdr, text="⟳ Refresh", width=90, height=30,
                      font=ctk.CTkFont("Courier New", 11),
                      fg_color="transparent", border_color=ACCENT,
                      border_width=1, text_color=ACCENT,
                      hover_color="#001e2a", corner_radius=6,
                      command=self._load_history).pack(side="right", padx=20, pady=12)

        self.history_box = ctk.CTkTextbox(
            self.tab_history, fg_color=BG_CHAT,
            font=ctk.CTkFont("Courier New", 12),
            text_color=TEXT_MAIN, corner_radius=0
        )
        self.history_box.grid(row=1, column=0, sticky="nsew")
        self.history_box.configure(state="disabled")

    # ── TAB SWITCHER ──────────────────────────────────────────────────────────
    def _switch_tab(self, key):
        self.current_tab = key
        tab_map = {
            "chat":    self.tab_chat,
            "search":  self.tab_search,
            "disk":    self.tab_disk,
            "system":  self.tab_system,
            "history": self.tab_history,
        }
        for k, frame in tab_map.items():
            if k == key:
                frame.tkraise()
            # Highlight nav button
            if k in self._nav_btns:
                self._nav_btns[k].configure(
                    fg_color="#002a2a" if k == key else "transparent",
                    text_color=ACCENT if k == key else TEXT_MAIN
                )

        # Load data for info tabs
        if key == "disk":
            threading.Thread(target=self._load_disk, daemon=True).start()
        elif key == "system":
            threading.Thread(target=self._load_system, daemon=True).start()
        elif key == "history":
            self._load_history()

    # ── CHAT BUBBLE ───────────────────────────────────────────────────────────
    def _add_bubble(self, text, sender="user"):
        is_user = (sender == "user")
        bg     = BG_BUBBLE_USER if is_user else BG_BUBBLE_AI
        anchor = "e" if is_user else "w"
        prefix = "You" if is_user else "ARIA"
        color  = ACCENT2 if is_user else ACCENT

        row = len(self.chat_scroll.winfo_children())

        outer = ctk.CTkFrame(self.chat_scroll, fg_color="transparent")
        outer.grid(row=row, column=0, sticky="ew", padx=12, pady=4)
        outer.grid_columnconfigure(0, weight=1)

        # Label row
        lbl_frame = ctk.CTkFrame(outer, fg_color="transparent")
        lbl_frame.pack(anchor=anchor, fill="x")
        ctk.CTkLabel(lbl_frame, text=f"{prefix}  ",
                     font=ctk.CTkFont("Courier New", 10, "bold"),
                     text_color=color).pack(side="left" if not is_user else "right")
        ctk.CTkLabel(lbl_frame, text=now(),
                     font=ctk.CTkFont("Courier New", 9),
                     text_color=TEXT_DIM).pack(side="left" if not is_user else "right")

        # Bubble
        bubble = ctk.CTkTextbox(
            outer,
            fg_color=bg,
            font=ctk.CTkFont("Courier New", 12),
            text_color=TEXT_MAIN,
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
            wrap="word",
            height=self._calc_height(text),
        )
        bubble.pack(anchor=anchor, fill="x" if not is_user else None,
                    padx=(0 if not is_user else 60, 0 if is_user else 60))
        bubble.insert("end", text)
        bubble.configure(state="disabled")

        self._scroll_to_bottom()

    def _calc_height(self, text):
        lines = text.count("\n") + 1
        chars = len(text)
        estimated = max(lines, chars // 60 + 1)
        return min(max(estimated * 22 + 16, 44), 400)

    def _scroll_to_bottom(self):
        self.after(50, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))

    # ── SEND / PROCESS ────────────────────────────────────────────────────────
    def _on_enter(self, event):
        self._send_command()

    def _send_command(self):
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
        self.cmd_entry.delete(0, "end")
        self._add_bubble(cmd, sender="user")
        self._set_thinking(True)
        self.send_btn.configure(state="disabled")
        threading.Thread(target=self._process_async, args=(cmd,), daemon=True).start()

    def _process_async(self, cmd):
        result, action = process_command(cmd)
        self.after(0, lambda: self._on_result(result, action))

    def _on_result(self, result, action):
        self._set_thinking(False)
        self.send_btn.configure(state="normal")
        self._add_bubble(result, sender="aria")
        if self.tts_enabled.get():
            threading.Thread(target=speak, args=(result,), daemon=True).start()

    def _set_thinking(self, thinking):
        if thinking:
            self.thinking_label.configure(text="⠋ ARIA thinking…")
            self._animate_thinking()
        else:
            self.thinking_label.configure(text="")

    def _animate_thinking(self):
        frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        current = getattr(self, "_think_frame", 0)
        if self.thinking_label.cget("text") == "":
            return
        self.thinking_label.configure(text=f"{frames[current % len(frames)]} ARIA thinking…")
        self._think_frame = current + 1
        self.after(100, self._animate_thinking)

    # ── VOICE INPUT ───────────────────────────────────────────────────────────
    def _voice_input(self):
        if self.listening:
            return
        self.listening = True
        self.mic_btn.configure(text="🔴", fg_color="#3a0000")
        threading.Thread(target=self._listen_async, daemon=True).start()

    def _listen_async(self):
        text, err = listen()
        self.after(0, lambda: self._on_listen_done(text, err))

    def _on_listen_done(self, text, err):
        self.listening = False
        self.mic_btn.configure(text="🎙", fg_color="#1e1e1e")
        if err:
            self._add_bubble(f"🎙 Voice error: {err}", sender="aria")
        elif text:
            self._add_bubble(f"🎙 You said: {text}", sender="user")
            self._set_thinking(True)
            self.send_btn.configure(state="disabled")
            threading.Thread(target=self._process_async, args=(text,), daemon=True).start()

    # ── SEARCH ────────────────────────────────────────────────────────────────
    def _do_search(self, event=None):
        query = self.search_entry.get().strip()
        if not query:
            return
        self._set_search_result(f"🔍 Searching for: {query}\nPlease wait…")
        threading.Thread(target=self._search_async, args=(query,), daemon=True).start()

    def _search_async(self, query):
        found = tools.find_item(query)
        if found:
            result = f"✅ Found: {found}"
        else:
            result = f"❌ Not found: {query}"
        self.after(0, lambda: self._set_search_result(result))

    def _set_search_result(self, text):
        self.search_result.configure(state="normal")
        self.search_result.delete("1.0", "end")
        self.search_result.insert("end", text)
        self.search_result.configure(state="disabled")

    # ── DISK INFO ─────────────────────────────────────────────────────────────
    def _load_disk(self):
        self.after(0, lambda: self._set_box(self.disk_box, "Loading disk info…"))
        info = tools.disk_info()
        self.after(0, lambda: self._set_box(self.disk_box, info))

    # ── SYSTEM INFO ───────────────────────────────────────────────────────────
    def _load_system(self):
        self.after(0, lambda: self._set_box(self.system_box, "Loading system info…"))
        info = tools.system_info()
        self.after(0, lambda: self._set_box(self.system_box, info))

    # ── HISTORY ───────────────────────────────────────────────────────────────
    def _load_history(self):
        logs = memory.get_history()
        if not logs:
            self._set_box(self.history_box, "No command history yet.\nStart chatting with ARIA!")
            return
        lines = []
        for i, entry in enumerate(reversed(logs), 1):
            lines.append(f"[{i}] Command : {entry.get('command','')}")
            lines.append(f"     Action  : {entry.get('action','')}")
            fb = entry.get('feedback', '')
            if fb:
                lines.append(f"     Feedback: {fb}")
            lines.append("")
        self._set_box(self.history_box, "\n".join(lines))

    def _set_box(self, box, text):
        box.configure(state="normal")
        box.delete("1.0", "end")
        box.insert("end", text)
        box.configure(state="disabled")

    # ── OLLAMA STATUS CHECK ───────────────────────────────────────────────────
    def _check_ollama(self):
        try:
            import requests as req
            r = req.get("YOUR_API_KEY", timeout=3)
            if r.status_code == 200:
                self.after(0, lambda: self.status_label.configure(
                    text="● Ollama: online", text_color=ACCENT2))
                return
        except Exception:
            pass
        self.after(0, lambda: self.status_label.configure(
            text="● Ollama: offline", text_color=TEXT_ERROR))

    # ── WELCOME ───────────────────────────────────────────────────────────────
    def _welcome_message(self):
        self._add_bubble(
            "Hello! I'm ARIA — your AI Desktop Assistant.\n\n"
            "I can help you:\n"
            "• Create, move, delete, rename files & folders\n"
            "• Open apps (Valorant, Brave, VS Code…)\n"
            "• Search files on your system\n"
            "• Run multi-step automation workflows\n"
            "• Open websites & search Google\n"
            "• Show disk & system info\n"
            "• Answer questions in chat mode\n\n"
            "Try: 'create folder myproject in desktop'\n"
            "Or : 'open brave'\n"
            "Or : 'show disk info'\n"
            "Or : 'search notes.txt'\n\n"
            "💡 Tip: Click 🎙 to use voice input!",
            sender="aria"
        )


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = ARIAApp()
    app.mainloop()
