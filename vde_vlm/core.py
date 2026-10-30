"""
vde_vlm.core
~~~~~~~~~~~~
High-level object-oriented VM interface for Vision-Language Models and AI agents.
Combines lifecycle, vision, keyboard, mouse, guest execution, snapshots,
compound batch actions, and collaborative presence broadcasting.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from vde_vlm.vbox import (
    find_vboxmanage,
    get_vm_info,
    get_vm_state,
    is_vm_running,
    list_vms,
    run_vbox_cmd,
)
from vde_vlm.vision import (
    add_coordinate_grid,
    clean_temp_artifacts,
    compare_screenshots,
    draw_agent_cursor,
    get_rolling_screen_path,
    inspect_screen_state,
    take_screenshot,
    transcribe_screen,
)
from vde_vlm.keyboard import press_key, type_string
from vde_vlm.mouse import click, move_to, scroll
from vde_vlm.guest import copy_from_guest, copy_to_guest, run_guest_command
from vde_vlm.snapshots import delete_snapshot, list_snapshots, restore_snapshot, safe_checkpoint, take_snapshot
from vde_vlm.macro import MacroStep, execute_batch

logger = logging.getLogger(__name__)


class VBoxVM:
    """Represents a VirtualBox Virtual Machine under VLM control."""

    def __init__(self, name_or_uuid: str):
        self.name_or_uuid = name_or_uuid
        self._last_screenshot: Optional[str] = None
        self._last_grid_screenshot: Optional[str] = None

    @classmethod
    def list_all(cls) -> List[VBoxVM]:
        """List all available VirtualBox machines as VBoxVM instances."""
        return [cls(m["name"]) for m in list_vms()]

    @property
    def name(self) -> str:
        return self.info.get("name", self.name_or_uuid)

    @property
    def uuid(self) -> str:
        return self.info.get("UUID", "")

    @property
    def state(self) -> str:
        return get_vm_state(self.name_or_uuid)

    @property
    def is_running(self) -> bool:
        return is_vm_running(self.name_or_uuid)

    @property
    def info(self) -> Dict[str, Any]:
        return get_vm_info(self.name_or_uuid)

    # -------------------------------------------------------------------------
    # Collaborative Presence
    # -------------------------------------------------------------------------

    def notify_agent_cursor(self, x: int, y: int, is_click: bool = True, label: str = "Gemini"):
        """Notify the live web viewer of an agent cursor event."""
        try:
            from vde_vlm.web_viewer import notify_agent_action
            notify_agent_action(x, y, is_click=is_click, label=label)
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # Lifecycle Management
    # -------------------------------------------------------------------------

    def start(self, headless: bool = True, wait_seconds: float = 3.0) -> bool:
        """Start the virtual machine."""
        if self.is_running:
            logger.info(f"VM '{self.name_or_uuid}' is already running.")
            return True

        from vde_vlm.session_manager import VBoxSessionManager
        sm = VBoxSessionManager.get_instance()
        ok = sm.start_vm_interactive(self.name_or_uuid, headless=headless)
        if ok and self.is_running:
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            return True

        vm_type = "headless" if headless else "gui"
        run_vbox_cmd("startvm", self.name_or_uuid, "--type", vm_type)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        return self.is_running

    def stop(self, mode: str = "poweroff", wait_seconds: float = 2.0) -> bool:
        """Stop or pause the virtual machine."""
        if not self.is_running and mode != "savestate":
            logger.info(f"VM '{self.name_or_uuid}' is not running.")
            return True

        if mode == "poweroff":
            run_vbox_cmd("controlvm", self.name_or_uuid, "poweroff")
        elif mode == "savestate":
            run_vbox_cmd("controlvm", self.name_or_uuid, "savestate")
        elif mode == "acpipowerbutton":
            run_vbox_cmd("controlvm", self.name_or_uuid, "acpipowerbutton")
        elif mode == "pause":
            run_vbox_cmd("controlvm", self.name_or_uuid, "pause")
        elif mode == "resume":
            run_vbox_cmd("controlvm", self.name_or_uuid, "resume")
        elif mode == "reset":
            run_vbox_cmd("controlvm", self.name_or_uuid, "reset")
        else:
            raise ValueError(f"Unknown stop mode: {mode}")

        if wait_seconds > 0:
            time.sleep(wait_seconds)
        return not self.is_running

    # -------------------------------------------------------------------------
    # Vision & Perception
    # -------------------------------------------------------------------------

    def screenshot(
        self,
        output_path: Optional[str] = None,
        with_grid: bool = False,
        grid_step: int = 100,
        display: int = 0,
        use_rolling_cache: bool = True,
        style: str = "stitch",
    ) -> str:
        """Capture a screenshot of the VM screen with zero disk shredding.

        Args:
            output_path: Path to write PNG file. If None, overwrites rolling buffer.
            with_grid: If True, also overlays subtle non-obtrusive coordinate grid.
            grid_step: Distance in pixels between grid marks.
            display: Display index.
            use_rolling_cache: If True, uses persistent rolling file.
            style: 'stitch' for sleek subtle guides, 'dense' for high-contrast lines.

        Returns:
            Path to the captured screenshot.
        """
        screen_file = take_screenshot(
            self.name_or_uuid,
            output_path=output_path,
            display=display,
            use_rolling_cache=use_rolling_cache,
        )
        self._last_screenshot = screen_file

        if with_grid:
            grid_dest = get_rolling_screen_path(self.name_or_uuid, annotated=True) if use_rolling_cache else None
            grid_file = add_coordinate_grid(screen_file, output_path=grid_dest, grid_step=grid_step, style=style)
            self._last_grid_screenshot = grid_file
            return grid_file

        return screen_file

    def observe(
        self,
        grid: bool = True,
        ocr: bool = False,
        use_rolling_cache: bool = True,
    ) -> Dict[str, Any]:
        """Produce a complete multimodal observation of the VM state with zero disk clutter.

        Returns:
            Dictionary containing state, resolution, screenshot paths, brightness,
            and optional OCR transcription.
        """
        raw_screen = self.screenshot(with_grid=False, use_rolling_cache=use_rolling_cache)
        metrics = inspect_screen_state(raw_screen)

        grid_path = None
        if grid:
            grid_path = self.screenshot(with_grid=True, use_rolling_cache=use_rolling_cache)
            self._last_grid_screenshot = grid_path

        obs: Dict[str, Any] = {
            "vm": self.name_or_uuid,
            "state": self.state,
            "is_running": self.is_running,
            "resolution": (metrics["width"], metrics["height"]),
            "is_all_black": metrics["is_all_black"],
            "average_brightness": metrics["average_brightness"],
            "screenshot": raw_screen,
            "grid_screenshot": grid_path,
        }

        if ocr:
            obs["ocr"] = transcribe_screen(raw_screen)

        return obs

    # -------------------------------------------------------------------------
    # Input & Interaction
    # -------------------------------------------------------------------------

    def click(
        self,
        x: int,
        y: int,
        button: str = "left",
        double: bool = False,
        verify_change: bool = False,
        broadcast_cursor: bool = True,
    ) -> Dict[str, Any]:
        """Click at screen coordinates (x, y)."""
        if broadcast_cursor:
            self.notify_agent_cursor(x, y, is_click=True)

        before_shot = None
        if verify_change:
            before_shot = self.screenshot()

        res_x, res_y = 1920, 1080
        if self._last_screenshot and os.path.exists(self._last_screenshot):
            m = inspect_screen_state(self._last_screenshot)
            res_x, res_y = m["width"], m["height"]

        success = click(self.name_or_uuid, x, y, button=button, screen_width=res_x, screen_height=res_y, double=double)
        res = {"success": success, "x": x, "y": y, "button": button}

        if verify_change and before_shot:
            time.sleep(0.4)
            after_shot = self.screenshot()
            diff_ratio, has_changed = compare_screenshots(before_shot, after_shot)
            res["changed"] = has_changed
            res["diff_ratio"] = round(diff_ratio, 4)

        return res

    def detect_elements(self, confidence: float = 0.35, include_shapes: bool = True) -> List[Dict[str, Any]]:
        """Detect text labels, buttons, and UI elements on the current VM screen."""
        from vde_vlm.grounding import detect_ui_elements
        shot = self.screenshot(use_rolling_cache=True)
        return detect_ui_elements(shot, confidence_threshold=confidence, include_shapes=include_shapes)

    def find_element(self, query: str, confidence: float = 0.35) -> Optional[Dict[str, Any]]:
        """Find a specific button or text element by label."""
        from vde_vlm.grounding import find_element_by_text
        shot = self.screenshot(use_rolling_cache=True)
        return find_element_by_text(shot, query, min_confidence=confidence)

    def click_element(self, query: str, button: str = "left", double: bool = False) -> Dict[str, Any]:
        """Locate a UI element by text label and click its centroid."""
        el = self.find_element(query)
        if not el:
            return {"success": False, "error": f"Element '{query}' not found on screen"}
        cx, cy = el["centroid"]
        res = self.click(cx, cy, button=button, double=double)
        res["element"] = el
        return res

    def observe_grounded(self, confidence: float = 0.35) -> Dict[str, Any]:
        """Capture screen and render Set-of-Marks (SoM) bounding box overlay."""
        from vde_vlm.grounding import detect_ui_elements, draw_grounded_overlay
        shot = self.screenshot(use_rolling_cache=True)
        elements = detect_ui_elements(shot, confidence_threshold=confidence)
        overlay_path = draw_grounded_overlay(shot, elements)
        return {
            "screenshot": shot,
            "grounded_screenshot": overlay_path,
            "elements": elements,
            "count": len(elements),
        }

    def type(self, text: str, press_enter: bool = False) -> None:
        """Type characters into the active VM window."""
        type_string(self.name_or_uuid, text, press_enter=press_enter)

    def press_key(self, key_or_chord: str) -> None:
        """Press a special key or chord (e.g. 'enter', 'super', 'ctrl+alt+t', 'esc')."""
        press_key(self.name_or_uuid, key_or_chord)

    # -------------------------------------------------------------------------
    # Compound Batch Actions & Macros
    # -------------------------------------------------------------------------

    def batch(self, steps: List[Union[Dict[str, Any], MacroStep, str]], verify: bool = True) -> Dict[str, Any]:
        """Execute a compound sequence of actions in one atomic call.

        Example steps:
            ['type:echo hello|enter', 'wait:0.5', 'click:450,720']
        """
        return execute_batch(self, steps, verify_final_change=verify)

    def macro(self, *steps: str) -> Dict[str, Any]:
        """Shorthand macro runner using string notation."""
        return self.batch(list(steps))

    # -------------------------------------------------------------------------
    # Guest OS Commands & Files
    # -------------------------------------------------------------------------

    def exec(
        self,
        command: str,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: float = 60.0,
        check: bool = True,
    ) -> Tuple[int, str, str]:
        """Execute a bash command inside the guest VM."""
        return run_guest_command(
            self.name_or_uuid,
            command,
            username=username,
            password=password,
            timeout=timeout,
            check=check,
        )

    def upload(self, host_path: str, guest_path: str, username: Optional[str] = None, password: Optional[str] = None) -> None:
        """Copy a file or directory from host into the guest VM."""
        copy_to_guest(self.name_or_uuid, host_path, guest_path, username=username, password=password)

    def download(self, guest_path: str, host_path: str, username: Optional[str] = None, password: Optional[str] = None) -> None:
        """Copy a file or directory from the guest VM to host."""
        copy_from_guest(self.name_or_uuid, guest_path, host_path, username=username, password=password)

    # -------------------------------------------------------------------------
    # Snapshot Management
    # -------------------------------------------------------------------------

    def snapshot(self, name: str, description: Optional[str] = None) -> str:
        """Take a snapshot of the VM state."""
        return take_snapshot(self.name_or_uuid, name, description=description)

    def restore(self, name_or_uuid: str) -> None:
        """Restore the VM to a previous snapshot."""
        if self.is_running:
            self.stop(mode="poweroff")
        restore_snapshot(self.name_or_uuid, name_or_uuid)

    def list_snapshots(self) -> List[Dict[str, str]]:
        """List all snapshots."""
        return list_snapshots(self.name_or_uuid)

    def checkpoint(self, name: Optional[str] = None):
        """Context manager for safe transactional testing."""
        return safe_checkpoint(self.name_or_uuid, name)
