"""
vde_vlm.agent
~~~~~~~~~~~~~
High-level perception-action loop for autonomous VLM agents.
Provides a structured `step()` interface that executes agent actions
and returns multimodal feedback (screen, diff, metrics).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional
from vde_vlm.core import VBoxVM
from vde_vlm.vision import compare_screenshots

logger = logging.getLogger(__name__)


def execute_agent_step(vm: VBoxVM, action: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a single structured agent action on the VM.

    Supported action dictionaries:
      - {"type": "observe"}
      - {"type": "click", "x": int, "y": int, "button": "left"|"right"|"middle", "double": bool}
      - {"type": "type", "text": str, "enter": bool}
      - {"type": "key", "key": str}  (e.g. "ctrl+alt+t", "super", "enter")
      - {"type": "exec", "cmd": str, "user": str, "password": str}
      - {"type": "wait", "seconds": float}

    Returns:
        Dict containing:
          - observation: current observe() dict
          - diff_ratio: visual change between before and after action
          - changed: bool indicating if screen changed
          - action_result: output of the specific action
    """
    action_type = action.get("type", "observe").lower()

    # Pre-action observation
    before_shot = vm.screenshot()
    action_result: Any = None

    if action_type == "observe":
        action_result = "observed"

    elif action_type == "click":
        x = int(action["x"])
        y = int(action["y"])
        button = action.get("button", "left")
        double = bool(action.get("double", False))
        action_result = vm.click(x, y, button=button, double=double)

    elif action_type == "type":
        text = str(action["text"])
        enter = bool(action.get("enter", False))
        vm.type(text, press_enter=enter)
        action_result = f"typed: {text} (enter={enter})"

    elif action_type == "key":
        key = str(action["key"])
        vm.press_key(key)
        action_result = f"pressed: {key}"

    elif action_type == "exec":
        cmd = str(action["cmd"])
        user = action.get("user")
        pwd = action.get("password")
        ret, stdout, stderr = vm.exec(cmd, username=user, password=pwd, check=False)
        action_result = {"returncode": ret, "stdout": stdout, "stderr": stderr}

    elif action_type == "wait":
        secs = float(action.get("seconds", 1.0))
        time.sleep(secs)
        action_result = f"waited {secs}s"

    else:
        raise ValueError(f"Unsupported action type: {action_type}")

    # Small delay for GUI to render state change
    time.sleep(action.get("post_delay", 0.5))

    # Post-action observation
    obs = vm.observe(grid=True)
    after_shot = obs["screenshot"]

    diff_ratio, changed = compare_screenshots(before_shot, after_shot)

    return {
        "action": action,
        "action_result": action_result,
        "changed": changed,
        "diff_ratio": round(diff_ratio, 4),
        "observation": obs,
    }
