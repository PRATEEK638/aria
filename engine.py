"""
ARIA - Execution Engine
Routes AI action plans to the correct tool functions.
This is the bridge between ai.py and tools.py
"""

import tools
from ai import memory


def execute(action, args):
    """
    Central dispatcher: action + args → tool function → result string
    """
    try:
        if not isinstance(args, list):
            args = []

        # ── File Operations ───────────────────────────────────────────────────
        if action == "create_folder":
            if not args:
                return "❌ Missing folder path"
            return tools.create_folder(args[0])

        elif action == "create_file":
            if not args:
                return "❌ Missing file path"
            return tools.create_file(args[0])

        elif action == "move":
            if len(args) < 2:
                return "❌ Need source AND destination"
            return tools.move(args[0], args[1])

        elif action == "delete":
            if not args:
                return "❌ Missing path to delete"
            return tools.delete(args[0])

        elif action == "rename":
            if len(args) < 2:
                return "❌ Need original name AND new name"
            return tools.rename_item(args[0], args[1])

        elif action == "list":
            if not args:
                return "❌ Missing folder path"
            return tools.list_files(args[0])

        elif action == "read_file":
            if not args:
                return "❌ Missing file path"
            return tools.read_file(args[0])

        # ── Search ────────────────────────────────────────────────────────────
        elif action == "search":
            if not args:
                return "❌ Missing search term"
            found = tools.find_item(args[0])
            if found:
                return f"🔍 Found: {found}"
            return f"❌ Not found: {args[0]}"

        # ── App / File Opening ────────────────────────────────────────────────
        elif action == "open":
            if not args:
                return "❌ Missing app/file name"
            return tools.open_item(args[0])

        # ── System Info ───────────────────────────────────────────────────────
        elif action == "disk_info":
            return tools.disk_info()

        elif action == "system_info":
            return tools.system_info()

        # ── Browser Automation ────────────────────────────────────────────────
        elif action == "browser_open":
            if not args:
                return "❌ Missing URL"
            return tools.browser_open(args[0])

        elif action == "browser_search":
            if not args:
                return "❌ Missing search query"
            return tools.browser_search(args[0])

        # ── Multi-step Automation ─────────────────────────────────────────────
        elif action == "automate":
            if not args:
                return "❌ No automation steps provided"
            return tools.run_automation(args)

        else:
            return None  # Signal: not a known action → fall through to chat

    except Exception as e:
        return f"❌ Error: {e}"


def process_command(command):
    """
    Full pipeline:
      command → AI plan → execute → result
    Also handles memory, logging, feedback.
    Returns: (result_text, action_used)
    """
    from ai import get_plan, chat_response

    plan   = get_plan(command)
    action = plan.get("action", "unknown")
    args   = plan.get("args", [])

    if action == "unknown":
        reply = chat_response(command)
        memory.log_action(command, "chat", reply)
        return reply, "chat"

    result = execute(action, args)

    if result is None:
        # Unknown action → fallback to chat
        reply = chat_response(command)
        memory.log_action(command, "chat", reply)
        return reply, "chat"

    memory.log_action(command, action, result)
    return result, action
