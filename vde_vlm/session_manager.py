"""
vde_vlm.session_manager
~~~~~~~~~~~~~~~~~~~~~~~
Persistent COM Session Manager for VirtualBox.
Maintains an active VirtualBox ISession in-process to enable direct,
low-latency hardware mouse and keyboard injection without process boundary limits.
"""

from __future__ import annotations

import logging
import platform
import time
from typing import Any, Dict, Optional, Tuple

from vde_vlm.vbox import is_vm_running, run_vbox_cmd
from vde_vlm.keyboard import parse_key_combo, type_string

logger = logging.getLogger(__name__)

# Button constants
BUTTON_NONE = 0
BUTTON_LEFT = 1
BUTTON_RIGHT = 2
BUTTON_MIDDLE = 4


class VBoxSessionManager:
    """Manages an active VirtualBox COM Session for live interactive control."""

    _instance: Optional[VBoxSessionManager] = None

    def __init__(self):
        self._vbox = None
        self._active_session = None
        self._active_vm_name = None
        self._last_norm_x: int = 32768
        self._last_norm_y: int = 32768
        self._init_com()

    @classmethod
    def get_instance(cls) -> VBoxSessionManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _init_com(self):
        if platform.system() == "Windows":
            try:
                import win32com.client
                self._vbox = win32com.client.Dispatch("VirtualBox.VirtualBox")
            except Exception as exc:
                logger.warning(f"Could not initialize COM VirtualBox: {exc}")

    def get_active_session(self, vm_name_or_uuid: str):
        """Return the active ISession object with Console if open."""
        if self._active_session is not None and self._active_vm_name == vm_name_or_uuid:
            try:
                if self._active_session.State == 2 and self._active_session.Console is not None:
                    return self._active_session
            except Exception:
                self._active_session = None

        return None

    def start_vm_interactive(self, vm_name_or_uuid: str, headless: bool = True) -> bool:
        """Boot the VM using LaunchVMProcess to retain full Console COM access."""
        if is_vm_running(vm_name_or_uuid):
            logger.info(f"VM '{vm_name_or_uuid}' is already running.")
            return True

        if platform.system() == "Windows" and self._vbox is not None:
            try:
                import win32com.client
                session = win32com.client.Dispatch("VirtualBox.Session")
                machine = self._vbox.FindMachine(vm_name_or_uuid)
                vm_type = "headless" if headless else "gui"
                progress = machine.LaunchVMProcess(session, vm_type, [])
                progress.WaitForCompletion(15000)

                self._active_session = session
                self._active_vm_name = vm_name_or_uuid
                logger.info(f"VM '{vm_name_or_uuid}' started with active in-process COM console.")
                return True
            except Exception as exc:
                logger.warning(f"LaunchVMProcess failed, falling back to VBoxManage: {exc}")

        # Fallback to standard start
        run_vbox_cmd("startvm", vm_name_or_uuid, "--type", "headless" if headless else "gui")
        return is_vm_running(vm_name_or_uuid)

    def mouse_move(
        self,
        vm_name_or_uuid: str,
        x: int,
        y: int,
        width: int = 1280,
        height: int = 800,
    ) -> bool:
        """Move the mouse pointer to (x, y)."""
        px = max(1, min(width, int(x)))
        py = max(1, min(height, int(y)))
        session = self.get_active_session(vm_name_or_uuid)
        if session and session.Console:
            try:
                mouse = session.Console.Mouse
                mouse.PutMouseEventAbsolute(px, py, 0, 0, BUTTON_NONE)
                self._last_norm_x = px
                self._last_norm_y = py
                return True
            except Exception as exc:
                logger.debug(f"COM mouse move error: {exc}")

        # Fallback to shared lock
        from vde_vlm.mouse import _get_com_console
        sh_session, console = _get_com_console(vm_name_or_uuid)
        if console:
            try:
                console.Mouse.PutMouseEventAbsolute(px, py, 0, 0, BUTTON_NONE)
                return True
            finally:
                if sh_session:
                    sh_session.UnlockMachine()
        return False

    def mouse_click(
        self,
        vm_name_or_uuid: str,
        x: int,
        y: int,
        button: str = "left",
        width: int = 1280,
        height: int = 800,
        double: bool = False,
    ) -> bool:
        """Inject absolute mouse click using in-process COM Console or shared lock fallback."""
        btn_mask = BUTTON_LEFT
        if button.lower() == "right":
            btn_mask = BUTTON_RIGHT
        elif button.lower() == "middle":
            btn_mask = BUTTON_MIDDLE

        px = max(1, min(width, int(x)))
        py = max(1, min(height, int(y)))

        # 1. Try active session console
        session = self.get_active_session(vm_name_or_uuid)
        if session and session.Console:
            try:
                mouse = session.Console.Mouse
                mouse.PutMouseEventAbsolute(px, py, 0, 0, BUTTON_NONE)
                time.sleep(0.04)
                mouse.PutMouseEventAbsolute(px, py, 0, 0, btn_mask)
                time.sleep(0.06)
                mouse.PutMouseEventAbsolute(px, py, 0, 0, BUTTON_NONE)

                if double:
                    time.sleep(0.08)
                    mouse.PutMouseEventAbsolute(px, py, 0, 0, btn_mask)
                    time.sleep(0.06)
                    mouse.PutMouseEventAbsolute(px, py, 0, 0, BUTTON_NONE)

                self._last_norm_x = px
                self._last_norm_y = py
                logger.info(f"Mouse click injected at ({px}, {py}) btn={button}")
                return True
            except Exception as exc:
                logger.warning(f"COM mouse click failed: {exc}")

        # 2. Try shared lock console
        from vde_vlm.mouse import _get_com_console
        sh_session, console = _get_com_console(vm_name_or_uuid)
        if console:
            try:
                console.Mouse.PutMouseEventAbsolute(px, py, 0, 0, BUTTON_NONE)
                time.sleep(0.04)
                console.Mouse.PutMouseEventAbsolute(px, py, 0, 0, btn_mask)
                time.sleep(0.06)
                console.Mouse.PutMouseEventAbsolute(px, py, 0, 0, BUTTON_NONE)

                if double:
                    time.sleep(0.08)
                    console.Mouse.PutMouseEventAbsolute(px, py, 0, 0, btn_mask)
                    time.sleep(0.06)
                    console.Mouse.PutMouseEventAbsolute(px, py, 0, 0, BUTTON_NONE)

                logger.info(f"Shared lock mouse click injected at ({px}, {py}) btn={button}")
                return True
            finally:
                if sh_session:
                    sh_session.UnlockMachine()

        return False

    def send_key(self, vm_name_or_uuid: str, key_or_chord: str) -> bool:
        """Send key or key combination to VM."""
        session = self.get_active_session(vm_name_or_uuid)
        makes, breaks = parse_key_combo(key_or_chord)

        if session and session.Console:
            try:
                kbd = session.Console.Keyboard
                sc_ints = [int(s, 16) for s in (makes + breaks)]
                kbd.PutScancodes(sc_ints)
                return True
            except Exception as exc:
                logger.debug(f"Direct COM PutScancodes failed: {exc}")

        # Fallback to VBoxManage controlvm keyboardputscancode
        run_vbox_cmd("controlvm", vm_name_or_uuid, "keyboardputscancode", *makes)
        time.sleep(0.03)
        run_vbox_cmd("controlvm", vm_name_or_uuid, "keyboardputscancode", *breaks)
        return True

    def type_text(self, vm_name_or_uuid: str, text: str, enter: bool = False) -> bool:
        """Type characters into VM."""
        type_string(vm_name_or_uuid, text, press_enter=enter)
        return True
