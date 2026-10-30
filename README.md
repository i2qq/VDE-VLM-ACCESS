# VDE-VLM-ACCESS

> **Empowering Vision-Language Models (Gemini, Claude, Antigravity, local VLMs) with direct eyes, hands, and control over VirtualBox Virtual Machines.**

This repository enables autonomous coding agents and VLMs working on the [Victors Desktop Environment (VDE)](https://github.com/i2qq/VDE) project to boot, observe, interact with, test, and debug Linux desktop environments inside Oracle VirtualBox.

---

## 🌟 Key Capabilities

- 👁️ **Multimodal VLM Vision**: Capture high-resolution screenshots directly into agent context (`observe`, `screenshot`).
- 📐 **Coordinate Grid Overlays**: Automatically generates overlay images marked with coordinate rulers (every 100px) so VLMs can target buttons and windows with pixel-level precision.
- ⌨️ **Precise Hardware Keyboard Injection**: Maps key combinations (`Ctrl+Alt+T`, `Super` / Win key, `Enter`, `Alt+F4`, `Esc`) into exact PS/2 Set 1 make/break scancodes, as well as text typing.
- 🖱️ **Absolute Mouse Control**: Position, left/right/middle click, double click, drag, and scroll via VirtualBox COM and guest fallback.
- 🛡️ **Safety Checkpoint Snapshots**: Create instant snapshots before testing experimental code and roll back in seconds if a build breaks the desktop.
- 🔄 **Perceptual Diffing**: Measures before/after visual difference (`diff_ratio`) to confirm if UI elements opened, focused, or closed.
- 📦 **Guest Execution & File Sync**: Run bash commands inside the guest (`guestcontrol run`) and synchronize files between host and VM.
- 🔌 **Model Context Protocol (MCP)**: Native MCP tool server (`vde_vlm.server`) for standard agent integration.
- 🧠 **Antigravity Skill**: Pre-packaged `skills/vde-vlm/SKILL.md` ready for immediate agent discovery.

---

## 🏗️ Architecture

```
                                  +------------------------------+
                                  |   AI Agent / VLM (Gemini)    |
                                  +--------------+---------------+
                                                 |
                   +-----------------------------+-----------------------------+
                   |                                                           |
          [ CLI / Terminal ]                                           [ MCP Tool Server ]
         vde-vlm observe / click                                        tools/call: vm_*
                   |                                                           |
                   +-----------------------------+-----------------------------+
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
|  PIL Overlays   |     | Scancodes & COM |                     | Shell Execution |
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

### 1. Installation

```bash
git clone https://github.com/i2qq/VDE-VLM-ACCESS.git
cd VDE-VLM-ACCESS
pip install -e .
```

### 2. Discover VMs

```bash
vde-vlm list
```

Output:
```
VM Name                        State           UUID
---------------------------------------------------------------------------
vmvdebox5                      poweroff        151e457b-2be6-4a1e-8c9d-21a6d4b18a65
vmvdebox6.1                    poweroff        bd692e80-baae-4d36-9653-e94684f8b1d4
```

### 3. Boot & Observe Headless

```bash
# Power on headless
vde-vlm start "vmvdebox6.1"

# Observe with coordinate grid overlay
vde-vlm observe "vmvdebox6.1"
```

The output gives you the exact file path to both the raw screenshot and the grid overlay (`screenshot_grid.png`). Load this image into your agent's vision tool (`read_file`) to inspect the desktop!

---

## 💻 CLI Command Reference

| Command | Description | Example |
|---|---|---|
| `vde-vlm list` | List all registered VMs and states | `vde-vlm list` |
| `vde-vlm start <vm> [--gui]` | Boot VM (default: headless) | `vde-vlm start "vmvdebox6.1"` |
| `vde-vlm stop <vm> [--mode poweroff\|savestate\|acpi]` | Stop VM | `vde-vlm stop "vmvdebox6.1"` |
| `vde-vlm observe <vm> [--ocr]` | Full observation (screen + grid + metrics) | `vde-vlm observe "vmvdebox6.1"` |
| `vde-vlm screenshot <vm> [--grid]` | Save screenshot PNG | `vde-vlm screenshot "vmvdebox6.1" -o screen.png --grid` |
| `vde-vlm click <vm> <x> <y> [--button left\|right] [--verify]` | Click pixel coordinate | `vde-vlm click "vmvdebox6.1" 450 720 --verify` |
| `vde-vlm type <vm> "<text>" [--enter]` | Type text into active window | `vde-vlm type "vmvdebox6.1" "ls -la" --enter` |
| `vde-vlm key <vm> "<chord>"` | Send key combination | `vde-vlm key "vmvdebox6.1" "ctrl+alt+t"` |
| `vde-vlm exec <vm> "<cmd>"` | Execute command inside guest | `vde-vlm exec "vmvdebox6.1" "whoami"` |
| `vde-vlm upload <vm> <host> <guest>` | Copy files into guest | `vde-vlm upload "vmvdebox6.1" ./build /home/victor/build` |
| `vde-vlm download <vm> <guest> <host>` | Copy files from guest | `vde-vlm download "vmvdebox6.1" /var/log/vde.log ./logs` |
| `vde-vlm snapshot <vm> take <name>` | Create safety snapshot | `vde-vlm snapshot "vmvdebox6.1" take "baseline"` |
| `vde-vlm snapshot <vm> restore <name>` | Roll back to snapshot | `vde-vlm snapshot "vmvdebox6.1" restore "baseline"` |
| `vde-vlm serve` | Launch MCP JSON-RPC server | `vde-vlm serve` |

---

## 🐍 Python API Reference

```python
from vde_vlm import VBoxVM

vm = VBoxVM("vmvdebox6.1")

# Boot headless
vm.start(headless=True)

# Create safety checkpoint
with vm.checkpoint("test_vde_desktop"):
    # Observe screen with coordinate grid
    obs = vm.observe(grid=True)
    print("Screenshot:", obs["screenshot"])
    print("Grid Image:", obs["grid_screenshot"])

    # Press Super key to open VDE start menu
    vm.press_key("super")

    # Verify visual change
    click_res = vm.click(x=120, y=950, verify_change=True)
    print("Clicked element, visual change:", click_res["diff_ratio"])

# Stops VM safely
vm.stop()
```

---

## 🎯 Testing

Run the included test suite:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

All 10 tests verify key scancode parsing, VirtualBox executable discovery, VM enumeration, grid overlays, image metrics, and difference calculations.

---

## 📜 License

MIT License. Developed for the VDE ecosystem.
