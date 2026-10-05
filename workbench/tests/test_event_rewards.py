"""Cross-check event #1 rewards against published bases and raw rate rows."""
import unittest

import planner_core as p


class EventRewardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = p.Data()

    def test_published_rank_bases_and_all_consumption_rates(self):
        ordinary_pt = dict(zip(p.RANKS, (15, 25, 35, 50, 75, 100)))
        ordinary_badges = dict(zip(p.RANKS, (18, 30, 42, 60, 90, 120)))
        ordinary_cp = dict(zip(p.RANKS, (3, 4, 5, 6, 8, 10)))
        challenge_pt = dict(zip(p.RANKS, (1500, 2000, 2550, 3250, 3900, 5000)))
        challenge_badges = dict(zip(p.RANKS, (1450, 2650, 3400, 3750, 4450, 4950)))
        for challenge in (False, True):
            bases = self.data.event['challenge_base_rewards' if challenge else 'ordinary_base_rewards']
            for base in bases:
                rank = base['rank']
                self.assertEqual(base['event_pt_base'], (challenge_pt if challenge else ordinary_pt)[rank])
                self.assertEqual(sum(row['_resourceCount'] for row in base['shop_reward_rows']),
                                 (challenge_badges if challenge else ordinary_badges)[rank])
                if not challenge:
                    self.assertEqual(base['cp_base'], ordinary_cp[rank])
                for consumed in ((200, 400, 800, 1600) if challenge else range(1, 11)):
                    rate = (consumed // 200) if challenge else consumed * 5
                    for pt_bonus, badge_bonus in ((0, 0), (10800, 14000), (5500, 7500)):
                        preview = (p.rw.preview_challenge_rewards if challenge else p.rw.preview_normal_rewards)(
                            self.data.snapshot, rank, consumed, pt_bonus, badge_bonus,
                            _context=self.data.reward_context)['gained']
                        self.assertEqual(preview['event_pt'],
                                         base['event_pt_base'] * rate * (10000 + pt_bonus) // 10000)
                        self.assertEqual(preview['shop_pt'],
                                         sum(row['_resourceCount'] * rate * (10000 + badge_bonus) // 10000
                                             for row in base['shop_reward_rows']))
                        self.assertEqual(preview['cp'], 0 if challenge else base['cp_base'] * rate)

    def test_raw_effect_rows_separate_member_pt_and_snap_badge_bonuses(self):
        rows = [row for row in self.data.tables['MasterEventEffect'] if row['_eventId'] == 1]
        self.assertEqual(len(rows), 20)
        self.assertEqual({row['_resourceTypeConstraint'] for row in rows if row['_eventBonusType'] == 0}, {2})
        self.assertEqual({row['_resourceTypeConstraint'] for row in rows if row['_eventBonusType'] == 1}, {3})
        self.assertEqual({row['_resourceTypeConstraint'] for row in rows if row['_eventBonusType'] == 2}, {2, 3})

    def test_pt_and_badge_bonuses_are_independent(self):
        first = p.rw.preview_normal_rewards(self.data.snapshot, 'C', 4, 7000, 9000,
                                            _context=self.data.reward_context)['gained']
        self.assertEqual(first, {'event_pt': 850, 'shop_pt': 1140, 'cp': 80})
        second = p.rw.preview_normal_rewards(self.data.snapshot, 'C', 4, 7000, 0,
                                             _context=self.data.reward_context)['gained']
        self.assertEqual(second['event_pt'], first['event_pt'])
        self.assertEqual(second['shop_pt'], 600)


if __name__ == '__main__':
    unittest.main()
