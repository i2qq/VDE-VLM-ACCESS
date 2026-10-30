# Changelog 10 - VLM Token Efficiency Suite (Text-First Grounding & Low-Token Thumbnails)

## Summary
- **Text-First UI Grounding (`mode="text"`, DEFAULT)**:
  - Local EasyOCR and edge saliency run entirely on the host machine with zero Gemini vision token costs.
  - `vm.observe(mode="text")` returns a lightweight structured JSON list of detected UI elements with bounding boxes and centroid coordinates.
  - Consumes only ~50–100 prompt tokens per observation instead of 2,000+ multimodal vision tokens, delivering a **95%+ reduction in weekly API quota consumption**.
- **Compact Low-Tier Vision Mode (`mode="compact"`)**:
  - Implemented `create_compact_thumbnail()` in `vde_vlm/vision.py` which scales screenshots to $\le$ 512px with JPEG compression.
  - Aligns with Gemini's lowest vision billing tier (~258 tokens vs ~2,000+ for raw 1280x800 PNGs).
- **Region of Interest (ROI) Cropping (`crop_region`)**:
  - Added ability to crop specific bounding boxes `[x1, y1, x2, y2]`, allowing agents to inspect localized dialogs without transmitting full frames.
- **Smart Diff Suppression (`skip_if_unchanged=True`)**:
  - Detects if the screen changed compared to the last turn using normalized pixel difference; if `< 0.5%`, suppresses redundant image re-transmission.
- **MCP Server & CLI Integration**:
  - Updated `vm_observe` MCP tool schema and dispatch to default to `mode="text"`.
  - Added `-m/--mode [text|compact|full]` and `--crop X1 Y1 X2 Y2` flags to `vde-vlm observe`.
