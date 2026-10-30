# Changelog 8 - Visual Grounding, SoM UI Detection, Precise Mouse Coordinates & Cursor Separation

## Summary
- **Visual Grounding & UI Element Recognition (`vde_vlm/grounding.py`)**:
  - Built-in High-Accuracy OCR & Visual Feature Model (VFM) with Set-of-Marks (SoM) style bounding boxes and centroid coordinates.
  - Saliency and contour segmentation to locate buttons, text inputs, and widgets.
  - Fuzzy and exact text matching with `find_element_by_text`.
  - Annotated SoM overlay generator (`draw_grounded_overlay`) for visual inspection.
- **Hardware Mouse Coordinate Fix (`vde_vlm/mouse.py` & `session_manager.py`)**:
  - Replaced incorrect `0xFFFF` coordinate scaling with VirtualBox's native 1-based guest display pixel coordinates `[1..width], [1..height]`.
  - Added shared COM console fallback directly in `session_manager.py` so mouse injection works seamlessly even on externally started VMs.
  - Added scroll wheel handling and aspect-ratio letterbox compensation in `web_viewer.py`.
- **Cursor & Focus Indicator Separation (`vde_vlm/web_viewer.py`)**:
  - Separated agent cursor from user focus marker:
    - 🟣 `🤖 Gemini`: strictly animates and ripples for agent actions.
    - 🔵 `🎯 User Focus`: cyan ripple and `🎯 Focus: (x, y)` badge appears when the user taps to guide attention without morphing or moving the agent's cursor.
  - Added interactive header toggle: `[🎯 Grounding / SoM]` to stream real-time bounding boxes and labels.
  - Added `/api/grounding` and `/api/grounded_screen` endpoints.
- **New CLI Subcommands & MCP Tools**:
  - CLI: `vde-vlm detect <vm>`, `vde-vlm find <vm> <text>`, `vde-vlm click-text <vm> <text>`.
  - MCP Tools: `vm_detect`, `vm_find`, `vm_click_text`.
  - High-level Python methods on `VBoxVM`: `vm.detect_elements()`, `vm.find_element(query)`, `vm.click_element(query)`, `vm.observe_grounded()`.
