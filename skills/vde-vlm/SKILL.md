---
name: vde-vlm
description: Enables Vision-Language Models (VLMs) and AI coding agents to control, observe, and collaboratively interact with Oracle VirtualBox VMs running VDE (or Linux desktops). Use this skill when you need to boot a VM, view its screen with multimodal vision, click UI buttons, type text, send key combos, execute compound batch actions, launch the collaborative live web studio (Port 7891), or roll back snapshots.
---

# VDE-VLM VirtualBox Agent Controller & Collaborative Studio

This skill gives you (Gemini, Antigravity, Claude, or any VLM agent) and the user direct collaborative perception and control over Oracle VirtualBox Virtual Machines.

---

## 1. Quick Reference Commands

All commands can be invoked using `run_command` in PowerShell or bash:

```powershell
# 1. Discover VMs and their states
python -m vde_vlm list

# 2. Boot a VM in headless mode (no host window clutter)
python -m vde_vlm start "vmvdebox6.1"

# 3. Launch the Google Stitch-style collaborative live web studio (Port 7891)
# User and agent can interact simultaneously with live presence & cursors
python -m vde_vlm live --port 7891

# 4. Multimodal observation with rolling cache (zero disk bloat)
python -m vde_vlm observe "vmvdebox6.1"

# 5. Compound Batch Actions (Atomic multi-step execution in one turn!)
python -m vde_vlm macro "vmvdebox6.1" "type:echo 'hello world'|enter" "wait:0.5" "click:450,720"

# 6. Click an element seen on screen (broadcasts agent cursor to live studio)
python -m vde_vlm click "vmvdebox6.1" 450 720 --verify

# 7. Press hotkeys or special chords
python -m vde_vlm key "vmvdebox6.1" "super"
python -m vde_vlm key "vmvdebox6.1" "ctrl+alt+t"
python -m vde_vlm key "vmvdebox6.1" "enter"
python -m vde_vlm key "vmvdebox6.1" "esc"

# 8. Clean up stale temporary files from disk
python -m vde_vlm clean

# 9. Stop the VM when finished
python -m vde_vlm stop "vmvdebox6.1" --mode poweroff
```

---

## 2. Google Stitch-Style Collaborative Studio (Port 7891)

When running `python -m vde_vlm live --port 7891`:
- Open **http://localhost:7891** in your browser.
- **Collaborative Presence**:
  - Shows the VM screen unfolding live without saving thousands of PNGs to disk.
  - When Gemini clicks or moves, an animated `🤖 Gemini` cursor badge with a glowing ripple indicator shows the user exactly what the agent is doing in real-time.
  - The user can click anywhere or type on their physical keyboard to interact with the VM collaboratively with the agent.
  - Quick action buttons: `[⊞ Super]`, `[Terminal]`, `[↵ Enter]`, `[⇥ Tab]`, `[Esc]`.
  - Live coordinate HUD at the bottom right (`X: ... | Y: ...`) displays the exact pixel coordinates under your mouse without needing an intrusive grid.

---

## 3. Compound Batch Interaction Patterns

Instead of sending one keypress or click at a time, execute an entire action sequence in one shot:

### Shorthand Macro Syntax:
- `type:<text>|enter`: Types text and presses Enter.
- `click:<x>,<y>`: Left-clicks at `(x, y)`.
- `rclick:<x>,<y>`: Right-clicks.
- `dclick:<x>,<y>`: Double-clicks.
- `key:<chord>`: Presses key combo (`super`, `ctrl+alt+t`, `esc`, `enter`).
- `wait:<seconds>`: Pauses execution (e.g. `wait:1.0`).
- `exec:<command>`: Runs bash command inside guest.

```python
from vde_vlm import VBoxVM

vm = VBoxVM("vmvdebox6.1")

# Compound plan in a single call
result = vm.macro(
    "type:google-chrome|enter",
    "wait:1.5",
    "click:500,350",
    "type:https://github.com/i2qq/VDE|enter"
)
```
