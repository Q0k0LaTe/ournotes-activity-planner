"""Compare song search with direct scoring of every binding in a small pool."""
import itertools
import unittest

import planner_core as p
from sample import sample
import song_optimizer
import simulation


class SongOptimizerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = p.Data()

    def request(self, snaps=5, method='ap', mode='normal'):
        value = sample(self.data)
        value['candidate_member_ids'] = value['candidate_member_ids'][:5]
        value['candidate_snap_ids'] = value['candidate_snap_ids'][:snaps]
        return {'input': value, 'mode': mode, 'song_id': 100111,
                'difficulty': 'expert', 'method': method,
                'consumed': 200 if mode == 'challenge' else 4}

    def test_ap_minimum_score_matches_all_bindings(self):
        raw = self.request()
        found = song_optimizer.optimize(raw, self.data)
        mids = sorted(raw['input']['candidate_member_ids'])
        sids = raw['input']['candidate_snap_ids']
        model = p.PowerModel(self.data, raw['input']['profile'], mids, sids)
        model.music(100111, False)
        leader, vectors = model.best_leader(mids)
        scorer = p.Scores(self.data, {'song_id': 100111, 'difficulty': 'expert', 'method': 'ap'}, False)
        gold = 0
        for binding in itertools.permutations(sids):
            power = model.total(mids, binding, vectors)
            contract = p.sk.derive_ap_skill_contract(self.data.snapshot, raw['input']['profile'], mids, list(binding),
                                                     _verified_inputs=self.data.skill_inputs)
            gold = max(gold, scorer.evaluate(power, contract['slots'])['minimum_score'])
        self.assertEqual(found['team']['score']['minimum_score'], gold)
        self.assertEqual(found['team']['leader_id'], leader)
        self.assertTrue(found['search']['complete'])

    def test_skip_honors_fixed_binding_and_bonus_floor(self):
        raw = self.request(6, 'skip', 'normal')
        raw['objective'] = 'event_pt'
        input_data = raw['input']
        mid, sid = input_data['candidate_member_ids'][0], input_data['candidate_snap_ids'][0]
        input_data['team_settings']['required_bindings'] = [{'member_id': mid, 'snap_id': sid}]
        input_data['team_settings']['min_shop_bonus_10000'] = 100
        found = song_optimizer.optimize(raw, self.data)
        self.assertEqual(dict(zip(found['team']['member_ids'], found['team']['snap_ids']))[mid], sid)
        self.assertGreaterEqual(found['team']['bonuses_10000']['shop_pt'], 100)
        self.assertEqual(found['team']['score']['minimum_score'], found['team']['score']['maximum_score'])

    def test_skip_event_and_badge_targets_match_brute_force(self):
        raw = self.request(5, 'skip', 'normal')
        raw['input']['candidate_snap_ids'].append(62)
        raw['input']['profile']['inventory']['snaps'].append(
            {'id': 62, 'level': 20, 'limit_break_count': 0})
        mids = sorted(raw['input']['candidate_member_ids'])
        sids = raw['input']['candidate_snap_ids']
        model = p.PowerModel(self.data, raw['input']['profile'], mids, sids)
        model.music(100111, False)
        leader, vectors = model.best_leader(mids)
        scorer = p.Scores(self.data, {'song_id': 100111, 'difficulty': 'expert', 'method': 'skip'}, False)
        bases = {r['rank']: r for r in self.data.event['ordinary_base_rewards']}
        expected = {'event_pt': None, 'shop_pt': None}
        for selected in itertools.combinations(sids, 5):
            for binding in itertools.permutations(selected):
                power = model.total(mids, binding, vectors)
                bonuses = model.bonuses(mids, binding)
                score = scorer.evaluate(power, None)
                self.assertEqual(score['rank'], 'C')
                base = bases['C']
                pt = (10000 + bonuses['event_pt']) * 20 * base['event_pt_base'] // 10000
                badges = sum(row['_resourceCount'] * (10000 + bonuses['shop_pt']) * 20 // 10000
                             for row in base['shop_reward_rows'])
                for goal, key in [('event_pt', (pt, badges, score['minimum_score'], power)),
                                  ('shop_pt', (badges, pt, score['minimum_score'], power))]:
                    expected[goal] = max(expected[goal], key) if expected[goal] else key
        for goal in expected:
            found = song_optimizer.optimize({**raw, 'objective': goal}, self.data)
            team = found['team']
            pt, badges = team['per_live']['event_pt'], team['per_live']['shop_pt']
            actual = ((pt, badges, team['score']['minimum_score'], team['power']) if goal == 'event_pt'
                      else (badges, pt, team['score']['minimum_score'], team['power']))
            self.assertEqual(actual, expected[goal])
            self.assertEqual(found['objective'], goal)
            self.assertEqual(team['leader_id'], leader)

    def test_ap_challenge_pt_target_matches_every_binding(self):
        raw = self.request(5, 'ap', 'challenge')
        mids = sorted(raw['input']['candidate_member_ids'])
        sids = raw['input']['candidate_snap_ids']
        model = p.PowerModel(self.data, raw['input']['profile'], mids, sids)
        model.music(100111, True)
        _, vectors = model.best_leader(mids)
        scorer = p.Scores(self.data, {'song_id': 100111, 'difficulty': 'expert', 'method': 'ap'}, True)
        bases = {r['rank']: r['event_pt_base'] for r in self.data.event['challenge_base_rewards']}
        gold = None
        for binding in itertools.permutations(sids):
            power = model.total(mids, binding, vectors)
            contract = p.sk.derive_ap_skill_contract(self.data.snapshot, raw['input']['profile'], mids, list(binding),
                                                     _verified_inputs=self.data.skill_inputs)
            score = scorer.evaluate(power, contract['slots'])
            bonus = model.bonuses(mids, binding)['event_pt']
            pt = bases[score['rank']] * (10000 + bonus) // 10000
            gold = max(gold, pt) if gold is not None else pt
        found = song_optimizer.optimize({**raw, 'objective': 'event_pt'}, self.data)
        self.assertEqual(found['team']['per_live']['event_pt'], gold)
        self.assertTrue(found['search']['complete'])

    def test_skip_reward_stays_at_c_when_model_score_rank_changes(self):
        base = sample(self.data)
        base['candidate_snap_ids'] = [33, 37, 52, 61, 3]
        base['profile']['inventory']['members'] = [row for row in base['profile']['inventory']['members']
                                                   if row['id'] != 3]
        results = []
        for mid, level in ((63, 1), (38, 20)):
            request = {**base, 'candidate_member_ids': [59, 11, 55, 26, mid]}
            request['profile'] = {**base['profile'], 'inventory': {**base['profile']['inventory'],
                'members': base['profile']['inventory']['members'] +
                [{'id': mid, 'level': level, 'training_count': 0, 'awakening_count': 0,
                  'live_skill_level': 1, 'gekisou_skill_level': 1}]}}
            results.append(simulation.simulate({'input': request, 'team': {
                'member_ids': request['candidate_member_ids'], 'snap_ids': request['candidate_snap_ids'],
                'leader_id': 59}, 'mode': 'normal', 'song_id': 100039, 'difficulty': 'expert',
                'method': 'skip', 'consumed': 4}, self.data))
        lower_bonus, higher_bonus = results
        self.assertLess(lower_bonus['bonuses_10000']['event_pt'], higher_bonus['bonuses_10000']['event_pt'])
        self.assertEqual((lower_bonus['score']['theoretical_rank'], higher_bonus['score']['theoretical_rank']), ('D', 'C'))
        self.assertEqual((lower_bonus['score']['rank'], higher_bonus['score']['rank']), ('C', 'C'))
        self.assertEqual((lower_bonus['per_live']['event_pt'], higher_bonus['per_live']['event_pt']), (500, 550))

    def test_challenge_skip_and_skip_score_search_are_rejected(self):
        request = self.request(5, 'skip', 'challenge')
        with self.assertRaisesRegex(p.InputError, '仅用于普通单人演出'):
            song_optimizer.optimize({**request, 'objective': 'event_pt'}, self.data)
        with self.assertRaisesRegex(p.InputError, '仅用于普通单人演出'):
            simulation.simulate({**request, 'team': {'member_ids': request['input']['candidate_member_ids'],
                'snap_ids': request['input']['candidate_snap_ids'], 'leader_id': 59}}, self.data)
        request['mode'] = 'normal'
        with self.assertRaisesRegex(p.InputError, '不会更新最高分'):
            song_optimizer.optimize({**request, 'objective': 'score'}, self.data)

    def test_unavailable_boost_and_cp_costs_are_rejected_before_scoring(self):
        for mode, consumed, label in (('normal', 11, '普通演出 Boost'),
                                      ('challenge', 600, '挑战演出 CP')):
            raw = self.request(5, 'ap', mode)
            raw['consumed'] = consumed
            raw['objective'] = 'event_pt'
            with self.subTest(mode=mode), self.assertRaisesRegex(p.InputError, label):
                song_optimizer.optimize(raw, self.data)
            raw['team'] = {'member_ids': raw['input']['candidate_member_ids'],
                           'snap_ids': raw['input']['candidate_snap_ids'],
                           'leader_id': raw['input']['candidate_member_ids'][0]}
            with self.subTest(mode=mode, endpoint='simulation'), self.assertRaisesRegex(p.InputError, label):
                simulation.simulate(raw, self.data)

    def test_challenge_score_goal_and_pt_goal_each_respect_their_objective(self):
        request = self.request(5, 'ap', 'challenge')
        request['input']['candidate_member_ids'] = [59, 11, 55, 26, 38, 63]
        request['input']['profile']['inventory']['members'] = [
            row for row in request['input']['profile']['inventory']['members'] if row['id'] != 3]
        request['input']['profile']['inventory']['members'] += [
            {'id': mid, 'level': level, 'training_count': 0, 'awakening_count': 0,
             'live_skill_level': 1, 'gekisou_skill_level': 1}
            for mid, level in ((38, 30), (63, 1))]
        score = song_optimizer.optimize({**request, 'objective': 'score'}, self.data)['team']
        pt = song_optimizer.optimize({**request, 'objective': 'event_pt'}, self.data)['team']
        self.assertGreaterEqual(score['score']['minimum_score'], pt['score']['minimum_score'])
        self.assertGreaterEqual(pt['per_live']['event_pt'], score['per_live']['event_pt'])


if __name__ == '__main__':
    unittest.main()
