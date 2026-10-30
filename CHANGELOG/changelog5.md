# Changelog 5 - Agent Cursor Showcase & Default VM Selection

### Summary
Enhanced the collaborative live studio with an interactive agent cursor demonstration mode and dynamic fallback VM detection for `vmvdebox7`.

### Highlights & Modifications
1. **Interactive Agent Cursor Showcase (`vde_vlm/web_viewer.py`)**:
   - Added `POST /api/demo_agent` triggering automated multi-point cursor navigation and click animations.
   - Added interactive `[✨ Demo Agent Cursor]` button on the web studio header.
   - Hardened cursor coordinate scaling for early frame loading states.
2. **Default VM Selection**:
   - Configured `vmvdebox7` as default VM with dynamic fallback to available machines.
