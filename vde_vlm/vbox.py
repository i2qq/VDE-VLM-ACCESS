"""
vde_vlm.vbox
~~~~~~~~~~~~
Low-level wrapper for Oracle VirtualBox CLI (VBoxManage).
Handles cross-platform discovery, subprocess execution, error handling,
and machine info parsing.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple


def find_vboxmanage() -> str:
    """Find the path to the VBoxManage executable."""
    env_vbox = os.environ.get("VBOX_MANAGE_PATH")
    if env_vbox and os.path.isfile(env_vbox):
        return env_vbox

    # Check PATH first
    which_path = shutil.which("VBoxManage") or shutil.which("VBoxManage.exe")
    if which_path and os.path.isfile(which_path):
        return which_path

    system = platform.system()
    if system == "Windows":
        candidates = [
            r"C:\Program Files\Oracle\VirtualBox\VBoxManage.exe",
            r"C:\Program Files (x86)\Oracle\VirtualBox\VBoxManage.exe",
        ]
        # Check standard environment variables
        for env_var in ["VBOX_MSI_INSTALL_PATH", "VBOX_INSTALL_PATH"]:
            val = os.environ.get(env_var)
            if val:
                candidates.insert(0, os.path.join(val, "VBoxManage.exe"))

        for path in candidates:
            if os.path.isfile(path):
                return path

    elif system == "Darwin":  # macOS
        candidates = [
            "/usr/local/bin/VBoxManage",
            "/Applications/VirtualBox.app/Contents/MacOS/VBoxManage",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path

    elif system == "Linux":
        candidates = [
            "/usr/bin/VBoxManage",
            "/usr/local/bin/VBoxManage",
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path

    raise FileNotFoundError(
        "VBoxManage executable could not be found. Please ensure Oracle VirtualBox "
        "is installed and added to your PATH or set VBOX_MANAGE_PATH."
    )


class VBoxExecutionError(RuntimeError):
    """Raised when a VBoxManage command fails."""

    def __init__(self, cmd: List[str], returncode: int, stdout: str, stderr: str):
        self.cmd = cmd
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        msg = f"VBoxManage error (exit code {returncode}): {stderr.strip() or stdout.strip()}"
        super().__init__(msg)


def run_vbox_cmd(
    *args: str,
    timeout: Optional[float] = 60.0,
    check: bool = True,
) -> Tuple[int, str, str]:
    """Execute a VBoxManage command.

    Args:
        *args: Subcommand and flags for VBoxManage.
        timeout: Execution timeout in seconds.
        check: If True, raises VBoxExecutionError on non-zero exit code.

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    vbox_path = find_vboxmanage()
    cmd = [vbox_path] + list(args)

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"Command '{' '.join(cmd)}' timed out after {timeout}s") from exc

    if check and proc.returncode != 0:
        raise VBoxExecutionError(cmd, proc.returncode, proc.stdout, proc.stderr)

    return proc.returncode, proc.stdout, proc.stderr


def list_vms() -> List[Dict[str, str]]:
    """List all registered virtual machines.

    Returns:
        List of dicts with 'name' and 'uuid'.
    """
    _, stdout, _ = run_vbox_cmd("list", "vms")
    vms = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # Expected format: "Name" {uuid}
        if line.startswith('"') and '" {' in line and line.endswith("}"):
            name_part, uuid_part = line.split('" {', 1)
            name = name_part[1:]  # strip leading quote
            uuid = uuid_part[:-1]  # strip trailing bracket
            vms.append({"name": name, "uuid": uuid})
    return vms


def list_running_vms() -> List[Dict[str, str]]:
    """List currently running virtual machines.

    Returns:
        List of dicts with 'name' and 'uuid'.
    """
    _, stdout, _ = run_vbox_cmd("list", "runningvms")
    vms = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith('"') and '" {' in line and line.endswith("}"):
            name_part, uuid_part = line.split('" {', 1)
            name = name_part[1:]
            uuid = uuid_part[:-1]
            vms.append({"name": name, "uuid": uuid})
    return vms


def get_vm_info(vm_name_or_uuid: str) -> Dict[str, Any]:
    """Retrieve machine information in machine-readable format.

    Args:
        vm_name_or_uuid: VM name or UUID.

    Returns:
        Dictionary of key-value properties.
    """
    _, stdout, _ = run_vbox_cmd("showvminfo", vm_name_or_uuid, "--machinereadable")
    info: Dict[str, Any] = {}
    for line in stdout.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if val.startswith('"') and val.endswith('"'):
            val = val[1:-1]
        info[key] = val
    return info


def get_vm_state(vm_name_or_uuid: str) -> str:
    """Get the current state of a VM (e.g. 'running', 'poweroff', 'saved', 'paused')."""
    info = get_vm_info(vm_name_or_uuid)
    return info.get("VMState", "unknown")


def is_vm_running(vm_name_or_uuid: str) -> bool:
    """Return True if the specified VM is currently running."""
    state = get_vm_state(vm_name_or_uuid)
    return state.lower() == "running"
