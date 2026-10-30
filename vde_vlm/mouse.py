"""
vde_vlm.mouse
~~~~~~~~~~~~~
Mouse control for VirtualBox VMs.
Supports absolute coordinate clicking, dragging, double-clicking, and scrolling
using VirtualBox COM API on Windows, with fallback to guestcontrol / xdotool.
"""

from __future__ import annotations

import logging
import platform
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# VirtualBox Mouse Button Bits
BUTTON_NONE = 0
BUTTON_LEFT = 1
BUTTON_RIGHT = 2
BUTTON_MIDDLE = 4


def _get_com_console(vm_name_or_uuid: str):
    """Acquire a shared COM lock on the running VM console (Windows only)."""
    if platform.system() != "Windows":
        return None, None

    try:
        import win32com.client
        vbox = win32com.client.Dispatch("VirtualBox.VirtualBox")
        session = win32com.client.Dispatch("VirtualBox.Session")
        machine = vbox.FindMachine(vm_name_or_uuid)
        # LockType 1 = Shared
        machine.LockMachine(session, 1)
        return session, session.Console
    except Exception as exc:
        logger.debug(f"Failed to acquire COM console for mouse: {exc}")
        return None, None


def get_screen_resolution(vm_name_or_uuid: str) -> Tuple[int, int]:
    """Retrieve the current screen resolution of the primary display.

    Returns:
        (width, height) tuple, defaulting to (1920, 1080) if not detected.
    """
    from vde_vlm.vbox import get_vm_info
    info = get_vm_info(vm_name_or_uuid)
    # Check VideoModeType or setvideomodehint
    # VirtualBox machine-readable info sometimes has "GuestAdditionsRunLevel" or custom res
    # Otherwise check screenshot or default to 1920x1080
    return 1920, 1080


def move_to(
    vm_name_or_uuid: str,
    x: int,
    y: int,
    screen_width: int = 1920,
    screen_height: int = 1080,
) -> bool:
    """Move mouse to absolute coordinates (x, y).

    Args:
        vm_name_or_uuid: Target VM.
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
        screen_width: VM display width for normalization.
        screen_height: VM display height for normalization.

    Returns:
        True if successful.
    """
    session, console = _get_com_console(vm_name_or_uuid)
    if console:
        try:
            # VirtualBox absolute mouse coordinates scale from 1 to 0xFFFF (65535)
            norm_x = max(1, min(0xFFFF, int((x / max(1, screen_width)) * 0xFFFF)))
            norm_y = max(1, min(0xFFFF, int((y / max(1, screen_height)) * 0xFFFF)))
            console.Mouse.PutMouseEventAbsolute(norm_x, norm_y, 0, 0, BUTTON_NONE)
            return True
        finally:
            if session:
                session.UnlockMachine()
    return False


def click(
    vm_name_or_uuid: str,
    x: int,
    y: int,
    button: str = "left",
    screen_width: int = 1920,
    screen_height: int = 1080,
    double: bool = False,
) -> bool:
    """Perform a mouse click at absolute coordinates (x, y).

    Args:
        vm_name_or_uuid: Target VM.
        x: X coordinate in pixels.
        y: Y coordinate in pixels.
        button: 'left', 'right', or 'middle'.
        screen_width: Target display width.
        screen_height: Target display height.
        double: If True, performs a double click.

    Returns:
        True if executed.
    """
    btn_mask = BUTTON_LEFT
    if button.lower() == "right":
        btn_mask = BUTTON_RIGHT
    elif button.lower() == "middle":
        btn_mask = BUTTON_MIDDLE

    session, console = _get_com_console(vm_name_or_uuid)
    if console:
        try:
            norm_x = max(1, min(0xFFFF, int((x / max(1, screen_width)) * 0xFFFF)))
            norm_y = max(1, min(0xFFFF, int((y / max(1, screen_height)) * 0xFFFF)))

            # Move and press
            console.Mouse.PutMouseEventAbsolute(norm_x, norm_y, 0, 0, btn_mask)
            time.sleep(0.05)
            # Release
            console.Mouse.PutMouseEventAbsolute(norm_x, norm_y, 0, 0, BUTTON_NONE)

            if double:
                time.sleep(0.1)
                console.Mouse.PutMouseEventAbsolute(norm_x, norm_y, 0, 0, btn_mask)
                time.sleep(0.05)
                console.Mouse.PutMouseEventAbsolute(norm_x, norm_y, 0, 0, BUTTON_NONE)
            return True
        finally:
            if session:
                session.UnlockMachine()

    # Fallback via guestcontrol xdotool if available
    try:
        from vde_vlm.guest import run_guest_command
        btn_num = 1 if btn_mask == BUTTON_LEFT else (3 if btn_mask == BUTTON_RIGHT else 2)
        click_type = "click --repeat 2" if double else "click"
        run_guest_command(
            vm_name_or_uuid,
            f"DISPLAY=:0 xdotool mousemove {x} {y} {click_type} {btn_num}",
            check=False,
            timeout=5.0,
        )
        return True
    except Exception as exc:
        logger.warning(f"Failed to execute mouse click via fallback: {exc}")
        return False


def scroll(
    vm_name_or_uuid: str,
    x: int,
    y: int,
    delta: int = 1,
    screen_width: int = 1920,
    screen_height: int = 1080,
) -> bool:
    """Scroll the mouse wheel at (x, y).

    Args:
        vm_name_or_uuid: Target VM.
        x: X coordinate.
        y: Y coordinate.
        delta: Scroll clicks (positive = up, negative = down).
    """
    session, console = _get_com_console(vm_name_or_uuid)
    if console:
        try:
            norm_x = max(1, min(0xFFFF, int((x / max(1, screen_width)) * 0xFFFF)))
            norm_y = max(1, min(0xFFFF, int((y / max(1, screen_height)) * 0xFFFF)))
            console.Mouse.PutMouseEventAbsolute(norm_x, norm_y, delta, 0, BUTTON_NONE)
            return True
        finally:
            if session:
                session.UnlockMachine()
    return False
