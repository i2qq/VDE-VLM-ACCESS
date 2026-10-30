"""
vde_vlm.guest
~~~~~~~~~~~~~
Guest OS execution and file management for VirtualBox VMs via guestcontrol.
Allows running shell commands inside the VM, copying files to/from the guest,
and checking Guest Additions status.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple
from vde_vlm.vbox import run_vbox_cmd, get_vm_info


def is_guest_additions_running(vm_name_or_uuid: str) -> bool:
    """Check if Guest Additions are active and reporting in the VM."""
    info = get_vm_info(vm_name_or_uuid)
    run_level = info.get("GuestAdditionsRunLevel", "0")
    try:
        return int(run_level) > 0
    except ValueError:
        return False


def run_guest_command(
    vm_name_or_uuid: str,
    command: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    cwd: Optional[str] = None,
    timeout: float = 60.0,
    check: bool = True,
) -> Tuple[int, str, str]:
    """Execute a shell command inside the Linux guest VM.

    Args:
        vm_name_or_uuid: Target VM.
        command: Command string to execute via bash.
        username: Guest user (defaults to env VDE_GUEST_USER or 'root' / current user).
        password: Guest password (defaults to env VDE_GUEST_PASS).
        cwd: Working directory inside the guest.
        timeout: Execution timeout in seconds.
        check: Whether to raise on non-zero exit code.

    Returns:
        Tuple of (returncode, stdout, stderr).
    """
    user = username or os.environ.get("VDE_GUEST_USER", "victor")
    pwd = password or os.environ.get("VDE_GUEST_PASS", "")

    args = [
        "guestcontrol",
        vm_name_or_uuid,
        "run",
        "--exe", "/bin/bash",
        "--username", user,
        "--wait-stdout",
        "--wait-stderr",
    ]

    if pwd:
        args.extend(["--password", pwd])
    else:
        args.extend(["--password", ""])

    if cwd:
        args.extend(["--cwd", cwd])

    args.extend(["--", "-c", command])

    return run_vbox_cmd(*args, timeout=timeout, check=check)


def copy_to_guest(
    vm_name_or_uuid: str,
    host_source: str,
    guest_target_dir: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    recursive: bool = True,
) -> None:
    """Copy a file or directory from host into the guest VM.

    Args:
        vm_name_or_uuid: Target VM.
        host_source: Host file or directory path.
        guest_target_dir: Target directory path inside the guest.
        username: Guest username.
        password: Guest password.
        recursive: Whether to copy directories recursively.
    """
    user = username or os.environ.get("VDE_GUEST_USER", "victor")
    pwd = password or os.environ.get("VDE_GUEST_PASS", "")

    abs_src = os.path.abspath(host_source)
    args = [
        "guestcontrol",
        vm_name_or_uuid,
        "copyto",
        "--username", user,
        "--target-directory", guest_target_dir,
    ]
    if pwd:
        args.extend(["--password", pwd])
    else:
        args.extend(["--password", ""])

    if recursive and os.path.isdir(abs_src):
        args.append("--recursive")

    args.append(abs_src)
    run_vbox_cmd(*args, timeout=120.0)


def copy_from_guest(
    vm_name_or_uuid: str,
    guest_source: str,
    host_target_dir: str,
    username: Optional[str] = None,
    password: Optional[str] = None,
    recursive: bool = True,
) -> None:
    """Copy a file or directory from the guest VM to the host.

    Args:
        vm_name_or_uuid: Target VM.
        guest_source: Source path inside guest.
        host_target_dir: Target directory on host.
        username: Guest username.
        password: Guest password.
        recursive: Whether to copy directories recursively.
    """
    user = username or os.environ.get("VDE_GUEST_USER", "victor")
    pwd = password or os.environ.get("VDE_GUEST_PASS", "")

    os.makedirs(host_target_dir, exist_ok=True)
    args = [
        "guestcontrol",
        vm_name_or_uuid,
        "copyfrom",
        "--username", user,
        "--target-directory", os.path.abspath(host_target_dir),
    ]
    if pwd:
        args.extend(["--password", pwd])
    else:
        args.extend(["--password", ""])

    if recursive:
        args.append("--recursive")

    args.append(guest_source)
    run_vbox_cmd(*args, timeout=120.0)
