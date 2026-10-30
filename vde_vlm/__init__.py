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
    clean_temp_artifacts,
    compare_screenshots,
    draw_agent_cursor,
    get_cache_dir,
    get_rolling_screen_path,
    inspect_screen_state,
    take_screenshot,
    transcribe_screen,
)
from vde_vlm.keyboard import parse_key_combo, press_key, type_string
from vde_vlm.mouse import click, move_to, scroll
from vde_vlm.guest import copy_from_guest, copy_to_guest, run_guest_command
from vde_vlm.snapshots import delete_snapshot, list_snapshots, restore_snapshot, safe_checkpoint, take_snapshot
from vde_vlm.agent import execute_agent_step
from vde_vlm.macro import MacroStep, execute_batch
from vde_vlm.web_viewer import run_web_viewer

__version__ = "2.0.0"
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
    "draw_agent_cursor",
    "compare_screenshots",
    "inspect_screen_state",
    "transcribe_screen",
    "clean_temp_artifacts",
    "get_cache_dir",
    "get_rolling_screen_path",
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
    "MacroStep",
    "execute_batch",
    "run_web_viewer",
]
