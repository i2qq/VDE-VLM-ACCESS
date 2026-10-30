"""
examples/basic_control.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Simple demonstration of booting a VM headless, capturing a screenshot,
and sending keypresses using VDE-VLM-ACCESS.
"""

import sys
import time
from vde_vlm import VBoxVM, list_vms


def main():
    vms = list_vms()
    if not vms:
        print("No VirtualBox VMs found on this system.")
        return 1

    target_vm_name = vms[0]["name"]
    print(f"Selected VM: {target_vm_name}")

    vm = VBoxVM(target_vm_name)
    print(f"Initial state: {vm.state}")

    if not vm.is_running:
        print("Starting VM in headless mode...")
        vm.start(headless=True)
        print("VM started. Waiting 5s for boot...")
        time.sleep(5)

    # Observe screen with coordinate grid overlay
    obs = vm.observe(grid=True)
    print(f"Screenshot taken: {obs['screenshot']}")
    print(f"Grid overlay image: {obs['grid_screenshot']}")
    print(f"Resolution: {obs['resolution'][0]}x{obs['resolution'][1]}")

    # Press Enter or Super
    print("Sending Enter key to VM...")
    vm.press_key("enter")

    time.sleep(2)
    new_obs = vm.observe()
    print(f"Updated screenshot: {new_obs['screenshot']}")

    print("Demo completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
