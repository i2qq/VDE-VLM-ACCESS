"""
vde_vlm.snapshots
~~~~~~~~~~~~~~~~~
Safe snapshot management for VirtualBox VMs.
Enables creating checkpoints, rolling back, and safe transactional testing
with the `snapshot_context` context manager.
"""

from __future__ import annotations

import contextlib
import logging
import time
from typing import Any, Dict, List, Optional
from vde_vlm.vbox import run_vbox_cmd

logger = logging.getLogger(__name__)


def take_snapshot(
    vm_name_or_uuid: str,
    snapshot_name: str,
    description: Optional[str] = None,
) -> str:
    """Create a new snapshot of the VM.

    Args:
        vm_name_or_uuid: Target VM.
        snapshot_name: Name for the snapshot.
        description: Optional notes/description.

    Returns:
        Snapshot name.
    """
    args = ["snapshot", vm_name_or_uuid, "take", snapshot_name]
    if description:
        args.extend(["--description", description])

    run_vbox_cmd(*args, timeout=120.0)
    logger.info(f"Snapshot '{snapshot_name}' taken successfully for {vm_name_or_uuid}")
    return snapshot_name


def restore_snapshot(vm_name_or_uuid: str, snapshot_name_or_uuid: str) -> None:
    """Restore a VM to a named snapshot.

    Note: VM must be powered off before restoring a snapshot.

    Args:
        vm_name_or_uuid: Target VM.
        snapshot_name_or_uuid: Snapshot identifier.
    """
    run_vbox_cmd("snapshot", vm_name_or_uuid, "restore", snapshot_name_or_uuid, timeout=120.0)
    logger.info(f"Restored {vm_name_or_uuid} to snapshot '{snapshot_name_or_uuid}'")


def delete_snapshot(vm_name_or_uuid: str, snapshot_name_or_uuid: str) -> None:
    """Delete a snapshot."""
    run_vbox_cmd("snapshot", vm_name_or_uuid, "delete", snapshot_name_or_uuid, timeout=180.0)


def list_snapshots(vm_name_or_uuid: str) -> List[Dict[str, str]]:
    """List all snapshots of the VM.

    Returns:
        List of dicts with 'name' and 'uuid'.
    """
    code, stdout, _ = run_vbox_cmd("snapshot", vm_name_or_uuid, "list", "--machinereadable", check=False)
    if code != 0 or "does not have any snapshots" in stdout:
        return []

    snapshots: List[Dict[str, str]] = []
    # Machine-readable output format:
    # SnapshotName="name"
    # SnapshotUUID="uuid"
    current_name = None
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("SnapshotName"):
            _, val = line.split("=", 1)
            current_name = val.strip('"')
        elif line.startswith("SnapshotUUID") and current_name is not None:
            _, val = line.split("=", 1)
            uuid = val.strip('"')
            snapshots.append({"name": current_name, "uuid": uuid})
            current_name = None

    return snapshots


@contextlib.contextmanager
def safe_checkpoint(vm_name_or_uuid: str, checkpoint_name: Optional[str] = None):
    """Context manager that creates a temporary snapshot and rolls back if an error occurs.

    Usage:
        with safe_checkpoint("my_vm", "pre_test"):
            # run experimental changes
            # if exception is raised, VM is automatically restored to pre_test!
    """
    name = checkpoint_name or f"auto_ckpt_{int(time.time())}"
    take_snapshot(vm_name_or_uuid, name, description="Automated safety checkpoint")
    try:
        yield name
    except Exception as exc:
        logger.warning(f"Error during execution; rolling back to checkpoint '{name}': {exc}")
        # Import VM stop if VM is running
        from vde_vlm.vbox import is_vm_running, run_vbox_cmd
        if is_vm_running(vm_name_or_uuid):
            run_vbox_cmd("controlvm", vm_name_or_uuid, "poweroff", check=False)
            time.sleep(2.0)
        restore_snapshot(vm_name_or_uuid, name)
        raise
