"""
vde_vlm.macro
~~~~~~~~~~~~~
Compound batch execution system for VDE-VLM.
Allows agents and users to execute multi-step interaction plans (type, click,
chords, waits) in a single atomic turn instead of separate round-trips.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class MacroStep:
    """Represents a single atomic action within a compound sequence."""

    def __init__(self, action_type: str, **kwargs: Any):
        self.type = action_type.lower().strip()
        self.params = kwargs

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MacroStep:
        d = dict(data)
        action_type = d.pop("type", "wait")
        return cls(action_type, **d)

    @classmethod
    def parse_shorthand(cls, item: str) -> MacroStep:
        """Parse concise string notation.

        Examples:
            'type:hello|enter' -> type 'hello' and press enter
            'type:echo hi'     -> type 'echo hi'
            'click:450,720'    -> click at x=450, y=720
            'rclick:450,720'   -> right click
            'dclick:450,720'   -> double click
            'key:super'        -> press super key
            'key:ctrl+alt+t'   -> press ctrl+alt+t
            'wait:1.5'         -> wait 1.5 seconds
            'exec:ls -la'      -> run guest shell command
        """
        item = item.strip()
        if ":" not in item:
            return cls("wait", seconds=1.0)

        kind, rest = item.split(":", 1)
        kind = kind.lower().strip()
        rest = rest.strip()

        if kind == "type":
            press_enter = False
            if rest.endswith("|enter"):
                press_enter = True
                rest = rest[:-6]
            return cls("type", text=rest, enter=press_enter)

        elif kind in ("click", "lclick"):
            x_str, y_str = rest.split(",", 1)
            return cls("click", x=int(x_str.strip()), y=int(y_str.strip()), button="left")

        elif kind == "rclick":
            x_str, y_str = rest.split(",", 1)
            return cls("click", x=int(x_str.strip()), y=int(y_str.strip()), button="right")

        elif kind == "dclick":
            x_str, y_str = rest.split(",", 1)
            return cls("click", x=int(x_str.strip()), y=int(y_str.strip()), button="left", double=True)

        elif kind in ("key", "chord"):
            return cls("key", chord=rest)

        elif kind in ("wait", "sleep"):
            return cls("wait", seconds=float(rest))

        elif kind == "exec":
            return cls("exec", cmd=rest)

        raise ValueError(f"Unknown shorthand macro step: {item}")


def execute_batch(
    vm: Any,
    steps: List[Union[Dict[str, Any], MacroStep, str]],
    verify_final_change: bool = True,
) -> Dict[str, Any]:
    """Execute a sequence of actions on the VM in one continuous flow.

    Args:
        vm: VBoxVM instance.
        steps: List of dicts, MacroStep instances, or shorthand strings.
        verify_final_change: Compare screen before vs after the whole batch.

    Returns:
        Dict with execution summary, step count, elapsed time, and observation.
    """
    parsed_steps: List[MacroStep] = []
    for s in steps:
        if isinstance(s, MacroStep):
            parsed_steps.append(s)
        elif isinstance(s, dict):
            parsed_steps.append(MacroStep.from_dict(s))
        elif isinstance(s, str):
            parsed_steps.append(MacroStep.parse_shorthand(s))

    before_shot = None
    if verify_final_change and vm.is_running:
        before_shot = vm.screenshot()

    start_time = time.time()
    results: List[Dict[str, Any]] = []

    for idx, step in enumerate(parsed_steps):
        step_res: Dict[str, Any] = {"step_index": idx, "type": step.type}

        try:
            if step.type == "type":
                text = step.params.get("text", "")
                enter = bool(step.params.get("enter", False))
                vm.type(text, press_enter=enter)
                step_res["status"] = "ok"
                step_res["details"] = f"typed '{text}' (enter={enter})"

            elif step.type == "click":
                x = int(step.params["x"])
                y = int(step.params["y"])
                button = step.params.get("button", "left")
                double = bool(step.params.get("double", False))
                # Broadcast agent cursor to live UI listeners if present
                if hasattr(vm, "notify_agent_cursor"):
                    vm.notify_agent_cursor(x, y, is_click=True)
                res = vm.click(x, y, button=button, double=double)
                step_res["status"] = "ok"
                step_res["details"] = res

            elif step.type == "key":
                chord = step.params.get("chord") or step.params.get("key", "")
                vm.press_key(chord)
                step_res["status"] = "ok"
                step_res["details"] = f"pressed '{chord}'"

            elif step.type == "wait":
                secs = float(step.params.get("seconds", 1.0))
                time.sleep(secs)
                step_res["status"] = "ok"
                step_res["details"] = f"waited {secs}s"

            elif step.type == "exec":
                cmd = step.params.get("cmd", "")
                user = step.params.get("user")
                pwd = step.params.get("password")
                code, stdout, stderr = vm.exec(cmd, username=user, password=pwd, check=False)
                step_res["status"] = "ok" if code == 0 else "failed"
                step_res["details"] = {"exit_code": code, "stdout": stdout, "stderr": stderr}

            else:
                step_res["status"] = "unknown_action"
                step_res["details"] = f"Action {step.type} not recognized"

        except Exception as exc:
            logger.exception(f"Error on macro step {idx} ({step.type})")
            step_res["status"] = "error"
            step_res["error"] = str(exc)
            results.append(step_res)
            break

        results.append(step_res)
        # Small default pacing between compound actions (50ms)
        pacing = float(step.params.get("pacing", 0.05))
        if pacing > 0:
            time.sleep(pacing)

    total_time = round(time.time() - start_time, 3)

    # Post observation
    obs = None
    changed = False
    diff_ratio = 0.0
    if vm.is_running:
        obs = vm.observe(grid=False)
        if before_shot and obs.get("screenshot"):
            from vde_vlm.vision import compare_screenshots
            diff_ratio, changed = compare_screenshots(before_shot, obs["screenshot"])

    return {
        "success": all(r.get("status") == "ok" for r in results),
        "total_steps": len(parsed_steps),
        "executed_steps": len(results),
        "elapsed_seconds": total_time,
        "changed": changed,
        "diff_ratio": round(diff_ratio, 4),
        "step_results": results,
        "observation": obs,
    }
