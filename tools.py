"""
ARIA - Tools Module
Handles: file ops, app launching, system info, disk info, browser, search
"""

import subprocess
import sys

# ── Auto-install ──────────────────────────────────────────────────────────────
def _pip(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

try:
    import psutil
except ImportError:
    _pip("psutil==5.9.8")
    import psutil

import os
import shutil
import webbrowser
import platform

HOME = os.path.expanduser("~")

# ── Known paths ───────────────────────────────────────────────────────────────
KNOWN_PATHS = {
    "desktop":   os.path.join(HOME, "Desktop"),
    "downloads": os.path.join(HOME, "Downloads"),
    "documents": os.path.join(HOME, "Documents"),
    "music":     os.path.join(HOME, "Music"),
    "pictures":  os.path.join(HOME, "Pictures"),
    "videos":    os.path.join(HOME, "Videos"),
}

# ── App paths (edit these for your system) ────────────────────────────────────
APP_PATHS = {
    "valorant":   r"C:\Riot Games\Riot Client\RiotClientServices.exe --launch-product=valorant --launch-patchline=live",
    "brave":      r"C:\Users\heman\AppData\Local\BraveSoftware\Brave-Browser\Application\brave.exe",
    "edge":       r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "spotify":    r"C:\Users\heman\AppData\Roaming\Spotify\Spotify.exe",
    "whatsapp":   "start whatsapp:",
    "chrome":     r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "vscode":     r"C:\Users\heman\AppData\Local\Programs\Microsoft VS Code\Code.exe",
    "notepad":    "notepad.exe",
    "calculator": "calc.exe",
    "explorer":   "explorer.exe",
    "cmd":        "cmd.exe",
    "paint":      "mspaint.exe",
}


# ── PATH RESOLVER ─────────────────────────────────────────────────────────────
def resolve_path(p):
    if not p:
        return p
    p = p.strip().replace("\\", "/")
    p_lower = p.lower()

    # Handle "X drive" or "X drive/path"
    if "drive" in p_lower:
        parts = p_lower.split("drive")
        drive_letter = parts[0].strip()
        if drive_letter:
            drive_letter = drive_letter[-1].upper()
        else:
            drive_letter = "C"
        rest = parts[1].strip().lstrip("/").strip() if len(parts) > 1 else ""
        base = f"{drive_letter}:/"
        return os.path.join(base, rest.replace("/", os.sep)) if rest else base

    # Handle known folder names
    for key, value in KNOWN_PATHS.items():
        if p_lower.startswith(key):
            remainder = p[len(key):].lstrip("/").strip()
            return os.path.join(value, remainder) if remainder else value

    # Already absolute path
    if len(p) >= 2 and p[1] == ":":
        return p

    # Default → Desktop
    return os.path.join(KNOWN_PATHS["desktop"], p)


# ── SMART FILE SEARCH ─────────────────────────────────────────────────────────
def find_item(name, indexed=False):
    """
    Smart file search:
    1. Checks Desktop first (fast)
    2. Checks all known folders
    3. Falls back to full HOME search
    Returns first match path or None.
    """
    name_lower = name.lower()

    # Priority 1: Desktop
    desktop = KNOWN_PATHS["desktop"]
    if os.path.exists(desktop):
        for root, dirs, files in os.walk(desktop):
            for f in files:
                if name_lower in f.lower():
                    return os.path.join(root, f)
            for d in dirs:
                if name_lower in d.lower():
                    return os.path.join(root, d)

    # Priority 2: Known folders
    for folder in KNOWN_PATHS.values():
        if not os.path.exists(folder):
            continue
        for root, dirs, files in os.walk(folder):
            for f in files:
                if name_lower in f.lower():
                    return os.path.join(root, f)
            for d in dirs:
                if name_lower in d.lower():
                    return os.path.join(root, d)

    # Priority 3: Full HOME
    for root, dirs, files in os.walk(HOME):
        # Skip hidden/system folders
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in
                   ['AppData', 'node_modules', '__pycache__', '$RECYCLE.BIN']]
        for f in files:
            if name_lower in f.lower():
                return os.path.join(root, f)
        for d in dirs:
            if name_lower in d.lower():
                return os.path.join(root, d)

    return None


# ── FILE OPERATIONS ───────────────────────────────────────────────────────────
def create_folder(path):
    path = resolve_path(path)
    os.makedirs(path, exist_ok=True)
    return f"✅ Folder created: {path}"


def create_file(path):
    path = resolve_path(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("")
    return f"✅ File created: {path}"


def move(src, dest):
    src_path = resolve_path(src)
    # If src not found at resolved path, try searching
    if not os.path.exists(src_path):
        found = find_item(src)
        if found:
            src_path = found
        else:
            return f"❌ Source not found: {src}"
    dest_path = resolve_path(dest)
    shutil.move(src_path, dest_path)
    return f"✅ Moved: {src_path} → {dest_path}"


def delete(path):
    resolved = resolve_path(path)
    if not os.path.exists(resolved):
        found = find_item(path)
        if found:
            resolved = found
        else:
            return f"❌ Not found: {path}"
    if os.path.isfile(resolved):
        os.remove(resolved)
    elif os.path.isdir(resolved):
        shutil.rmtree(resolved)
    return f"🗑️ Deleted: {resolved}"


def rename_item(old, new_name):
    old_path = resolve_path(old)
    if not os.path.exists(old_path):
        found = find_item(old)
        if found:
            old_path = found
        else:
            return f"❌ Not found: {old}"
    parent = os.path.dirname(old_path)
    new_path = os.path.join(parent, new_name)
    os.rename(old_path, new_path)
    return f"✅ Renamed: {os.path.basename(old_path)} → {new_name}"


def list_files(path):
    resolved = resolve_path(path)
    if not os.path.exists(resolved):
        return f"❌ Path not found: {resolved}"
    items = os.listdir(resolved)
    if not items:
        return "📂 Folder is empty"
    result = []
    for item in sorted(items):
        full = os.path.join(resolved, item)
        icon = "📁" if os.path.isdir(full) else "📄"
        result.append(f"{icon} {item}")
    return "\n".join(result)


def read_file(path):
    resolved = resolve_path(path)
    if not os.path.exists(resolved):
        found = find_item(path)
        if found:
            resolved = found
        else:
            return f"❌ File not found: {path}"
    try:
        with open(resolved, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read(3000)  # max 3000 chars
        return f"📄 {resolved}\n\n{content}"
    except Exception as e:
        return f"❌ Cannot read file: {e}"


# ── SYSTEM INFO ───────────────────────────────────────────────────────────────
def disk_info():
    lines = ["💽 DISK INFORMATION\n"]
    for part in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(part.mountpoint)
            total  = usage.total  // (1024**3)
            used   = usage.used   // (1024**3)
            free   = usage.free   // (1024**3)
            pct    = usage.percent
            lines.append(
                f"Drive {part.device}\n"
                f"  Total: {total} GB  |  Used: {used} GB  |  Free: {free} GB  |  {pct}% used\n"
            )
        except PermissionError:
            continue
    return "\n".join(lines)


def system_info():
    cpu_pct  = psutil.cpu_percent(interval=1)
    ram      = psutil.virtual_memory()
    ram_used = ram.used  // (1024**2)
    ram_tot  = ram.total // (1024**2)
    ram_pct  = ram.percent
    uname    = platform.uname()
    return (
        f"🖥️  SYSTEM INFORMATION\n\n"
        f"OS       : {uname.system} {uname.release}\n"
        f"Machine  : {uname.machine}\n"
        f"Processor: {uname.processor or uname.machine}\n\n"
        f"CPU Usage: {cpu_pct}%\n"
        f"RAM Used : {ram_used} MB / {ram_tot} MB  ({ram_pct}%)\n"
    )


# ── APP LAUNCHER ──────────────────────────────────────────────────────────────
def open_item(name):
    name_lower = name.lower().strip()

    # 1. Known app
    if name_lower in APP_PATHS:
        try:
            subprocess.Popen(APP_PATHS[name_lower], shell=True)
            return f"🚀 Launched: {name}"
        except Exception as e:
            return f"❌ Error launching {name}: {e}"

    # 2. Resolved direct path
    path = resolve_path(name)
    if os.path.exists(path):
        os.startfile(path)
        return f"📂 Opened: {path}"

    # 3. Smart search
    found = find_item(name)
    if found:
        os.startfile(found)
        return f"🔍 Found & Opened: {found}"

    return f"❌ Not found: {name}"


# ── BROWSER AUTOMATION ────────────────────────────────────────────────────────
def browser_open(url):
    if not url.startswith("http"):
        url = "https://" + url
    webbrowser.open(url)
    return f"🌐 Opened in browser: {url}"


def browser_search(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"🔍 Googled: {query}"


# ── MULTI-STEP AUTOMATION ─────────────────────────────────────────────────────
def run_automation(steps):
    """
    Execute a chain of actions.
    steps: list of "action:arg" strings
    Example: ["create_folder:desktop/project", "open:vscode"]
    """
    results = []
    action_map = {
        "create_folder": create_folder,
        "create_file":   create_file,
        "delete":        delete,
        "list":          list_files,
        "open":          open_item,
        "search":        find_item,
        "browser_open":  browser_open,
        "browser_search":browser_search,
        "disk_info":     lambda _: disk_info(),
        "system_info":   lambda _: system_info(),
    }
    for step in steps:
        if ":" in step:
            act, arg = step.split(":", 1)
        else:
            act, arg = step, ""
        act = act.strip()
        arg = arg.strip()
        fn = action_map.get(act)
        if fn:
            try:
                res = fn(arg) if arg else fn("")
                results.append(f"✅ {act}({arg}): {res}")
            except Exception as e:
                results.append(f"❌ {act}({arg}): {e}")
        else:
            results.append(f"⚠️ Unknown step: {act}")
    return "\n".join(results)
