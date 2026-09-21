"""Fictional rehearsal consistency and packaging, not model acceptance."""
import csv
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).parents[1]
SKILL = ROOT / "ops/skills/team-banquet"


class BanquetSkillTests(unittest.TestCase):
    def test_references_resolve_and_demo_stays_explicit(self):
        for path in SKILL.rglob("*.md"):
            content = path.read_text(encoding="utf-8")
            for link in re.findall(r"\]\(([^)]+)\)", content):
                self.assertTrue((path.parent / link).is_file(), (path, link))
        entry = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("仅在员工明确要求虚构演练时", entry)
        for existing in ("team-files", "team-brain", "team-crm"):
            self.assertIn(existing, entry)
        policy = (ROOT / "ops/CLAUDE.vps.md").read_text(encoding="utf-8")
        self.assertIn(".claude/skills/team-banquet/SKILL.md", policy)

    def test_demo_has_consistent_counts_and_zero_denominator_case(self):
        with (SKILL / "references/fictional-leads.csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        totals = [0] * 5
        for row in rows:
            self.assertEqual("虚构演练", row["数据范围"])
            cost, leads, valid, visits, orders = [int(row[key]) for key in ("花费元", "线索", "有效线索", "到店", "成交")]
            self.assertTrue(0 <= orders <= visits <= valid <= leads)
            totals = [a + b for a, b in zip(totals, (cost, leads, valid, visits, orders))]
        self.assertEqual([10500, 110, 58, 26, 6], totals)
        self.assertTrue(any(row["有效线索"] == "0" for row in rows))

    def test_linked_team_identity_budget_and_capacity(self):
        data = json.loads((SKILL / "references/fictional-team.json").read_text(encoding="utf-8"))
        venue, customer, event = data["venue"], data["customer"], data["event"]
        self.assertEqual(("DEMO-TEAM-001", "1.0", "虚构演练"),
                         (data["source_id"], data["version"], data["data_scope"]))
        self.assertEqual((customer["id"], venue["id"]),
                         (event["customer_id"], event["venue_id"]))
        self.assertIsNone(event["selected_package"])
        self.assertEqual("待确认", venue["availability"])
        self.assertIsNone(venue["discount_rules"])
        self.assertIsNone(venue["deposit_and_cancellation_rules"])
        self.assertEqual(event["initial_people"], event["initial_tables"] * venue["people_per_table"])
        self.assertLessEqual(event["initial_tables"], venue["max_tables"])
        prices = {package["id"]: package["price_per_table_yuan"] for package in venue["packages"]}
        self.assertEqual({"A", "B"}, set(prices))
        for tables, expected in ((20, {"A": 81600, "B": 93600}),
                                 (22, {"A": 89560, "B": 102760})):
            totals = {key: tables * price + venue["fixed_service_fee_yuan"] for key, price in prices.items()}
            self.assertEqual(expected, totals)
        self.assertLess(89560, customer["budget_yuan"])
        self.assertEqual(2760, 102760 - customer["budget_yuan"])
        self.assertEqual(24, venue["max_tables"])
        self.assertGreater(26, venue["max_tables"])


if __name__ == "__main__":
    unittest.main()
