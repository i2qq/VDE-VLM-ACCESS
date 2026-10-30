# Changelog 7 - Native Hardware Mouse Support & Dynamic Agent Cursor Auto-Fade

### Summary
Resolved hardware mouse input routing through persistent in-process session acquisition and added smooth auto-fade visibility to the collaborative agent cursor so it never blocks static menus or screen text.

### Highlights & Modifications
1. **Direct In-Process Mouse Hardware Routing (`vde_vlm/core.py`, `vde_vlm/session_manager.py`)**:
   - `vm.start()` now boots through `start_vm_interactive`, keeping the VirtualBox `ISession` open in memory.
   - Connected `mouse_click` directly to `session.Console.Mouse.PutMouseEventAbsolute` using exact guest resolution normalization (1280x800).
2. **Auto-Fading Collaborative Agent Cursor (`vde_vlm/web_viewer.py`)**:
   - Cursor starts completely invisible (`opacity: 0`) and automatically animates in with glowing ripples only during active agent movements or clicks.
   - Auto-fades after 3.5 seconds of inactivity so it never obscures GRUB, text, or menus.
