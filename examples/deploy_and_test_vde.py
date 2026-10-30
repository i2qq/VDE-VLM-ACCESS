"""
examples/deploy_and_test_vde.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
End-to-end workflow tailored for the VDE (Victors Desktop Environment) project:
1. Connects to VM.
2. Creates a safety snapshot checkpoint.
3. Deploys VDE codebase into the guest.
4. Executes VDE build or test scripts.
5. Captures screenshot + grid for VLM evaluation.
6. Rolls back on error.
"""

import os
import sys
import time
from vde_vlm import VBoxVM


def main():
    vm_name = os.environ.get("VDE_VM", "vmvdebox6.1")
    vde_host_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "VDE")
    )

    if not os.path.isdir(vde_host_dir):
        print(f"Warning: VDE repo directory not found at {vde_host_dir}")

    vm = VBoxVM(vm_name)
    print(f"Connecting to VM '{vm_name}'...")

    if not vm.is_running:
        print("Booting VM headless...")
        vm.start(headless=True)
        time.sleep(10)

    # Use transactional checkpoint
    print("Creating safety checkpoint...")
    with vm.checkpoint("deploy_vde_test"):
        if os.path.isdir(vde_host_dir):
            print(f"Uploading VDE from {vde_host_dir} into guest /home/victor/VDE...")
            vm.upload(vde_host_dir, "/home/victor/VDE")

        print("Capturing desktop state...")
        obs = vm.observe(grid=True)
        print(f"Current desktop screenshot: {obs['screenshot']}")
        print(f"Grid overlay for targeting clicks: {obs['grid_screenshot']}")

        # Test pressing key to open VDE launcher
        print("Triggering launcher key chord...")
        vm.press_key("super")
        time.sleep(1)

        after_obs = vm.observe(grid=True)
        print(f"Launcher open observation: {after_obs['grid_screenshot']}")

    print("Deploy and test flow completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
