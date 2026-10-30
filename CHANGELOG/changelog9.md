# Changelog 9 - Fix Broken Image Stream, In-Memory Zero-Latency Cache & Thread-Safe Screenshot Locks

## Summary
- **In-Memory Zero-Latency Frame Cache (`vde_vlm/web_viewer.py`)**:
  - Replaced synchronous per-request file reads and OCR execution with a background async frame capture worker (`_capture_frame_sync`).
  - `/api/screen` and `/api/grounded_screen` now serve directly from in-memory byte buffers (`_cached_screen_bytes`, `_cached_grounded_bytes`) in less than 1 millisecond.
  - Eliminated the `UnboundLocalError` on `_cached_grounded_bytes`.
- **Thread-Safe Screenshot Capture (`vde_vlm/vision.py`)**:
  - Added module-level `_SCREENSHOT_LOCK` around `VBoxManage controlvm ... screenshotpng` to prevent Windows `VERR_SHARING_VIOLATION` when concurrent background threads access the rolling frame buffer.
- **Frontend Double-Buffered Stream (`vde_vlm/web_viewer.py`)**:
  - Replaced naive `setInterval` (which aborted in-flight requests in Chrome and rendered the `[broken image] Live VM Display` alt text) with double-buffered `onload` / `onerror` image chaining.
  - Images are pre-loaded in memory and swapped only when 100% complete and valid, eliminating flickering and broken image icons.
