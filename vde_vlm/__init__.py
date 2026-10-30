"""
VDE-VLM-ACCESS: VirtualBox interaction toolkit for Vision-Language Models & autonomous coding agents.
"""

from vde_vlm.core import VBoxVM
from vde_vlm.vbox import (
    find_vboxmanage,
    get_vm_info,
    get_vm_state,
    is_vm_running,
    list_running_vms,
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
from vde_vlm.keyboard import parse_key_combo, press_key, type_string
from vde_vlm.mouse import click, move_to, scroll
from vde_vlm.guest import copy_from_guest, copy_to_guest, run_guest_command
from vde_vlm.snapshots import delete_snapshot, list_snapshots, restore_snapshot, safe_checkpoint, take_snapshot
from vde_vlm.agent import execute_agent_step

__version__ = "1.0.0"
__all__ = [
    "VBoxVM",
    "find_vboxmanage",
    "list_vms",
    "list_running_vms",
    "get_vm_info",
    "get_vm_state",
    "is_vm_running",
    "run_vbox_cmd",
    "take_screenshot",
    "add_coordinate_grid",
    "compare_screenshots",
    "inspect_screen_state",
    "transcribe_screen",
    "press_key",
    "type_string",
    "parse_key_combo",
    "click",
    "move_to",
    "scroll",
    "run_guest_command",
    "copy_to_guest",
    "copy_from_guest",
    "take_snapshot",
    "restore_snapshot",
    "list_snapshots",
    "delete_snapshot",
    "safe_checkpoint",
    "execute_agent_step",
]
