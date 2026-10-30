# VDE-VLM-ACCESS

> **Empowering Vision-Language Models (Gemini, Claude, Antigravity, local VLMs) with direct eyes, hands, collaborative presence, and control over VirtualBox Virtual Machines.**

This repository enables autonomous coding agents and human developers working on the [Victorious Desktop Environment (VDE)](https://github.com/i2qq/VDE) project to boot, observe, collaboratively interact with, test, and debug Linux desktop environments inside Oracle VirtualBox.

---

## 🌟 Key Capabilities

- 🔮 **Google Stitch-Style Collaborative Studio (`vde-vlm live --port 7891`)**:
  - Open `http://localhost:7891` to see the live VM screen unfolding in real-time.
  - Features real-time **agent presence**: when Gemini acts or clicks, a glowing cursor pointer with a `🤖 Gemini (x, y)` badge and click ripple indicator animates across the user's screen.
  - The user can click anywhere on the canvas or type on their physical keyboard to interact with the VM collaboratively with the agent.
- 🍃 **Zero Disk Bloat / Rolling Buffer**:
  - Screen streams and observations overwrite a persistent rolling buffer instead of shredding host storage with thousands of temporary PNGs. Includes `vde-vlm clean` for instant artifact cleanup.
- ⚡ **Compound Batch Actions & Macros (`vde-vlm macro`)**:
  - Execute multi-step sequences in a single atomic turn (e.g. `type:hello|enter`, `wait:0.5`, `click:450,720`) rather than slow single-key round-trips.
- 📐 **Subtle Non-Intrusive Vision Overlays**:
  - Modern, subtle border rulers and corner intersection badges that do not slice through or obscure text.
- ⌨️ **Precise Hardware Keyboard Injection**:
  - Maps key combinations (`Ctrl+Alt+T`, `Super` / Win key, `Enter`, `Alt+F4`, `Esc`) into exact PS/2 Set 1 make/break scancodes, plus text typing.
- 🖱️ **Absolute Mouse Control**:
  - Position, left/right/middle click, double-click, drag, and scroll via VirtualBox COM and guest fallback.
- 🛡️ **Safety Checkpoint Snapshots**:
  - Create instant snapshots before testing experimental code and roll back in seconds if a build breaks the desktop.
- 🔌 **Model Context Protocol (MCP)**:
  - Native MCP tool server (`vde_vlm.server`) for standard agent integration.
- 🧠 **Antigravity Skill**:
  - Pre-packaged `skills/vde-vlm/SKILL.md` ready for immediate agent discovery.

---

## 🏗️ Architecture

```
                                  +------------------------------+
                                  |   AI Agent / VLM (Gemini)    |
                                  +--------------+---------------+
                                                 |
         +---------------------------------------+---------------------------------------+
         |                                       |                                       |
[ Collaborative Studio ]                [ CLI / Terminal ]                       [ MCP Tool Server ]
http://localhost:7891                   vde-vlm macro / click                    tools/call: vm_batch
(Live Stream & Stitch Cursors)                   |                                       |
         |                                       |                                       |
         +---------------------------------------+---------------------------------------+
                                                 |
                                     +-----------v-----------+
                                     |   vde_vlm Python API  |
                                     |   (VBoxVM Controller) |
                                     +-----------+-----------+
                                                 |
         +-----------------------+---------------+-----------------------+
         |                       |                                       |
+--------v--------+     +--------v--------+                     +--------v--------+
|  Vision & Grid  |     | Keyboard/Mouse  |                     |  Guest Control  |
| Rolling Buffers |     | Scancodes & COM |                     | Shell Execution |
+--------+--------+     +--------+--------+                     +--------+--------+
         |                       |                                       |
         +-----------------------+---------------+-----------------------+
                                                 |
                                     +-----------v-----------+
                                     |   Oracle VirtualBox   |
                                     | (VBoxManage.exe / COM)|
                                     +-----------+-----------+
                                                 |
                                     +-----------v-----------+
                                     |  Linux Guest VM (VDE) |
                                     +-----------------------+
```

---

## 🚀 Quickstart

### 1. Installation & Global PATH Setup

```bash
git clone https://github.com/i2qq/VDE-VLM-ACCESS.git
cd VDE-VLM-ACCESS
pip install -e .

# Optional helper to install universal shims into ~/.local/bin:
powershell -ExecutionPolicy Bypass -File ./scripts/install-path.ps1  # On Windows
# ./scripts/install-path.sh                                          # On Linux/macOS
```

Once installed, `vde-vlm` works globally from **any working directory** in:
- **PowerShell (`pwsh` / `powershell`)**
- **Command Prompt (`cmd.exe`)**
- **Bash / Sh (`Git Bash`, `WSL`, `MSYS2`, `w64devkit`)**

### 2. Discover VMs (From any directory)

```bash
vde-vlm list
```

### 3. Launch the Collaborative Studio (Port 7891)

```bash
vde-vlm live --port 7891
```

Open **http://localhost:7891** in your browser. Both you and Gemini can see and control the VM simultaneously!

---

## 💻 CLI Command Reference

| Command | Description | Example |
|---|---|---|
| `vde-vlm list` | List all registered VMs and states | `vde-vlm list` |
| `vde-vlm live [--port 7891]` | Launch collaborative live web studio | `vde-vlm live --port 7891` |
| `vde-vlm start <vm> [--gui]` | Boot VM (default: headless) | `vde-vlm start "vmvdebox6.1"` |
| `vde-vlm stop <vm>` | Stop VM | `vde-vlm stop "vmvdebox6.1"` |
| `vde-vlm macro <vm> <steps...>` | Execute compound batch sequence | `vde-vlm macro "vmvdebox6.1" "type:echo hi\|enter" "wait:0.5" "click:450,720"` |
| `vde-vlm observe <vm>` | Multimodal observation (rolling buffer) | `vde-vlm observe "vmvdebox6.1"` |
| `vde-vlm click <vm> <x> <y>` | Click pixel coordinate | `vde-vlm click "vmvdebox6.1" 450 720 --verify` |
| `vde-vlm type <vm> "<text>" [--enter]` | Type text into active window | `vde-vlm type "vmvdebox6.1" "ls -la" --enter` |
| `vde-vlm key <vm> "<chord>"` | Send key combination | `vde-vlm key "vmvdebox6.1" "ctrl+alt+t"` |
| `vde-vlm snapshot <vm> take <name>` | Create safety snapshot | `vde-vlm snapshot "vmvdebox6.1" take "baseline"` |
| `vde-vlm snapshot <vm> restore <name>` | Roll back to snapshot | `vde-vlm snapshot "vmvdebox6.1" restore "baseline"` |
| `vde-vlm clean` | Clean stale temporary screenshots | `vde-vlm clean` |
| `vde-vlm serve` | Launch MCP JSON-RPC server | `vde-vlm serve` |

---

## 🐍 Python API Reference

```python
from vde_vlm import VBoxVM

vm = VBoxVM("vmvdebox6.1")
vm.start(headless=True)

# Compound batch interaction in one atomic turn
result = vm.macro(
    "type:google-chrome|enter",
    "wait:1.5",
    "click:500,350",
    "type:https://github.com/i2qq/VDE|enter"
)

# Observe screen without creating new temp files
obs = vm.observe(grid=True)
print("Screen:", obs["screenshot"])

vm.stop()
```

---

## 📜 License

MIT License. Developed for the VDE ecosystem.
