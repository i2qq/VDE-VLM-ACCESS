# Changelog 6 - Full Web Studio Interactivity & Persistent COM Session Control

### Summary
Revamped web interface interactivity with global keyboard listeners, directional D-Pad/ribbon controls, and in-process VirtualBox Session Manager for low-latency hardware mouse and keyboard injection.

### Highlights & Modifications
1. **Persistent COM Session Management (`vde_vlm/session_manager.py`)**:
   - Created `VBoxSessionManager` enabling direct, in-process access to `ISession.Console.Mouse` and `ISession.Console.Keyboard`.
   - Scaled mouse click coordinates to exact guest resolution (1280x800).
2. **Global Interactive Web Keyboard (`vde_vlm/web_viewer.py`)**:
   - Replaced canvas-only listener with page-wide `keydown` listener that maps `ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`, `Enter`, `Escape`, `Backspace`, `Tab`, `Space`, and direct character typing straight to the VM.
3. **On-Screen Navigation Controls**:
   - Added immediate clickable ribbon buttons for `▲ Up`, `▼ Down`, `␣ Space`, `↵ Enter`, `⇥ Tab`, `Esc`, `⊞ Super`, and `Terminal`.
