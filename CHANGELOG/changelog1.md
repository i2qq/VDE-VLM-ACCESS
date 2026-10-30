# Changelog 1 - Initial Implementation of VDE-VLM-ACCESS

### Summary
Comprehensive VirtualBox interaction and multimodal vision toolkit allowing Vision-Language Models (VLMs) and AI agents (Gemini, Antigravity, Claude, local models) to inspect, interact with, and test desktop environments (such as VDE) running inside VirtualBox virtual machines.

### Highlights & Modifications
1. **Low-level Engine & VBoxManage Integration (`vde_vlm/vbox.py`)**:
   - Automated cross-platform discovery of `VBoxManage` executable across Windows, Linux, and macOS.
   - Command runner with timeouts, exit code verification, and structured exception handling.
   - Querying all registered VMs, active running VMs, and machine properties.
2. **Vision & Perception Layer (`vde_vlm/vision.py`)**:
   - Virtual machine display screenshot capture to PNG.
   - Dynamic coordinate grid overlay generator (`add_coordinate_grid`) stamping pixel coordinate rulers and labels (every 100px) directly onto screenshots for pinpoint VLM targeting.
   - Perceptual diffing engine (`compare_screenshots`) measuring visual change ratios to verify UI responses.
   - Screen state analysis (resolution, average brightness, black screen detection).
3. **Hardware Input Layer (`vde_vlm/keyboard.py`, `vde_vlm/mouse.py`)**:
   - Complete PS/2 Set 1 scancode table with accurate make/break sequences for alphanumeric keys, special keys, arrows, function keys, and modifiers.
   - Chord parsing (`parse_key_combo`) supporting combos like `ctrl+alt+t`, `super`, `alt+f4`.
   - String typing helper (`type_string`) via `keyboardputstring`.
   - Absolute coordinate mouse positioning, left/right/middle clicking, double clicks, and scrolling via VirtualBox COM and guest fallback.
4. **Guest OS Control & Transfer (`vde_vlm/guest.py`)**:
   - In-guest shell command execution (`run_guest_command`) with stdout/stderr capture.
   - Bidirectional file copy between host and guest (`copy_to_guest`, `copy_from_guest`).
5. **Snapshot Safety Checkpoints (`vde_vlm/snapshots.py`)**:
   - Snapshot creation, restoration, listing, and deletion.
   - `safe_checkpoint` context manager providing automated rollback on test failures.
6. **Unified Core & Agent Loop (`vde_vlm/core.py`, `vde_vlm/agent.py`)**:
   - High-level `VBoxVM` class encapsulating lifecycle, vision, input, guest control, and snapshots.
   - Structured agent `execute_agent_step` perception-action loop.
7. **CLI, MCP Server, & Skill**:
   - Full command-line tool `vde-vlm` supporting `list`, `start`, `stop`, `observe`, `screenshot`, `click`, `type`, `key`, `exec`, `upload`, `download`, `snapshot`, `serve`.
   - MCP (Model Context Protocol) JSON-RPC tool server (`vde_vlm/server.py`).
   - Antigravity agent skill definition (`skills/vde-vlm/SKILL.md`).
8. **Test Suite & Examples**:
   - 10 automated unit tests (`tests/test_vde_vlm.py`) covering scancode parsing, discovery, overlays, and diffing.
   - End-to-end example scripts (`basic_control.py`, `vision_loop.py`, `deploy_and_test_vde.py`).
