"""Fictional rehearsal consistency and packaging, not model acceptance."""
import csv
from datetime import datetime, timedelta
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

    def test_business_materials_are_linked_and_future_events_stay_outside_skill(self):
        rules = json.loads((SKILL / "references/fictional-business.json").read_text(encoding="utf-8"))
        case = json.loads((ROOT / "tests/fixtures/banquet_business_journey.json").read_text(encoding="utf-8"))
        self.assertEqual((rules["source_id"], rules["version"]), (case["rules_source"], case["rules_version"]))
        self.assertEqual(rules["venue"]["id"], case["venue_id"])
        self.assertEqual("虚构演练", case["data_scope"])
        materials = case["materials"]
        self.assertEqual(5, len({m["source_id"] for m in materials}))
        self.assertEqual(sorted(m["as_of"] for m in materials), [m["as_of"] for m in materials])
        self.assertTrue(all(m["as_of"] < case["event_date"] for m in materials[:-1]))
        self.assertGreater(materials[-1]["as_of"], case["event_date"])
        runtime = "\n".join(p.read_text(encoding="utf-8") for p in SKILL.rglob("*") if p.is_file())
        for private_future_fact in ("DEMO-ORDER-B", "DEMO-RECEIPT-B-01", "DEMO-ACCESS-B", "DEMO-WINE-B"):
            self.assertNotIn(private_future_fact, runtime)
        self.assertEqual({"提出要求", "已确认", "已发生", "待核实"}, set(rules["status_meanings"]))

    def test_business_costs_receipts_and_returns_reconcile(self):
        rules = json.loads((SKILL / "references/fictional-business.json").read_text(encoding="utf-8"))
        case = json.loads((ROOT / "tests/fixtures/banquet_business_journey.json").read_text(encoding="utf-8"))
        prices = rules["prices"]
        def total(tables, package="A", decoration="basic"):
            return (tables * prices["packages_per_table_yuan"][package]
                    + tables * prices["wine_bottles_per_table"] * prices["wine_price_per_bottle_yuan"]
                    + prices["fixed_service_fee_yuan"] + prices["host_yuan"]
                    + prices["decoration_yuan"][decoration])
        self.assertEqual((101520, 107520, 114720), (total(22), total(22, decoration="upgraded"), total(22, "B")))
        self.assertEqual(4720, total(22, "B") - case["materials"][0]["facts"]["预算元"])
        self.assertEqual(105680, total(23))
        self.assertEqual(108180, total(23) + prices["led_optional_yuan"])
        end = case["materials"][-1]
        receipts = case["materials"][1]["receipts"] + end["receipts"]
        by_id = {r["id"]: r for r in receipts}
        self.assertEqual(2, len(by_id))
        self.assertTrue(all(r == by_id[r["id"]] for r in receipts))
        received = sum(r["amount_yuan"] for r in by_id.values() if r["status"] == "已核验")
        final = total(23) - end["returned_wine_bottles"] * prices["wine_price_per_bottle_yuan"]
        self.assertEqual((105380, 80000, 25380), (final, received, final - received))
        claim = end["unverified_receipt"]
        self.assertIsNone(claim["proof"])
        self.assertEqual("待核实", claim["status"])
        self.assertEqual(5380, final - received - claim["amount_yuan"])
        self.assertLessEqual(23, rules["venue"]["max_tables"])

    def test_business_timing_includes_sequential_inspection(self):
        rules = json.loads((SKILL / "references/fictional-business.json").read_text(encoding="utf-8"))["venue"]
        clock = lambda value: datetime.strptime(value, "%H:%M")
        self.assertTrue(rules["inspection_after_setup"])
        duration = timedelta(minutes=rules["setup_minutes"] + rules["inspection_minutes"])
        self.assertEqual(clock("11:30") - timedelta(minutes=rules["inspection_buffer_before_reception_minutes"]),
                         clock(rules["earliest_access"]) + duration)
        cutoff = clock("10:30") - timedelta(minutes=rules["inspection_buffer_before_reception_minutes"])
        self.assertGreater(clock(rules["earliest_access"]) + duration, cutoff)
        setup_done = clock("08:00") + timedelta(minutes=rules["setup_minutes"])
        self.assertEqual("09:30", setup_done.strftime("%H:%M"))
        self.assertEqual(cutoff, setup_done + timedelta(minutes=rules["inspection_minutes"]))


if __name__ == "__main__":
    unittest.main()
