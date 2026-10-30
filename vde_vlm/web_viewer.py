"""
vde_vlm.web_viewer
~~~~~~~~~~~~~~~~~~
Google Stitch-style collaborative live web viewer for VirtualBox VMs.
Enables simultaneous human & VLM interaction with live video streaming,
collaborative cursor presence (showing '🤖 Gemini' cursor badges in real-time),
direct click/type injection from the browser, and compound batch macro execution.
Default Port: 7891 (as requested).
"""

from __future__ import annotations

import asyncio
import io
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional, Set

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
import uvicorn

from vde_vlm.core import VBoxVM
from vde_vlm.macro import execute_batch
from vde_vlm.vbox import list_vms
from vde_vlm.vision import clean_temp_artifacts, get_rolling_screen_path, take_screenshot

logger = logging.getLogger("vde_vlm.web_viewer")

app = FastAPI(title="VDE-VLM Collaborative Studio", version="2.0.0")

# Active WebSocket connections
_active_sockets: Set[WebSocket] = set()

# Global state for active VM and collaborative agent cursor
_current_vm_name = os.environ.get("VDE_DEFAULT_VM", "vmvdebox7")
_agent_cursor_state: Dict[str, Any] = {
    "x": 300,
    "y": 200,
    "label": "Gemini",
    "is_click": False,
    "last_updated": 0,
}


def get_current_vm() -> VBoxVM:
    global _current_vm_name
    vms = list_vms()
    names = [m["name"] for m in vms]
    if _current_vm_name not in names and names:
        _current_vm_name = names[0]
    return VBoxVM(_current_vm_name)


async def broadcast_ws(message: Dict[str, Any]):
    """Broadcast JSON payload to all connected browser clients."""
    dead = set()
    for ws in _active_sockets:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _active_sockets.discard(ws)


def notify_agent_action(x: int, y: int, is_click: bool = True, label: str = "Gemini"):
    """Update global agent cursor state and broadcast to all live viewers."""
    global _agent_cursor_state
    _agent_cursor_state = {
        "x": x,
        "y": y,
        "label": label,
        "is_click": is_click,
        "last_updated": time.time(),
    }
    asyncio.run_coroutine_threadsafe(
        broadcast_ws({"type": "agent_cursor", **_agent_cursor_state}),
        asyncio.get_event_loop() if asyncio.get_event_loop().is_running() else asyncio.new_event_loop(),
    )


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>VDE-VLM Studio — Collaborative VM Canvas</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    :root {
      --bg: #0b0d14;
      --panel: #131722;
      --border: #232a3b;
      --accent: #8b5cf6;
      --accent-hover: #7c3aed;
      --cyan: #06b6d4;
      --green: #10b981;
      --red: #ef4444;
      --text: #e2e8f0;
      --muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      height: 100vh;
    }
    /* Header */
    header {
      background: var(--panel);
      border-bottom: 1px solid var(--border);
      padding: 10px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      z-index: 50;
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      font-size: 16px;
      letter-spacing: -0.02em;
    }
    .brand-pill {
      background: linear-gradient(135deg, var(--accent), var(--cyan));
      color: #fff;
      padding: 4px 8px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    select, button, input {
      background: #1e2433;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 6px 12px;
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.15s ease;
    }
    select:focus, input:focus { outline: none; border-color: var(--accent); }
    button:hover { background: #2a3348; border-color: #3b4764; }
    button.primary { background: var(--accent); border-color: var(--accent-hover); color: white; }
    button.primary:hover { background: var(--accent-hover); }
    button.danger { background: rgba(239, 68, 68, 0.2); border-color: var(--red); color: var(--red); }
    button.danger:hover { background: var(--red); color: white; }
    button.active { background: #2e3852; border-color: var(--cyan); color: var(--cyan); }

    .status-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 4px 10px;
      border-radius: 9999px;
      background: #1a202c;
      font-size: 12px;
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: #64748b; }
    .dot.running { background: var(--green); box-shadow: 0 0 8px var(--green); }

    /* Canvas Stage */
    #stage {
      flex: 1;
      position: relative;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #06070a;
      overflow: hidden;
      user-select: none;
    }
    #screen-wrap {
      position: relative;
      box-shadow: 0 20px 50px rgba(0,0,0,0.8), 0 0 0 1px var(--border);
      border-radius: 8px;
      overflow: hidden;
      background: #000;
      max-width: 95vw;
      max-height: 85vh;
      cursor: crosshair;
    }
    #vm-screen {
      display: block;
      width: 100%;
      height: 100%;
      object-fit: contain;
    }

    /* Coordinate Grid Overlay (Optional toggle) */
    #grid-overlay {
      position: absolute;
      top: 0; left: 0; right: 0; bottom: 0;
      pointer-events: none;
      display: none;
      background-size: 100px 100px;
      background-image:
        linear-gradient(to right, rgba(139, 92, 246, 0.1) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(139, 92, 246, 0.1) 1px, transparent 1px);
    }

    /* Collaborative Agent Cursor (Google Stitch Style) */
    #agent-cursor {
      position: absolute;
      top: 0; left: 0;
      pointer-events: none;
      opacity: 0;
      transition: transform 0.2s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.3s ease;
      z-index: 100;
      display: flex;
      align-items: flex-start;
    }
    #agent-cursor.visible {
      opacity: 1;
    }
    .cursor-pointer {
      width: 22px;
      height: 22px;
      filter: drop-shadow(0 2px 5px rgba(0,0,0,0.5));
    }
    .agent-pill {
      background: var(--accent);
      color: white;
      font-size: 11px;
      font-weight: 700;
      padding: 3px 8px;
      border-radius: 4px;
      white-space: nowrap;
      margin-left: 2px;
      margin-top: 12px;
      box-shadow: 0 4px 10px rgba(139, 92, 246, 0.4);
      display: flex;
      align-items: center;
      gap: 4px;
    }
    .click-ring {
      position: absolute;
      width: 40px;
      height: 40px;
      border-radius: 50%;
      border: 2px solid var(--accent);
      top: -10px; left: -10px;
      opacity: 0;
      pointer-events: none;
    }
    @keyframes ripple {
      0% { transform: scale(0.2); opacity: 1; }
      100% { transform: scale(1.6); opacity: 0; }
    }
    .click-ring.active {
      animation: ripple 0.4s ease-out;
    }

    /* Live Coordinate HUD */
    #coord-hud {
      position: absolute;
      bottom: 12px; right: 16px;
      background: rgba(19, 23, 34, 0.85);
      backdrop-filter: blur(8px);
      border: 1px solid var(--border);
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-family: monospace;
      color: var(--cyan);
      pointer-events: none;
    }

    /* Macro Drawer */
    #macro-drawer {
      position: absolute;
      bottom: 0; left: 0; right: 0;
      background: var(--panel);
      border-top: 1px solid var(--border);
      padding: 12px 20px;
      transform: translateY(100%);
      transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 60;
      display: flex;
      gap: 16px;
    }
    #macro-drawer.open { transform: translateY(0); }
    #macro-input {
      flex: 1;
      height: 70px;
      font-family: monospace;
      font-size: 12px;
      background: #0c0f17;
      color: #cbd5e1;
      padding: 8px;
      border: 1px solid var(--border);
      border-radius: 6px;
      resize: none;
    }

    /* Quick Keys Ribbon */
    .key-ribbon {
      display: flex;
      gap: 6px;
    }
  </style>
</head>
<body>

  <header>
    <div class="brand">
      <span>🔮 VDE-VLM Studio</span>
      <span class="brand-pill">Collaborative</span>
    </div>

    <div class="toolbar">
      <select id="vm-select"></select>
      <div class="status-badge">
        <div class="dot" id="vm-dot"></div>
        <span id="vm-state">checking...</span>
      </div>
      <button id="btn-start" class="primary">▶ Boot VM</button>
      <button id="btn-stop" class="danger">⏹ Power Off</button>
    </div>

    <!-- Quick Keys Ribbon -->
    <div class="key-ribbon">
      <button onclick="sendKey('up')" title="Up Arrow">▲ Up</button>
      <button onclick="sendKey('down')" title="Down Arrow">▼ Down</button>
      <button onclick="sendKey('space')" title="Space">␣ Space</button>
      <button onclick="sendKey('enter')" title="Enter">↵ Enter</button>
      <button onclick="sendKey('tab')" title="Tab">⇥ Tab</button>
      <button onclick="sendKey('esc')" title="Escape">Esc</button>
      <button onclick="sendKey('super')" title="Windows / Super Key">⊞ Super</button>
      <button onclick="sendKey('ctrl+alt+t')" title="Terminal shortcut">Terminal</button>
    </div>

    <div class="toolbar">
      <button id="btn-grid" onclick="toggleGrid()">📐 Grid</button>
      <button id="btn-demo" class="primary" onclick="triggerAgentDemo()">✨ Demo Agent Cursor</button>
      <button id="btn-macro-toggle" onclick="toggleMacroDrawer()">⚡ Compound Macro</button>
    </div>
  </header>

  <div id="stage">
    <div id="screen-wrap">
      <img id="vm-screen" src="/api/screen" alt="Live VM Display" tabindex="0">
      <div id="grid-overlay"></div>

      <!-- Stitch AI Cursor -->
      <div id="agent-cursor">
        <div class="click-ring" id="agent-ripple"></div>
        <svg class="cursor-pointer" viewBox="0 0 24 24" fill="none">
          <path d="M4 3L18 13L11.5 14L9 20L4 3Z" fill="#8b5cf6" stroke="#ffffff" stroke-width="1.5" stroke-linejoin="round"/>
        </svg>
        <div class="agent-pill" id="agent-label">🤖 Gemini</div>
      </div>
    </div>

    <div id="coord-hud">X: 0 | Y: 0</div>
  </div>

  <!-- Macro Drawer -->
  <div id="macro-drawer">
    <textarea id="macro-input" placeholder="Enter batch actions (one per line, e.g.):&#10;type:echo 'Hello from VDE-VLM'|enter&#10;wait:0.5&#10;click:450,720"></textarea>
    <div style="display:flex; flex-direction:column; gap:8px;">
      <button class="primary" onclick="runMacro()">▶ Run Batch</button>
      <button onclick="toggleMacroDrawer()">Close</button>
    </div>
  </div>

  <script>
    const vmScreen = document.getElementById("vm-screen");
    const screenWrap = document.getElementById("screen-wrap");
    const coordHud = document.getElementById("coord-hud");
    const agentCursor = document.getElementById("agent-cursor");
    const agentRipple = document.getElementById("agent-ripple");
    const agentLabel = document.getElementById("agent-label");
    const vmSelect = document.getElementById("vm-select");
    const vmDot = document.getElementById("vm-dot");
    const vmState = document.getElementById("vm-state");
    const gridOverlay = document.getElementById("grid-overlay");

    let currentVM = "";
    let isConnected = false;
    let ws = null;
    let cursorFadeTimer = null;

    // Load registered VMs
    async function refreshVMs() {
      try {
        const res = await fetch("/api/vms");
        const vms = await res.json();
        vmSelect.innerHTML = "";
        vms.forEach(vm => {
          const opt = document.createElement("option");
          opt.value = vm.name;
          opt.textContent = `${vm.name} (${vm.state})`;
          vmSelect.appendChild(opt);
        });
        if (vms.length > 0) {
          currentVM = vms[0].name;
          updateStatus(vms[0].state);
        }
      } catch (e) {
        console.error("Failed to load VMs", e);
      }
    }

    function updateStatus(state) {
      vmState.textContent = state;
      if (state.toLowerCase() === "running") {
        vmDot.className = "dot running";
      } else {
        vmDot.className = "dot";
      }
    }

    vmSelect.onchange = (e) => {
      currentVM = e.target.value;
      fetch(`/api/select_vm?name=${encodeURIComponent(currentVM)}`);
    };

    document.getElementById("btn-start").onclick = async () => {
      await fetch(`/api/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "start", vm: currentVM })
      });
      refreshVMs();
    };

    document.getElementById("btn-stop").onclick = async () => {
      await fetch(`/api/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "stop", vm: currentVM })
      });
      refreshVMs();
    };

    // Screen coordinate mapping
    function getVMPixelCoords(e) {
      const rect = vmScreen.getBoundingClientRect();
      const natW = vmScreen.naturalWidth > 0 ? vmScreen.naturalWidth : 1280;
      const natH = vmScreen.naturalHeight > 0 ? vmScreen.naturalHeight : 800;
      const scaleX = natW / rect.width;
      const scaleY = natH / rect.height;
      const x = Math.round((e.clientX - rect.left) * scaleX);
      const y = Math.round((e.clientY - rect.top) * scaleY);
      return { x: Math.max(0, x), y: Math.max(0, y), width: natW, height: natH };
    }

    vmScreen.onmousemove = (e) => {
      const { x, y } = getVMPixelCoords(e);
      coordHud.textContent = `X: ${x} | Y: ${y}`;
    };

    // User direct click
    vmScreen.onmousedown = async (e) => {
      const { x, y, width, height } = getVMPixelCoords(e);
      const btn = e.button === 2 ? "right" : (e.button === 1 ? "middle" : "left");
      await fetch("/api/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "click", vm: currentVM, x, y, button: btn, width, height })
      });
    };
    vmScreen.oncontextmenu = (e) => e.preventDefault();

    // Global keyboard listener for seamless real-time VM control
    window.addEventListener("keydown", async (e) => {
      // Don't intercept if user is typing inside the macro drawer textarea
      if (e.target && (e.target.tagName === "TEXTAREA" || e.target.tagName === "INPUT")) return;

      const key = e.key;
      const specialKeys = {
        "ArrowUp": "up",
        "ArrowDown": "down",
        "ArrowLeft": "left",
        "ArrowRight": "right",
        "Enter": "enter",
        "Escape": "esc",
        "Backspace": "backspace",
        "Tab": "tab",
        " ": "space",
        "Meta": "super",
        "F1": "f1", "F2": "f2", "F3": "f3", "F4": "f4", "F5": "f5", "F6": "f6",
        "F7": "f7", "F8": "f8", "F9": "f9", "F10": "f10", "F11": "f11", "F12": "f12",
      };

      if (specialKeys[key]) {
        e.preventDefault();
        await sendKey(specialKeys[key]);
      } else if (key.length === 1 && !e.ctrlKey && !e.altKey && !e.metaKey) {
        // Plain character typing
        e.preventDefault();
        await fetch("/api/action", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ type: "type", vm: currentVM, text: key })
        });
      }
    });

    async function sendKey(chord) {
      await fetch("/api/action", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type: "key", vm: currentVM, chord })
      });
    }

    async function triggerAgentDemo() {
      await fetch("/api/demo_agent", { method: "POST" });
    }

    function toggleGrid() {
      const isVisible = gridOverlay.style.display === "block";
      gridOverlay.style.display = isVisible ? "none" : "block";
      document.getElementById("btn-grid").classList.toggle("active", !isVisible);
    }

    function toggleMacroDrawer() {
      document.getElementById("macro-drawer").classList.toggle("open");
    }

    async function runMacro() {
      const text = document.getElementById("macro-input").value;
      const lines = text.split("\n").filter(l => l.trim().length > 0);
      await fetch("/api/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ vm: currentVM, steps: lines })
      });
      toggleMacroDrawer();
    }

    // Connect WebSocket for Live MJPEG / Cursor updates
    function connectWS() {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "agent_cursor") {
          // Render Google Stitch-style collaborative cursor
          const rect = vmScreen.getBoundingClientRect();
          const natW = vmScreen.naturalWidth > 0 ? vmScreen.naturalWidth : 1280;
          const natH = vmScreen.naturalHeight > 0 ? vmScreen.naturalHeight : 800;
          const scaleX = (rect.width > 0 ? rect.width : 1280) / natW;
          const scaleY = (rect.height > 0 ? rect.height : 800) / natH;

          const screenX = Math.round(data.x * scaleX);
          const screenY = Math.round(data.y * scaleY);

          agentCursor.style.transform = `translate3d(${screenX}px, ${screenY}px, 0)`;
          agentLabel.textContent = `🤖 ${data.label} (${data.x}, ${data.y})`;
          agentCursor.classList.add("visible");

          if (data.is_click) {
            agentRipple.classList.remove("active");
            void agentRipple.offsetWidth; // retrigger animation
            agentRipple.classList.add("active");
          }

          clearTimeout(cursorFadeTimer);
          cursorFadeTimer = setTimeout(() => {
            agentCursor.classList.remove("visible");
          }, 3500);
        } else if (data.type === "vm_state") {
          updateStatus(data.state);
        }
      };

      ws.onclose = () => {
        setTimeout(connectWS, 2000);
      };
    }

    // Poll live video frame stream smoothly without disk bloat
    function startLiveStream() {
      setInterval(() => {
        vmScreen.src = `/api/screen?t=${Date.now()}`;
      }, 400); // ~2.5 FPS periodic polling with zero disk shredding
    }

    refreshVMs();
    connectWS();
    startLiveStream();
  </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def get_index():
    return HTMLResponse(content=HTML_TEMPLATE)


@app.get("/api/vms")
async def get_vms():
    clean_temp_artifacts()
    vms = list_vms()
    res = []
    for m in vms:
        vm = VBoxVM(m["name"])
        res.append({"name": m["name"], "uuid": m["uuid"], "state": vm.state})
    return res


@app.get("/api/select_vm")
async def select_vm(name: str):
    global _current_vm_name
    _current_vm_name = name
    return {"selected": name}


@app.get("/api/screen")
async def get_screen(vm: Optional[str] = None):
    """Serve latest screen frame directly from rolling cache (zero disk shredding)."""
    target_vm = VBoxVM(vm or _current_vm_name)
    if not target_vm.is_running:
        # Generate placeholder image if VM is not running
        from PIL import Image
        img = Image.new("RGB", (720, 400), color=(15, 18, 25))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return Response(content=buf.getvalue(), media_type="image/jpeg")

    # Overwrite persistent rolling cache file in place
    screen_path = target_vm.screenshot(use_rolling_cache=True)
    with open(screen_path, "rb") as f:
        return Response(content=f.read(), media_type="image/png")


@app.post("/api/action")
async def execute_action(req: Request):
    data = await req.json()
    action_type = data.get("type")
    vm_name = data.get("vm") or _current_vm_name
    vm = VBoxVM(vm_name)

    if action_type == "start":
        from vde_vlm.session_manager import VBoxSessionManager
        VBoxSessionManager.get_instance().start_vm_interactive(vm_name, headless=True)
        return {"status": "started", "state": vm.state}

    elif action_type == "stop":
        vm.stop(mode="poweroff")
        return {"status": "stopped", "state": vm.state}

    elif action_type == "click":
        x = int(data["x"])
        y = int(data["y"])
        btn = data.get("button", "left")
        w = int(data.get("width", 1280))
        h = int(data.get("height", 800))
        double = bool(data.get("double", False))
        notify_agent_action(x, y, is_click=True, label="User")
        from vde_vlm.session_manager import VBoxSessionManager
        VBoxSessionManager.get_instance().mouse_click(vm_name, x, y, button=btn, width=w, height=h, double=double)
        vm.click(x, y, button=btn, double=double)
        return {"status": "clicked", "x": x, "y": y}

    elif action_type == "key":
        chord = data.get("chord", "enter")
        vm.press_key(chord)
        return {"status": "key_sent", "chord": chord}

    elif action_type == "type":
        text = data.get("text", "")
        enter = bool(data.get("enter", False))
        vm.type(text, press_enter=enter)
        return {"status": "typed", "text": text}

    raise HTTPException(status_code=400, detail=f"Unknown action: {action_type}")


@app.post("/api/demo_agent")
async def trigger_agent_demo():
    """Simulate a live demonstration of Gemini agent movements and clicks."""
    async def _tour():
        path = [
            (250, 120, "Inspecting Header", False),
            (360, 200, "Targeting GRUB Menu", True),
            (360, 230, "Selecting Safe Mode", True),
            (180, 320, "Reading Instructions", False),
            (500, 200, "Confirming Coordinates", True),
        ]
        for x, y, label, is_click in path:
            notify_agent_action(x, y, is_click=is_click, label=f"Gemini: {label}")
            await asyncio.sleep(1.2)

    asyncio.create_task(_tour())
    return {"status": "demo_started"}


@app.post("/api/batch")
async def execute_batch_action(req: Request):
    """Execute compound batch macro plan."""
    data = await req.json()
    vm_name = data.get("vm") or _current_vm_name
    steps = data.get("steps", [])
    vm = VBoxVM(vm_name)

    res = execute_batch(vm, steps)
    return res


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _active_sockets.add(websocket)
    # Send initial agent cursor
    await websocket.send_json({"type": "agent_cursor", **_agent_cursor_state})
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming ping / messages if needed
    except WebSocketDisconnect:
        _active_sockets.discard(websocket)


def run_web_viewer(host: str = "0.0.0.0", port: int = 7891):
    """Run the collaborative web studio on the specified port (default 7891)."""
    logger.info(f"Starting VDE-VLM Studio at http://localhost:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    port = int(os.environ.get("VDE_PORT", "7891"))
    run_web_viewer(port=port)
