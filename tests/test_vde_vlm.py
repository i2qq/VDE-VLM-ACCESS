"""
tests/test_vde_vlm.py
~~~~~~~~~~~~~~~~~~~~~
Unit tests for VDE-VLM-ACCESS core modules, compound macros, and visual overlays.
"""

import os
import sys
import tempfile
import unittest

# Ensure repo root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from PIL import Image

from vde_vlm.keyboard import parse_key_combo, SCANCODE_MAP
from vde_vlm.macro import MacroStep
from vde_vlm.vbox import find_vboxmanage, list_vms
from vde_vlm.vision import (
    add_coordinate_grid,
    clean_temp_artifacts,
    compare_screenshots,
    draw_agent_cursor,
    inspect_screen_state,
)
from vde_vlm.core import VBoxVM


class TestKeyboardScancodes(unittest.TestCase):
    def test_single_key(self):
        makes, breaks = parse_key_combo("enter")
        self.assertEqual(makes, ["1c"])
        self.assertEqual(breaks, ["9c"])

    def test_chord_combo(self):
        # ctrl+alt+t
        makes, breaks = parse_key_combo("ctrl+alt+t")
        self.assertEqual(makes, ["1d", "38", "14"])
        # Breaks in reverse: 't', 'alt', 'ctrl'
        self.assertEqual(breaks, ["94", "b8", "9d"])

    def test_super_key(self):
        makes, breaks = parse_key_combo("super")
        self.assertEqual(makes, ["e0", "5b"])
        self.assertEqual(breaks, ["e0", "db"])

    def test_unknown_key(self):
        with self.assertRaises(ValueError):
            parse_key_combo("nonexistentkey")


class TestMacroShorthand(unittest.TestCase):
    def test_type_shorthand(self):
        s = MacroStep.parse_shorthand("type:echo 'hello world'|enter")
        self.assertEqual(s.type, "type")
        self.assertEqual(s.params["text"], "echo 'hello world'")
        self.assertTrue(s.params["enter"])

    def test_click_shorthand(self):
        s = MacroStep.parse_shorthand("click:450,720")
        self.assertEqual(s.type, "click")
        self.assertEqual(s.params["x"], 450)
        self.assertEqual(s.params["y"], 720)
        self.assertEqual(s.params["button"], "left")

    def test_key_shorthand(self):
        s = MacroStep.parse_shorthand("key:ctrl+alt+t")
        self.assertEqual(s.type, "key")
        self.assertEqual(s.params["chord"], "ctrl+alt+t")

    def test_wait_shorthand(self):
        s = MacroStep.parse_shorthand("wait:1.5")
        self.assertEqual(s.type, "wait")
        self.assertEqual(s.params["seconds"], 1.5)


class TestVBoxDiscovery(unittest.TestCase):
    def test_find_vboxmanage(self):
        path = find_vboxmanage()
        self.assertTrue(os.path.isfile(path), f"VBoxManage not found at {path}")

    def test_list_vms(self):
        vms = list_vms()
        self.assertIsInstance(vms, list)
        self.assertGreater(len(vms), 0, "Expected at least 1 VM on host")
        names = [v["name"] for v in vms]
        self.assertTrue(any("vmvde" in n for n in names))


class TestVisionOverlay(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_img_path = os.path.join(self.test_dir, "test_base.png")
        img = Image.new("RGB", (800, 600), color=(50, 50, 150))
        img.save(self.test_img_path)

    def tearDown(self):
        for f in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, f))
        os.rmdir(self.test_dir)

    def test_stitch_grid_overlay(self):
        grid_path = add_coordinate_grid(self.test_img_path, grid_step=100, style="stitch")
        self.assertTrue(os.path.isfile(grid_path))
        with Image.open(grid_path) as out:
            self.assertEqual(out.size, (800, 600))

    def test_agent_cursor_drawing(self):
        cursor_path = draw_agent_cursor(self.test_img_path, 450, 300, label="Gemini", is_click=True)
        self.assertTrue(os.path.isfile(cursor_path))
        with Image.open(cursor_path) as out:
            self.assertEqual(out.size, (800, 600))

    def test_compare_screenshots(self):
        diff, changed = compare_screenshots(self.test_img_path, self.test_img_path)
        self.assertEqual(diff, 0.0)
        self.assertFalse(changed)

        other_path = os.path.join(self.test_dir, "test_other.png")
        img2 = Image.new("RGB", (800, 600), color=(250, 250, 250))
        img2.save(other_path)
        diff2, changed2 = compare_screenshots(self.test_img_path, other_path)
        self.assertGreater(diff2, 0.5)
        self.assertTrue(changed2)

    def test_inspect_screen_state(self):
        metrics = inspect_screen_state(self.test_img_path)
        self.assertEqual(metrics["width"], 800)
        self.assertEqual(metrics["height"], 600)
        self.assertFalse(metrics["is_all_black"])

    def test_clean_artifacts(self):
        cleaned = clean_temp_artifacts()
        self.assertIsInstance(cleaned, int)


class TestCoreVM(unittest.TestCase):
    def test_vm_instantiation(self):
        vms = list_vms()
        if not vms:
            return
        target = vms[0]["name"]
        vm = VBoxVM(target)
        self.assertEqual(vm.name, target)
        self.assertIn(vm.state, ["running", "poweroff", "saved", "paused"])


if __name__ == "__main__":
    unittest.main()
