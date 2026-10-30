"""
vde_vlm.core
~~~~~~~~~~~~
High-level object-oriented VM interface for Vision-Language Models and AI agents.
Combines lifecycle, vision, keyboard, mouse, guest execution, and snapshots.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

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
    compare_screenshots,
    inspect_screen_state,
    take_screenshot,
    transcribe_screen,
)
from vde_vlm.keyboard import press_key, type_string
from vde_vlm.mouse import click, move_to, scroll
from vde_vlm.guest import copy_from_guest, copy_to_guest, run_guest_command
from vde_vlm.snapshots import delete_snapshot, list_snapshots, restore_snapshot, safe_checkpoint, take_snapshot

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
    # Lifecycle Management
    # -------------------------------------------------------------------------

    def start(self, headless: bool = True, wait_seconds: float = 3.0) -> bool:
        """Start the virtual machine.

        Args:
            headless: If True, boots without a host desktop window (GUI-less).
            wait_seconds: Initial settling time after boot command.
        """
        if self.is_running:
            logger.info(f"VM '{self.name_or_uuid}' is already running.")
            return True

        vm_type = "headless" if headless else "gui"
        run_vbox_cmd("startvm", self.name_or_uuid, "--type", vm_type)
        if wait_seconds > 0:
            time.sleep(wait_seconds)
        return self.is_running

    def stop(self, mode: str = "poweroff", wait_seconds: float = 2.0) -> bool:
        """Stop or pause the virtual machine.

        Args:
            mode: 'poweroff', 'savestate', 'acpipowerbutton', or 'pause'.
            wait_seconds: Settling time.
        """
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
    ) -> str:
        """Capture a screenshot of the VM screen.

        Args:
            output_path: Path to write the PNG file.
            with_grid: If True, also generates a coordinate-grid overlay.
            grid_step: Pixel distance between grid lines.
            display: VirtualBox display index.

        Returns:
            Path to the captured screenshot (or grid screenshot if with_grid is True).
        """
        screen_file = take_screenshot(self.name_or_uuid, output_path=output_path, display=display)
        self._last_screenshot = screen_file

        if with_grid:
            grid_file = add_coordinate_grid(screen_file, grid_step=grid_step)
            self._last_grid_screenshot = grid_file
            return grid_file

        return screen_file

    def observe(self, grid: bool = True, ocr: bool = False) -> Dict[str, Any]:
        """Produce a complete multimodal observation of the VM state.

        Returns:
            Dictionary containing state, resolution, screenshot paths, brightness,
            and optional OCR transcription.
        """
        raw_screen = self.screenshot(with_grid=False)
        metrics = inspect_screen_state(raw_screen)

        grid_path = None
        if grid:
            grid_path = add_coordinate_grid(raw_screen)
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
    ) -> Dict[str, Any]:
        """Click at screen coordinates (x, y).

        Args:
            x: X pixel coordinate.
            y: Y pixel coordinate.
            button: 'left', 'right', or 'middle'.
            double: If True, performs a double-click.
            verify_change: If True, compares screenshots before and after click.

        Returns:
            Dict with execution status and visual change ratio.
        """
        before_shot = None
        if verify_change:
            before_shot = self.screenshot()

        # Resolution inference
        res_x, res_y = 1920, 1080
        if self._last_screenshot and os.path.exists(self._last_screenshot):
            m = inspect_screen_state(self._last_screenshot)
            res_x, res_y = m["width"], m["height"]

        success = click(self.name_or_uuid, x, y, button=button, screen_width=res_x, screen_height=res_y, double=double)

        res = {"success": success, "x": x, "y": y, "button": button}

        if verify_change and before_shot:
            time.sleep(0.5)
            after_shot = self.screenshot()
            diff_ratio, has_changed = compare_screenshots(before_shot, after_shot)
            res["changed"] = has_changed
            res["diff_ratio"] = round(diff_ratio, 4)

        return res

    def type(self, text: str, press_enter: bool = False) -> None:
        """Type characters into the active VM window."""
        type_string(self.name_or_uuid, text, press_enter=press_enter)

    def press_key(self, key_or_chord: str) -> None:
        """Press a special key or chord (e.g. 'enter', 'super', 'ctrl+alt+t', 'esc')."""
        press_key(self.name_or_uuid, key_or_chord)

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
