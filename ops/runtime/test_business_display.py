import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("business_display", Path(__file__).with_name("verify-business-display.py"))
display = importlib.util.module_from_spec(spec)
spec.loader.exec_module(display)


class BusinessDisplayTests(unittest.TestCase):
    def setUp(self):
        self.names = [f"fixture-{i}" for i in range(6)]
        self.config = {"display": {"reply_footer": False}, "projects": [{"name": n} for n in self.names]}

    def test_all_six_and_no_configuration_mutation(self):
        before = copy.deepcopy(self.config)
        self.assertEqual(display.verify(self.config, self.names)["verified_environments"], 6)
        self.assertEqual(before, self.config)

    def test_project_overrides_cannot_hide_behind_global_false(self):
        self.config["projects"][4]["display"] = {"reply_footer": True}
        with self.assertRaises(ValueError):
            display.verify(self.config, self.names)
        self.config["projects"][4]["reply_footer"] = False
        display.verify(self.config, self.names)

    def test_missing_duplicate_and_default_enabled_rejected(self):
        for config in ({"projects": self.config["projects"]},
                       {"display": {"reply_footer": False}, "projects": self.config["projects"][:5]},
                       {"display": {"reply_footer": False}, "projects": self.config["projects"] * 2}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                display.verify(config, self.names)
        with self.assertRaises(ValueError):
            display.verify(self.config, self.names[:5])


if __name__ == "__main__":
    unittest.main()
