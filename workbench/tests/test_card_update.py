"""The post-snapshot birthday card is available to real team calculations."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import planner_core as p
import team_candidates as teams
from sample import sample


class CardUpdateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = p.Data()

    def test_birthday_member_is_in_catalog_and_usable_as_leader(self):
        catalog = teams.workbench_catalog(self.data)
        self.assertEqual((len(catalog['members']), len(catalog['snaps'])), (74, 77))
        for kind, last in (('members', 74), ('snaps', 77)):
            cards = catalog[kind]
            expected = set(range(1, last + 1))
            self.assertEqual({c['id'] for c in cards}, expected)
            self.assertEqual(sum(c['rarity'] == 2 for c in cards), 25)
            self.assertEqual(sum(c['rarity'] == 3 for c in cards), 29)
        self.assertEqual([c['title'] for c in catalog['members'] if c['id'] in (65, 66, 67)],
                         ['薄明を裂いて', '光芒に立つ', '笑み、暗がりにて'])
        self.assertEqual([c['title'] for c in catalog['snaps'] if c['id'] in (65, 66, 67, 68)],
                         ['赤橙の中', 'きみのため', '光、手をかざして', 'DIMENSIONAL OVERLAP'])
        snap = next(c for c in catalog['snaps'] if c['id'] == 70)
        self.assertEqual((snap['name'], snap['title'], snap['rarity'], snap['type'], snap['character_ids'], snap['caps']),
                         ('Ave Mujica', 'Abracadabra', 10, 1, [6, 7, 8, 9, 10], [50, 60, 70, 80, 90]))
        self.assertIn('snaps-70.webp', snap['thumbnail'])
        self.assertEqual((self.data.index['MasterSupportCard'][70]['_supportSkillId01'],
                          self.data.index['MasterSupportCard'][70]['_supportSkillId02']), (71070, 72070))
        for identifier, title in ((27, 'きらめくステージ'), (28, 'おもしれー音'),
                                  (30, '一途な律動'), (33, '盤石の低音')):
            card = next(c for c in catalog['members'] if c['id'] == identifier)
            self.assertEqual((card['rarity'], card['title']), (3, title))
        card = next(c for c in catalog['members'] if c['id'] == 64)
        self.assertEqual((card['character_id'], card['rarity'], card['type'], card['caps']),
                         (22, 20, 5, [50, 60, 70, 80, 90]))
        self.assertIn('64', card['thumbnail'])
        self.assertEqual(self.data.index['MasterMemberCard'][64]['_leaderSkillID'], 59)
        self.assertEqual(len([r for r in self.data.tables['MasterLeaderSkillEffect']
                              if r['_leaderSkillID'] == 59]), 10)

        request = sample(self.data)
        request['candidate_member_ids'][0] = 64
        request['profile']['inventory']['members'][0]['id'] = 64
        request['fixed_team'] = {'member_ids': request['candidate_member_ids'][:5],
                                 'snap_ids': request['candidate_snap_ids'][:5], 'leader_id': 64}
        result = teams.evaluate(request, self.data)
        self.assertEqual(result['status'], 'complete_fixed_team')

        request['candidate_snap_ids'][0] = 70
        request['profile']['inventory']['snaps'][0]['id'] = 70
        request['fixed_team']['snap_ids'][0] = 70
        self.assertEqual(teams.evaluate(request, self.data)['status'], 'complete_fixed_team')

    def test_new_halloween_cards_and_skills_can_be_evaluated_at_both_growth_limits(self):
        # Distinct characters, including both new cumulative leader skills.
        mids, sids = [71, 72, 73, 74, 59], [70, 74, 75, 76, 77]
        catalog = self.data.catalog()
        for stage in (0, 4):
            request = sample(self.data)
            request['candidate_member_ids'], request['candidate_snap_ids'] = mids, sids
            for kind, ids in (('members', mids), ('snaps', sids)):
                cards = {row['id']: row for row in catalog[kind]}
                request['profile']['inventory'][kind] = [
                    {'id': identifier, 'level': cards[identifier]['caps'][stage],
                     **({'training_count': stage, 'awakening_count': stage,
                         'live_skill_level': stage + 1, 'gekisou_skill_level': stage + 1}
                        if kind == 'members' else {'limit_break_count': stage})}
                    for identifier in ids]
            for leader in mids[:4]:
                with self.subTest(stage=stage, leader=leader):
                    request['fixed_team'] = {'member_ids': mids, 'snap_ids': sids, 'leader_id': leader}
                    self.assertEqual(teams.evaluate(request, self.data)['status'], 'complete_fixed_team')

    def test_new_charts_and_all_four_neutral_challenges_are_usable(self):
        catalog = self.data.catalog()
        self.assertEqual(len(catalog['songs']), 93)
        self.assertEqual({song['id'] for song in catalog['songs'] if song['challenge']},
                         {100005, 100029, 100115, 100118})
        for song in (100102, 100107, 100115, 100118):
            for difficulty in ('easy', 'normal', 'hard', 'expert'):
                with self.subTest(song=song, difficulty=difficulty):
                    chart = p.ms.prepare_ap_chart(self.data.snapshot, song, difficulty,
                        1, self.data.event_id, ordinary=True, _conversion_report=self.data.conversion_report,
                        _verified_inputs=self.data.score_inputs)
                    self.assertGreater(len(chart['notes']), 0)
        request = sample(self.data)
        model = p.PowerModel(self.data, request['profile'], request['candidate_member_ids'],
                             request['candidate_snap_ids'])
        for song in (100005, 100029, 100115, 100118):
            model.music(song, True)
            self.assertEqual(model.music_type, 99)


if __name__ == '__main__':
    unittest.main()
