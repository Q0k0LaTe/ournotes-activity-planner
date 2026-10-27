"""AP-only Halloween mechanics and conservative song-score bounds."""
from copy import deepcopy
from collections import Counter
import itertools
import unittest

import planner_core as p
import score_intervals
from score_bounds import pool_upper_signature, signature_score


class HalloweenSkillTests(unittest.TestCase):
    def test_cumulative_window_counts_simultaneous_notes_caps_and_does_not_extend(self):
        times = [999, 1000, 1100, 1100, 1200, 1300, 2000, 2100]
        chart = {'skill_time_ms': [1000], 'music_length_ms': 3000,
                 'notes': [(t, i, 1) for i, t in enumerate(times)],
                 'combo_bases': [p.ms.f32(1)] * len(times), 'note_percents': {1: 100}}
        slots = [{'extension_ms': 5000, 'active_live_effects': [],
                  'active_support_effects': [{'skill_effect_type': 2001, 'effect_value': 1000,
                      'activation_ms': 1000, 'notes_per_step': 2, 'max_count': 2, 'max_effect_value': 1500}]}]
        samples = list(p.ms.cumulative_ap_factor_samples(chart, slots, (0,)))
        self.assertEqual([factor for _, _, factor in samples],
                         [p.ms.f32(x) for x in (1, 1, 1.1, 1.1, 1.15, 1.15, 1, 1)])
        intervals = dict(score_intervals.signature(chart, slots, (0,), score_intervals.note_index(chart)))
        self.assertEqual(intervals, Counter((100, base, factor) for _, base, factor in samples))
        capped = deepcopy(slots)
        capped[0]['active_support_effects'][0]['max_effect_value'] = 10000
        self.assertEqual(max(factor for _, _, factor in p.ms.cumulative_ap_factor_samples(chart, capped, (0,))),
                         p.ms.f32(1.2))
        changed = deepcopy(slots)
        changed[0]['active_support_effects'][0]['notes_per_step'] = 4
        self.assertNotEqual(p.Scores.skill_key(slots), p.Scores.skill_key(changed))

    def test_release_proof_rejects_conditions_that_can_end_perfect_bonus(self):
        data = p.Data()
        tables = data.skill_inputs[0]
        self.assertFalse(p.sk._condition_group(tables, 13, 1, 'release')['matched'])
        mutated = dict(tables)
        mutated['MasterSkillTarget'] = [dict(row, _judgement=5) if row['_id'] == 43 else row
                                       for row in tables['MasterSkillTarget']]
        with self.assertRaisesRegex(ValueError, 'not invariant'):
            p.sk._condition_group(mutated, 13, 1, 'release')
        mutated = dict(tables)
        mutated['MasterSkillCondition'] = [dict(row, _isPositive=False) if row['_id'] == 17 else row
                                          for row in tables['MasterSkillCondition']]
        with self.assertRaisesRegex(ValueError, 'not invariant'):
            p.sk._condition_group(mutated, 13, 1, 'release')

    def test_ramp_bound_covers_each_order_and_dense_chart_updates(self):
        times = list(range(0, 1800, 10))
        chart = {'skill_time_ms': [100, 300], 'music_length_ms': 2000,
                 'notes': [(t, i, 1) for i, t in enumerate(times)],
                 'combo_bases': [p.ms.f32(1)] * len(times), 'note_percents': {1: 100},
                 'level': 25, 'denominator': len(times), 'adjustment': 1, 'perfect_percent': 100}
        slots = [{'extension_ms': 0, 'active_live_effects': [],
                  'active_support_effects': [{'skill_effect_type': 2001, 'effect_value': 1000,
                    'activation_ms': 1000, 'notes_per_step': step, 'max_count': 12, 'max_effect_value': 12000}]}
                 for step in (2, 4)]
        upper = signature_score(chart, pool_upper_signature(chart, [slots, slots]), 1000000)
        for order in itertools.permutations(range(2)):
            score = sum(p.ms.note_score(1000000, 25, len(times), 1, 100, 100, base, factor)
                        for _, base, factor in p.ms.cumulative_ap_factor_samples(chart, slots, order))
            self.assertGreaterEqual(upper, score)
