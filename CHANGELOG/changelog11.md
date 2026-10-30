# Changelog 11 - Transparent Background SoM Spatial Maps, Isolated Clean User Stream & Multi-Tier Observation Modes

## Summary
- **Transparent Background SoM Spatial Wireframe (`mode="map"`)**:
  - Enhanced `draw_grounded_overlay()` in `vde_vlm/grounding.py` with `transparent_bg=True` and `max_dim=512`.
  - Generates a Set-of-Marks wireframe map with bounding boxes, numeric badges, and centroids rendered onto a 100% transparent (RGBA) background with zero desktop wallpaper or pixel entropy.
  - Gives agents a visual spatial map layout without consuming high-density image tokens.
- **Multi-Tier Agent Observation Hierarchy**:
  - `mode="text"` (DEFAULT): Local OCR and contour grounding returning structured element text and centroids (~50–100 tokens, 0 vision tokens).
  - `mode="map"`: Sparse SoM wireframe map on a transparent background for low-token spatial layout comprehension.
  - `mode="compact"`: Downscaled 512px compressed JPEG thumbnail (~258 base vision tokens) for rough visual inspections.
  - `mode="full"`: Lossless 1280x800 screenshot ("token shredder") for when pixel-level graphics and full visual detail are mandatory.
  - `mode="grounded"`: Full screenshot with SoM boxes composited on top of desktop wallpaper.
- **Isolated Clean Human User Feed (`vde_vlm/web_viewer.py`)**:
  - Web UI at `http://localhost:7891` now strictly serves the clean, pristine desktop display via `/api/screen` without SAM/grounding boxes cluttering the human user's view.
  - Added dedicated agent feed endpoints: `/api/screen_map` (transparent wireframe map), `/api/screen_compact` (512px thumbnail), and `/api/grounded_screen`.
- **Eliminated Windows Screenshot File Sharing Violations (`vde_vlm/vision.py`)**:
  - Added an exponential retry loop and automatic unique temporary file fallback when Windows processes access the rolling screen cache concurrently, completely eliminating `VERR_SHARING_VIOLATION`.
