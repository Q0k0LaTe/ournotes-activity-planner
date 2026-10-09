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
        self.assertEqual((len(catalog['members']), len(catalog['snaps'])), (67, 68))
        for kind, last in (('members', 67), ('snaps', 68)):
            cards = catalog[kind]
            self.assertEqual({c['id'] for c in cards}, set(range(1, last + 1)))
            self.assertEqual(sum(c['rarity'] == 2 for c in cards), 25)
            self.assertEqual(sum(c['rarity'] == 3 for c in cards), 27)
        self.assertEqual([c['title'] for c in catalog['members'] if c['id'] in (65, 66, 67)],
                         ['薄明を裂いて', '光芒に立つ', '笑み、暗がりにて'])
        self.assertEqual([c['title'] for c in catalog['snaps'] if c['id'] in (65, 66, 67, 68)],
                         ['赤橙の中', 'きみのため', '光、手をかざして', 'DIMENSIONAL OVERLAP'])
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


if __name__ == '__main__':
    unittest.main()
