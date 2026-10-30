"""
vde_vlm.keyboard
~~~~~~~~~~~~~~~~
Keyboard input injection for VirtualBox VMs.
Maps keys and key combinations into standard PS/2 Set 1 scancodes for VBoxManage,
and supports direct string typing.
"""

from __future__ import annotations

import time
from typing import List, Tuple
from vde_vlm.vbox import run_vbox_cmd


# PS/2 Set 1 Scancodes: (Make / Press, Break / Release)
# Single byte or multi-byte sequences as space-separated hex strings
SCANCODE_MAP = {
    # Alphabet
    "a": ("1e", "9e"),
    "b": ("30", "b0"),
    "c": ("2e", "ae"),
    "d": ("20", "a0"),
    "e": ("12", "92"),
    "f": ("21", "a1"),
    "g": ("22", "a2"),
    "h": ("23", "a3"),
    "i": ("17", "97"),
    "j": ("24", "a4"),
    "k": ("25", "a5"),
    "l": ("26", "a6"),
    "m": ("32", "b2"),
    "n": ("31", "b1"),
    "o": ("18", "98"),
    "p": ("19", "99"),
    "q": ("10", "90"),
    "r": ("13", "93"),
    "s": ("1f", "9f"),
    "t": ("14", "94"),
    "u": ("16", "96"),
    "v": ("2f", "af"),
    "w": ("11", "91"),
    "x": ("2d", "ad"),
    "y": ("15", "95"),
    "z": ("2c", "ac"),

    # Numbers (top row)
    "1": ("02", "82"),
    "2": ("03", "83"),
    "3": ("04", "84"),
    "4": ("05", "85"),
    "5": ("06", "86"),
    "6": ("07", "87"),
    "7": ("08", "88"),
    "8": ("09", "89"),
    "9": ("0a", "8a"),
    "0": ("0b", "8b"),

    # Special / Control keys
    "enter": ("1c", "9c"),
    "return": ("1c", "9c"),
    "esc": ("01", "81"),
    "escape": ("01", "81"),
    "backspace": ("0e", "8e"),
    "tab": ("0f", "8f"),
    "space": ("39", "b9"),
    " ": ("39", "b9"),
    "capslock": ("3a", "ba"),
    "minus": ("0c", "8c"),
    "-": ("0c", "8c"),
    "equal": ("0d", "8d"),
    "=": ("0d", "8d"),
    "leftbracket": ("1a", "9a"),
    "[": ("1a", "9a"),
    "rightbracket": ("1b", "9b"),
    "]": ("1b", "9b"),
    "backslash": ("2b", "ab"),
    "\\": ("2b", "ab"),
    "semicolon": ("27", "a7"),
    ";": ("27", "a7"),
    "quote": ("28", "a8"),
    "'": ("28", "a8"),
    "grave": ("29", "a9"),
    "`": ("29", "a9"),
    "comma": ("33", "b3"),
    ",": ("33", "b3"),
    "period": ("34", "b4"),
    ".": ("34", "b4"),
    "slash": ("35", "b5"),
    "/": ("35", "b5"),

    # Modifiers
    "ctrl": ("1d", "9d"),
    "control": ("1d", "9d"),
    "lctrl": ("1d", "9d"),
    "rctrl": ("e0 1d", "e0 9d"),
    "shift": ("2a", "aa"),
    "lshift": ("2a", "aa"),
    "rshift": ("36", "b6"),
    "alt": ("38", "b8"),
    "lalt": ("38", "b8"),
    "ralt": ("e0 38", "e0 b8"),
    "super": ("e0 5b", "e0 db"),
    "win": ("e0 5b", "e0 db"),
    "meta": ("e0 5b", "e0 db"),

    # Navigation / Editing
    "insert": ("e0 52", "e0 d2"),
    "delete": ("e0 53", "e0 d3"),
    "home": ("e0 47", "e0 c7"),
    "end": ("e0 4f", "e0 cf"),
    "pageup": ("e0 49", "e0 c9"),
    "pgup": ("e0 49", "e0 c9"),
    "pagedown": ("e0 51", "e0 d1"),
    "pgdn": ("e0 51", "e0 d1"),
    "up": ("e0 48", "e0 c8"),
    "down": ("e0 50", "e0 d0"),
    "left": ("e0 4b", "e0 cb"),
    "right": ("e0 4d", "e0 cd"),

    # Function keys
    "f1": ("3b", "bb"),
    "f2": ("3c", "bc"),
    "f3": ("3d", "bd"),
    "f4": ("3e", "be"),
    "f5": ("3f", "bf"),
    "f6": ("40", "c0"),
    "f7": ("41", "c1"),
    "f8": ("42", "c2"),
    "f9": ("43", "c3"),
    "f10": ("44", "c4"),
    "f11": ("57", "d7"),
    "f12": ("58", "d8"),
}


def parse_key_combo(combo_str: str) -> Tuple[List[str], List[str]]:
    """Parse a key combo string like 'ctrl+alt+t' or 'super' into make/break scancodes.

    Returns:
        Tuple of (make_scancodes_list, break_scancodes_list)
    """
    parts = [p.strip().lower() for p in combo_str.split("+") if p.strip()]
    makes = []
    breaks = []

    for part in parts:
        if part not in SCANCODE_MAP:
            raise ValueError(f"Unknown key identifier: '{part}'")
        make, brk = SCANCODE_MAP[part]
        makes.extend(make.split())
        # Break codes will be applied in reverse order
        breaks = brk.split() + breaks

    return makes, breaks


def send_scancodes(vm_name_or_uuid: str, scancodes: List[str]) -> None:
    """Send raw hex scancodes to the VM."""
    if not scancodes:
        return
    run_vbox_cmd("controlvm", vm_name_or_uuid, "keyboardputscancode", *scancodes)


def press_key(vm_name_or_uuid: str, key_or_combo: str, delay_between_ms: int = 50) -> None:
    """Press and release a key or key combination (e.g. 'ctrl+alt+t', 'enter', 'super').

    Args:
        vm_name_or_uuid: Target VM.
        key_or_combo: Key or chord (e.g. 'ctrl+c', 'alt+f4', 'enter').
        delay_between_ms: Delay in ms between make and break scancodes.
    """
    makes, breaks = parse_key_combo(key_or_combo)

    # Press keys
    send_scancodes(vm_name_or_uuid, makes)
    if delay_between_ms > 0:
        time.sleep(delay_between_ms / 1000.0)
    # Release keys in reverse
    send_scancodes(vm_name_or_uuid, breaks)


def type_string(vm_name_or_uuid: str, text: str, press_enter: bool = False) -> None:
    """Type a string into the target VM.

    Args:
        vm_name_or_uuid: Target VM.
        text: String content to type.
        press_enter: If True, sends an Enter keypress after typing the text.
    """
    if text:
        run_vbox_cmd("controlvm", vm_name_or_uuid, "keyboardputstring", text)
    if press_enter:
        press_key(vm_name_or_uuid, "enter")
