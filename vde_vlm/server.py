"""
vde_vlm.server
~~~~~~~~~~~~~~
Model Context Protocol (MCP) server for VirtualBox VM Control.
Exposes standard tool declarations over stdio for LLM / VLM pair-programmers.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Dict, List

from vde_vlm.core import VBoxVM
from vde_vlm.vbox import list_vms
from vde_vlm.vision import clean_temp_artifacts

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logger = logging.getLogger("vde_vlm.server")

# Tool definitions
TOOLS = [
    {
        "name": "vm_list",
        "description": "List all VirtualBox virtual machines and their running states.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "vm_start",
        "description": "Start a virtual machine (headless or GUI).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "headless": {"type": "boolean", "description": "True to run headless without host window", "default": True},
            },
            "required": ["vm"],
        },
    },
    {
        "name": "vm_stop",
        "description": "Stop or save state of a virtual machine.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "mode": {"type": "string", "enum": ["poweroff", "savestate", "acpipowerbutton"], "default": "poweroff"},
            },
            "required": ["vm"],
        },
    },
    {
        "name": "vm_observe",
        "description": "Ultra-efficient VM screen observation. Defaults to 'text' mode (~50-100 tokens, saving 95%+ of weekly VLM quota). Use 'compact' for a 512px downscaled low-token thumbnail (~258 tokens).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "mode": {
                    "type": "string",
                    "enum": ["text", "compact", "full"],
                    "default": "text",
                    "description": "Efficiency mode: 'text' (zero vision tokens, structured UI text), 'compact' (512px low-token thumbnail), 'full' (raw image)",
                },
                "grid": {"type": "boolean", "description": "Generate coordinate grid (for compact or full mode)", "default": False},
                "skip_if_unchanged": {"type": "boolean", "description": "Skip re-sending if screen has not changed", "default": True},
            },
            "required": ["vm"],
        },
    },
    {
        "name": "vm_click",
        "description": "Click at specific pixel coordinates on the VM screen and broadcast agent cursor to collaborative live canvas.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "x": {"type": "integer", "description": "X coordinate in pixels"},
                "y": {"type": "integer", "description": "Y coordinate in pixels"},
                "button": {"type": "string", "enum": ["left", "right", "middle"], "default": "left"},
                "double": {"type": "boolean", "default": False},
            },
            "required": ["vm", "x", "y"],
        },
    },
    {
        "name": "vm_type",
        "description": "Type a text string into the active VM window.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "text": {"type": "string", "description": "Text to type"},
                "enter": {"type": "boolean", "description": "Press enter after typing", "default": False},
            },
            "required": ["vm", "text"],
        },
    },
    {
        "name": "vm_key",
        "description": "Press a key or key combination (e.g. 'ctrl+alt+t', 'super', 'enter', 'esc').",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "key": {"type": "string", "description": "Key or combination to press"},
            },
            "required": ["vm", "key"],
        },
    },
    {
        "name": "vm_batch",
        "description": "Execute an atomic sequence of actions (compound interaction: type, enter, wait, click, key chords) in a single turn.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "steps": {
                    "type": "array",
                    "description": "List of action objects or shorthand strings (e.g. ['type:echo hello|enter', 'wait:0.5', 'click:450,720'])",
                    "items": {"type": "string"},
                },
            },
            "required": ["vm", "steps"],
        },
    },
    {
        "name": "vm_exec",
        "description": "Execute a shell command inside the guest VM via guestcontrol.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "cmd": {"type": "string", "description": "Command string to run"},
                "user": {"type": "string", "description": "Guest username", "default": "victor"},
                "password": {"type": "string", "description": "Guest password", "default": ""},
            },
            "required": ["vm", "cmd"],
        },
    },
    {
        "name": "vm_snapshot",
        "description": "Take a snapshot of the virtual machine.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "name": {"type": "string", "description": "Snapshot name"},
                "description": {"type": "string", "description": "Optional notes"},
            },
            "required": ["vm", "name"],
        },
    },
    {
        "name": "vm_restore",
        "description": "Restore virtual machine to a snapshot.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "name": {"type": "string", "description": "Snapshot name or UUID"},
            },
            "required": ["vm", "name"],
        },
    },
    {
        "name": "vm_clean",
        "description": "Clean up stale temporary screenshot files from system temp.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "vm_detect",
        "description": "Detect all UI buttons, labels, and text elements with Set-of-Marks bounding boxes and centroid coordinates using the visual recognition / OCR model.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "confidence": {"type": "number", "description": "Minimum confidence threshold (0.0 to 1.0)", "default": 0.35},
            },
            "required": ["vm"],
        },
    },
    {
        "name": "vm_find",
        "description": "Locate a specific button or text label on the VM screen and return its centroid (x, y) coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "query": {"type": "string", "description": "Text label or button name to search for (e.g. 'Next', 'Cancel', 'Install')"},
            },
            "required": ["vm", "query"],
        },
    },
    {
        "name": "vm_click_text",
        "description": "Find a button or text label on screen and autonomously click its centroid coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "vm": {"type": "string", "description": "VM name or UUID"},
                "query": {"type": "string", "description": "Target button text to click"},
                "double": {"type": "boolean", "default": False},
            },
            "required": ["vm", "query"],
        },
    },
]


def dispatch_tool(name: str, args: Dict[str, Any]) -> Any:
    """Execute the requested tool."""
    if name == "vm_list":
        vms = list_vms()
        return [{"name": m["name"], "uuid": m["uuid"], "state": VBoxVM(m["name"]).state} for m in vms]

    if name == "vm_clean":
        count = clean_temp_artifacts()
        return {"cleaned_files": count}

    vm_name = args.get("vm")
    if not vm_name:
        raise ValueError("Missing 'vm' parameter")

    vm = VBoxVM(vm_name)

    if name == "vm_start":
        headless = args.get("headless", True)
        ok = vm.start(headless=headless)
        return {"started": ok, "state": vm.state}

    elif name == "vm_stop":
        mode = args.get("mode", "poweroff")
        ok = vm.stop(mode=mode)
        return {"stopped": ok, "state": vm.state}

    elif name == "vm_observe":
        mode = args.get("mode", "text")
        grid = args.get("grid", False)
        skip = args.get("skip_if_unchanged", True)
        return vm.observe(mode=mode, grid=grid, skip_if_unchanged=skip)

    elif name == "vm_click":
        x = int(args["x"])
        y = int(args["y"])
        btn = args.get("button", "left")
        double = args.get("double", False)
        return vm.click(x, y, button=btn, double=double)

    elif name == "vm_type":
        text = args["text"]
        enter = args.get("enter", False)
        vm.type(text, press_enter=enter)
        return {"typed": text, "enter": enter}

    elif name == "vm_key":
        key = args["key"]
        vm.press_key(key)
        return {"pressed": key}

    elif name == "vm_batch":
        steps = args.get("steps", [])
        return vm.batch(steps)

    elif name == "vm_exec":
        cmd = args["cmd"]
        user = args.get("user")
        pwd = args.get("password")
        code, stdout, stderr = vm.exec(cmd, username=user, password=pwd, check=False)
        return {"returncode": code, "stdout": stdout, "stderr": stderr}

    elif name == "vm_snapshot":
        snap_name = args["name"]
        desc = args.get("description")
        vm.snapshot(snap_name, description=desc)
        return {"snapshot": snap_name}

    elif name == "vm_restore":
        snap_name = args["name"]
        vm.restore(snap_name)
        return {"restored": snap_name}

    elif name == "vm_detect":
        conf = float(args.get("confidence", 0.35))
        return vm.detect_elements(confidence=conf)

    elif name == "vm_find":
        query = args["query"]
        el = vm.find_element(query)
        return el or {"found": False, "query": query}

    elif name == "vm_click_text":
        query = args["query"]
        double = args.get("double", False)
        return vm.click_element(query, double=double)

    raise ValueError(f"Unknown tool: {name}")


def run_stdio_server():
    """Run MCP JSON-RPC protocol loop over stdio."""
    logger.info("VDE-VLM-ACCESS MCP Server starting...")
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue

        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")

            if method == "tools/list":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}}
            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                res = dispatch_tool(tool_name, tool_args)
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]},
                }
            elif method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "vde-vlm-server", "version": "2.0.0"},
                        "capabilities": {"tools": {}},
                    },
                }
            else:
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                }

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        except Exception as exc:
            logger.exception("Error processing MCP request")
            err_resp = {
                "jsonrpc": "2.0",
                "id": req.get("id") if "req" in locals() else None,
                "error": {"code": -32000, "message": str(exc)},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_stdio_server()
