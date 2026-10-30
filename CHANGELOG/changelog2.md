# Changelog 2 - Collaborative Studio (Port 7891), Zero Disk Shredding & Compound Macro System

### Summary
Introduced a Google Stitch-style collaborative live web studio on port 7891 with live presence cursors, eliminated disk-shredding temporary PNGs in favor of persistent rolling buffers and in-memory streams, and added a compound batch action / macro engine for atomic multi-step interactions.

### Highlights & Modifications
1. **Google Stitch-Style Collaborative Live Studio (`vde_vlm/web_viewer.py`)**:
   - Built a real-time web studio running on port 7891 (`http://localhost:7891`).
   - Implemented real-time **agent presence**: when Gemini or an AI agent clicks or moves, a glowing `🤖 Gemini (x, y)` cursor badge with pointer and ripple animations animates across the user's screen.
   - Real-time user interaction: user can click anywhere on the canvas or type on their physical keyboard to send inputs directly to the VM.
   - Quick action toolbar: `[⊞ Super]`, `[Terminal]`, `[↵ Enter]`, `[⇥ Tab]`, `[Esc]`, plus live cursor coordinate HUD `(X, Y)`.
   - Batch macro runner drawer embedded directly in the web UI.
2. **Zero Disk Shredding & Rolling Memory Buffers (`vde_vlm/vision.py`)**:
   - Replaced ad-hoc `tempfile.mkstemp()` captures with persistent rolling image buffers (`live_<vm>.png`) that overwrite in place.
   - Added automatic temp file cleaner (`clean_temp_artifacts`, `vde-vlm clean`).
   - Re-designed coordinate overlay into a sleek, non-intrusive Stitch-style subtle border ruler that does not slice through or obscure fonts and text.
   - Added agent cursor drawer (`draw_agent_cursor`) for annotated snapshots.
3. **Compound Batch Actions & Macros (`vde_vlm/macro.py`)**:
   - Created `execute_batch` and shorthand macro parser allowing multi-step interaction plans to run in a single atomic turn (e.g. `type:hello|enter`, `wait:0.5`, `click:450,720`).
   - Added `vm.batch()` and `vm.macro()` to high-level `VBoxVM` class.
   - Added `vde-vlm macro` and `vde-vlm batch` CLI commands.
   - Added `vm_batch` to MCP server (`vde_vlm/server.py`).
4. **Antigravity Skill & Unit Tests**:
   - Expanded unit tests in `tests/test_vde_vlm.py` from 10 to 16 tests covering macros, cleanups, cursors, and overlays.
   - Updated skill at `skills/vde-vlm/SKILL.md` and installed into `~/.gemini/config/skills/vde-vlm/SKILL.md`.
