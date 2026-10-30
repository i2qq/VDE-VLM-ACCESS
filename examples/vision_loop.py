"""
examples/vision_loop.py
~~~~~~~~~~~~~~~~~~~~~~~
Demonstration of an autonomous perception-action loop where an agent
takes an action and evaluates the visual difference.
"""

import sys
import time
from vde_vlm import VBoxVM, execute_agent_step


def main():
    vm_name = "vmvdebox6.1"
    vm = VBoxVM(vm_name)

    if not vm.is_running:
        print(f"Starting {vm_name}...")
        vm.start(headless=True)
        time.sleep(3)

    print("Step 1: Observing initial state...")
    step1 = execute_agent_step(vm, {"type": "observe"})
    print(f"Observation: {step1['observation']['screenshot']}")

    print("Step 2: Pressing Super key (to toggle start menu)...")
    step2 = execute_agent_step(vm, {"type": "key", "key": "super"})
    print(f"Screen changed: {step2['changed']}, diff ratio: {step2['diff_ratio']}")
    print(f"Grid overlay for targeting clicks: {step2['observation']['grid_screenshot']}")

    print("Perception loop verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
