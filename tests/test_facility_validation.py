"""A player can record an unused facility as level zero without breaking a team."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import planner_core as p


class FacilityValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = p.Data()
        request = p.demo_profile()
        cls.profile = request["profile"]
        cls.mids = request["candidate_member_ids"]
        cls.sids = request["candidate_snap_ids"]

    def test_unrelated_invalid_facility_does_not_block_selected_team(self):
        baseline = p.PowerModel(self.data, self.profile, self.mids, self.sids)
        profile = deepcopy(self.profile)
        next(row for row in profile["facilities"] if row["id"] == 405)["level"] = 0
        model = p.PowerModel(self.data, profile, self.mids, self.sids)
        self.assertEqual(model.band, baseline.band)

    def test_required_level_zero_facility_has_actionable_issue(self):
        profile = deepcopy(self.profile)
        mids = [*self.mids[:-1], 20]  # 和泉 朋花 uses facility 405.
        profile["inventory"]["members"][-1]["id"] = 20
        next(row for row in profile["facilities"] if row["id"] == 405)["level"] = 0
        check = p.growth_issues({"profile": profile, "candidate_member_ids": mids,
                                 "candidate_snap_ids": self.sids,
                                 "settings": {"normal": {"method": "ap"}}}, self.data)
        self.assertIn({"label": "朋花のドラム · 道具等级", "reason": "请填写 1～30 的整数",
                       "target": "facility", "id": 405}, check["issues"])


if __name__ == "__main__":
    unittest.main()
