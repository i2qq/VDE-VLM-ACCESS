"""
vde_vlm.cli
~~~~~~~~~~~
Command-Line Interface for VDE-VLM-ACCESS.
Enables agents and developers to interact with VirtualBox VMs directly via terminal,
launch the collaborative live studio, and execute compound macro sequences.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from vde_vlm.core import VBoxVM
from vde_vlm.macro import execute_batch
from vde_vlm.vbox import list_vms
from vde_vlm.vision import clean_temp_artifacts


def main(args: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vde-vlm",
        description="VDE-VLM-ACCESS: VirtualBox interaction toolkit for Vision-Language Models & autonomous agents.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # list
    subparsers.add_parser("list", help="List all registered VirtualBox VMs and their states")

    # info
    p_info = subparsers.add_parser("info", help="Display details for a VM")
    p_info.add_argument("vm", help="VM name or UUID")

    # start
    p_start = subparsers.add_parser("start", help="Power on a VM")
    p_start.add_argument("vm", help="VM name or UUID")
    p_start.add_argument("--gui", action="store_true", help="Launch with desktop window (default is headless)")

    # stop
    p_stop = subparsers.add_parser("stop", help="Power off or save state of a VM")
    p_stop.add_argument("vm", help="VM name or UUID")
    p_stop.add_argument(
        "--mode",
        choices=["poweroff", "savestate", "acpipowerbutton", "pause", "resume", "reset"],
        default="poweroff",
        help="Shutdown mode (default: poweroff)",
    )

    # screenshot
    p_shot = subparsers.add_parser("screenshot", help="Capture a screenshot of the VM")
    p_shot.add_argument("vm", help="VM name or UUID")
    p_shot.add_argument("-o", "--output", help="Output file path (default: rolling cache)")
    p_shot.add_argument("--grid", action="store_true", help="Include subtle coordinate grid overlay")
    p_shot.add_argument("--step", type=int, default=100, help="Grid step size in pixels (default: 100)")

    # observe
    p_obs = subparsers.add_parser("observe", help="Full multimodal observation (screen, grid, resolution, state)")
    p_obs.add_argument("vm", help="VM name or UUID")
    p_obs.add_argument("--no-grid", action="store_true", help="Omit coordinate grid overlay")
    p_obs.add_argument("--ocr", action="store_true", help="Attempt OCR transcription of screen")
    p_obs.add_argument("--json", action="store_true", help="Output strictly JSON")

    # click
    p_click = subparsers.add_parser("click", help="Simulate a mouse click at (x, y)")
    p_click.add_argument("vm", help="VM name or UUID")
    p_click.add_argument("x", type=int, help="X pixel coordinate")
    p_click.add_argument("y", type=int, help="Y pixel coordinate")
    p_click.add_argument("--button", choices=["left", "right", "middle"], default="left")
    p_click.add_argument("--double", action="store_true", help="Double click")
    p_click.add_argument("--verify", action="store_true", help="Verify if screen changed after click")

    # type
    p_type = subparsers.add_parser("type", help="Type text into the active VM window")
    p_type.add_argument("vm", help="VM name or UUID")
    p_type.add_argument("text", help="Text to type")
    p_type.add_argument("--enter", action="store_true", help="Press Enter after typing")

    # key
    p_key = subparsers.add_parser("key", help="Send a keypress or chord (e.g. 'ctrl+alt+t', 'super', 'enter')")
    p_key.add_argument("vm", help="VM name or UUID")
    p_key.add_argument("chord", help="Key or chord to press")

    # macro / batch
    p_macro = subparsers.add_parser("macro", help="Execute compound sequence of actions in one atomic turn")
    p_macro.add_argument("vm", help="VM name or UUID")
    p_macro.add_argument("steps", nargs="+", help="Shorthand actions (e.g. 'type:hello|enter' 'wait:0.5' 'click:450,720')")

    p_batch = subparsers.add_parser("batch", help="Execute compound batch from JSON file or string")
    p_batch.add_argument("vm", help="VM name or UUID")
    p_batch.add_argument("json_data", help="JSON string or path to JSON file containing action steps")

    # live studio
    p_live = subparsers.add_parser("live", help="Launch the Google Stitch-style collaborative web viewer (Port 7891)")
    p_live.add_argument("--port", type=int, default=7891, help="Web server port (default: 7891)")
    p_live.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")

    # exec
    p_exec = subparsers.add_parser("exec", help="Run a bash command inside the guest VM")
    p_exec.add_argument("vm", help="VM name or UUID")
    p_exec.add_argument("cmd", help="Command string to run")
    p_exec.add_argument("-u", "--user", default="victor", help="Guest username (default: victor)")
    p_exec.add_argument("-p", "--password", default="", help="Guest password")

    # upload / download
    p_up = subparsers.add_parser("upload", help="Copy a host file/directory into the guest VM")
    p_up.add_argument("vm", help="VM name or UUID")
    p_up.add_argument("host_src", help="Host path")
    p_up.add_argument("guest_dest", help="Destination path inside guest")
    p_up.add_argument("-u", "--user", default="victor")
    p_up.add_argument("-p", "--password", default="")

    p_down = subparsers.add_parser("download", help="Copy a guest file/directory to the host")
    p_down.add_argument("vm", help="VM name or UUID")
    p_down.add_argument("guest_src", help="Guest source path")
    p_down.add_argument("host_dest", help="Host destination directory")
    p_down.add_argument("-u", "--user", default="victor")
    p_down.add_argument("-p", "--password", default="")

    # snapshot
    p_snap = subparsers.add_parser("snapshot", help="Manage VM snapshots")
    p_snap.add_argument("vm", help="VM name or UUID")
    p_snap.add_argument("action", choices=["take", "restore", "list", "delete"], help="Snapshot action")
    p_snap.add_argument("name", nargs="?", help="Snapshot name")
    p_snap.add_argument("-d", "--desc", help="Snapshot description")

    # clean
    subparsers.add_parser("clean", help="Clean up stale temporary screenshot files from system temp")

    # serve (MCP)
    subparsers.add_parser("serve", help="Run the MCP stdio tool server")

    parsed = parser.parse_args(args)
    if not parsed.command:
        parser.print_help()
        return 0

    try:
        if parsed.command == "list":
            vms = list_vms()
            if not vms:
                print("No VirtualBox VMs registered.")
                return 0
            print(f"{'VM Name':<30} {'State':<15} {'UUID'}")
            print("-" * 75)
            for m in vms:
                vm = VBoxVM(m["name"])
                print(f"{m['name']:<30} {vm.state:<15} {m['uuid']}")
            return 0

        elif parsed.command == "clean":
            cleaned = clean_temp_artifacts()
            print(f"Cleaned {cleaned} temporary files from disk.")
            return 0

        elif parsed.command == "live":
            from vde_vlm.web_viewer import run_web_viewer
            run_web_viewer(host=parsed.host, port=parsed.port)
            return 0

        elif parsed.command == "serve":
            from vde_vlm.server import run_stdio_server
            run_stdio_server()
            return 0

        vm = VBoxVM(parsed.vm)

        if parsed.command == "info":
            info = vm.info
            for k in sorted(info.keys()):
                print(f"{k}: {info[k]}")

        elif parsed.command == "start":
            headless = not parsed.gui
            print(f"Starting VM '{parsed.vm}' ({'headless' if headless else 'GUI'})...")
            vm.start(headless=headless)
            print(f"State: {vm.state}")

        elif parsed.command == "stop":
            print(f"Stopping VM '{parsed.vm}' (mode: {parsed.mode})...")
            vm.stop(mode=parsed.mode)
            print(f"State: {vm.state}")

        elif parsed.command == "screenshot":
            out = vm.screenshot(output_path=parsed.output, with_grid=parsed.grid, grid_step=parsed.step)
            print(f"Screenshot saved to: {out}")

        elif parsed.command == "observe":
            obs = vm.observe(grid=not parsed.no_grid, ocr=parsed.ocr)
            if parsed.json:
                print(json.dumps(obs, indent=2))
            else:
                print(f"VM: {obs['vm']}")
                print(f"State: {obs['state']} (running={obs['is_running']})")
                print(f"Resolution: {obs['resolution'][0]}x{obs['resolution'][1]}")
                print(f"Brightness: {obs['average_brightness']} (all_black={obs['is_all_black']})")
                print(f"Screenshot: {obs['screenshot']}")
                if obs.get("grid_screenshot"):
                    print(f"Grid Overlay: {obs['grid_screenshot']}")
                if obs.get("ocr", {}).get("available"):
                    print(f"OCR Text:\n{obs['ocr'].get('text', '')}")

        elif parsed.command == "click":
            res = vm.click(parsed.x, parsed.y, button=parsed.button, double=parsed.double, verify_change=parsed.verify)
            print(json.dumps(res, indent=2))

        elif parsed.command == "type":
            vm.type(parsed.text, press_enter=parsed.enter)
            print(f"Typed: {parsed.text} (enter={parsed.enter})")

        elif parsed.command == "key":
            vm.press_key(parsed.chord)
            print(f"Pressed chord: {parsed.chord}")

        elif parsed.command == "macro":
            res = vm.macro(*parsed.steps)
            print(json.dumps(res, indent=2))

        elif parsed.command == "batch":
            if os.path.isfile(parsed.json_data):
                with open(parsed.json_data, "r", encoding="utf-8") as f:
                    steps = json.load(f)
            else:
                steps = json.loads(parsed.json_data)
            res = vm.batch(steps)
            print(json.dumps(res, indent=2))

        elif parsed.command == "exec":
            code, stdout, stderr = vm.exec(parsed.cmd, username=parsed.user, password=parsed.password, check=False)
            if stdout:
                print(stdout, end="")
            if stderr:
                sys.stderr.write(stderr)
            return code

        elif parsed.command == "upload":
            vm.upload(parsed.host_src, parsed.guest_dest, username=parsed.user, password=parsed.password)
            print(f"Uploaded {parsed.host_src} -> {parsed.guest_dest}")

        elif parsed.command == "download":
            vm.download(parsed.guest_src, parsed.host_dest, username=parsed.user, password=parsed.password)
            print(f"Downloaded {parsed.guest_src} -> {parsed.host_dest}")

        elif parsed.command == "snapshot":
            if parsed.action == "list":
                snaps = vm.list_snapshots()
                if not snaps:
                    print(f"Machine '{parsed.vm}' has no snapshots.")
                else:
                    for s in snaps:
                        print(f"- {s['name']} ({s['uuid']})")
            elif parsed.action == "take":
                if not parsed.name:
                    print("Error: snapshot name required for 'take'", file=sys.stderr)
                    return 1
                vm.snapshot(parsed.name, description=parsed.desc)
                print(f"Snapshot '{parsed.name}' created.")
            elif parsed.action == "restore":
                if not parsed.name:
                    print("Error: snapshot name required for 'restore'", file=sys.stderr)
                    return 1
                print(f"Restoring snapshot '{parsed.name}'...")
                vm.restore(parsed.name)
                print(f"Snapshot '{parsed.name}' restored.")
            elif parsed.action == "delete":
                if not parsed.name:
                    print("Error: snapshot name required for 'delete'", file=sys.stderr)
                    return 1
                from vde_vlm.snapshots import delete_snapshot
                delete_snapshot(parsed.vm, parsed.name)
                print(f"Snapshot '{parsed.name}' deleted.")

        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
