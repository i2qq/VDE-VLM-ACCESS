---
description: Seamlessly test, observe, and interact with the Victorious Desktop Environment (VDE) running inside VirtualBox VMs using the vde-vlm tool suite and collaborative live studio.
trigger: always_on
---

# Victorious Desktop Environment (VDE) VirtualBox Testing & VLM Interaction Rule

Whenever working in, developing, or testing the **Victorious Desktop Environment (VDE)**:

1. **VirtualBox VM Testing Environment**:
   - VDE can be deployed, tested, and observed live inside VirtualBox virtual machines (e.g. `vmvdebox7`, `vmvdebox6.1`, `vmvdebox5`) without requiring manual user setup.
   - You can boot, observe, interact with, and power off VMs completely autonomously.
   - Check available VMs anytime using:
     ```bash
     vde-vlm list
     ```

2. **Universal CLI & MCP Tools**:
   - `vde-vlm` is globally accessible from any directory in PowerShell (`pwsh`), Command Prompt (`cmd.exe`), and POSIX shells (`sh`, `bash`).
   - The MCP server `vde-vlm` is plugged in with tools:
     - `vm_list`: List registered VMs and running states.
     - `vm_start`: Power on VM (headless or GUI).
     - `vm_stop`: Power off or save state (`poweroff`, `savestate`).
     - `vm_observe`: Capture screen + subtle coordinate grid overlay + metrics with zero disk bloat.
     - `vm_click`: Click pixel coordinates `(x, y)` and broadcast collaborative agent presence.
     - `vm_type`: Type text strings with optional Enter.
     - `vm_key`: Send hardware scancode chords (e.g. `super`, `ctrl+alt+t`, `alt+f4`, `esc`, `enter`).
     - `vm_batch`: Execute compound multi-action macro plans in a single atomic turn.
     - `vm_exec`: Run shell commands inside guest VM via `guestcontrol`.
     - `vm_snapshot` / `vm_restore`: Checkpoint management.
     - `vm_clean`: Purge temporary screenshot files.

3. **Google Stitch-Style Collaborative Live Studio (Port 7891)**:
   - When running interactive tests with the user, launch the live web studio:
     ```bash
     vde-vlm live --port 7891
     ```
   - The user and agent can view the VM screen unfolding live at **http://localhost:7891**.
   - Features real-time **agent presence**: when the agent moves or clicks, a glowing `🤖 Gemini (x, y)` cursor badge with pointer and click ripple indicator animates across the user's canvas.
   - The user can also click or type directly into the VM from the browser canvas.

4. **Safety Checkpoints on Code Deployments**:
   - ALWAYS take a safety snapshot before testing experimental installer changes, systemd configurations, or compositor builds:
     ```bash
     vde-vlm snapshot <vm> take "pre-test"
     ```
   - If a build fails or breaks the session, immediately restore the clean checkpoint:
     ```bash
     vde-vlm snapshot <vm> restore "pre-test"
     ```

5. **Compound Batch Actions (Avoid Single-Movement Roundtrips)**:
   - Rather than single-key turn roundtrips (`press h`, `press e`, `press l`...), execute compound action sequences in one atomic turn:
     ```bash
     vde-vlm macro <vm> "type:google-chrome|enter" "wait:1.0" "click:500,350"
     ```
   - In Python:
     ```python
     from vde_vlm import VBoxVM
     vm = VBoxVM("vmvdebox7")
     vm.macro("type:echo 'Testing VDE'|enter", "wait:0.5", "click:450,720")
     ```

6. **Storage Hygiene (Zero Disk Shredding)**:
   - Screen observations overwrite a persistent rolling buffer (`~/.vde_vlm/cache/live_<vm>.png`) instead of creating thousands of new PNG files.
   - Use `vde-vlm clean` to purge any legacy temporary screenshots.
