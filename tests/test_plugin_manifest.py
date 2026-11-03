import os
import json
import unittest

class TestPluginManifest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.plugin_path = os.path.join(cls.repo_root, "plugin.json")
        cls.rules_path = os.path.join(cls.repo_root, "rules", "AGENTS.md")

    def test_plugin_json_exists_and_valid(self):
        self.assertTrue(os.path.exists(self.plugin_path), "plugin.json must exist at project root")
        with open(self.plugin_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("name"), "mobile-remote-control")
        self.assertEqual(data.get("version"), "0.1.0")
        self.assertIn("displayName", data)
        self.assertIn("description", data)
        self.assertIn("license", data)

    def test_rules_agents_md_exists(self):
        self.assertTrue(os.path.exists(self.rules_path), "rules/AGENTS.md must exist in plugin")
        with open(self.rules_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertTrue("Mobile Remote Control" in content or "MRC" in content)
        self.assertTrue("hands-free" in content.lower() or "handsfree" in content.lower())
