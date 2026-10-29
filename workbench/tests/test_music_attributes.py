"""Current challenge rules reach both recommendation and fixed evaluation."""
from copy import deepcopy
from unittest import TestCase
from unittest.mock import patch

import team_candidates as t
from sample import sample


class MusicAttributeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = t.p.Data()

    def request(self):
        request = sample(self.data)
        members, characters = [], set()
        for typ in range(1, 6):
            card = next(c for c in self.data.tables['MasterMemberCard']
                        if c['_cardType'] == typ and c['_characterID'] not in characters)
            members.append(card['_id'])
            characters.add(card['_characterID'])
        snaps = request['candidate_snap_ids'][:5]
        request['candidate_member_ids'], request['candidate_snap_ids'] = members, snaps
        request['profile']['inventory']['members'] = [
            {'id': mid, 'level': 20, 'training_count': 0, 'awakening_count': 0,
             'live_skill_level': 1, 'gekisou_skill_level': 1} for mid in members]
        request['fixed_team'] = {'member_ids': members, 'snap_ids': snaps, 'leader_id': members[0]}
        request['team_settings'].update(mode='challenge', count=1, required_leader_id=members[0],
            required_bindings=[{'member_id': mid, 'snap_id': sid} for mid, sid in zip(members, snaps)])
        return request

    def test_old_challenge_scenarios_resolve_to_event_all_for_search_and_fixed_team(self):
        request = self.request()
        self.assertEqual(t.workbench_catalog(self.data)['event']['challenge_music_attributes'], [99])
        results = []
        for old_attribute in (0, 2, 99):
            request['team_settings']['music_attribute'] = old_attribute
            fixed = t.evaluate(request, self.data)
            self.assertEqual(fixed['settings']['music_attribute'], 99)
            self.assertEqual(request['team_settings']['music_attribute'], old_attribute)
            results.append(fixed['teams'][0])
        self.assertEqual([row['power'] for row in results], [results[0]['power']] * 3)
        search = t.optimize(request, self.data)
        self.assertEqual(search['settings']['music_attribute'], 99)
        self.assertEqual(search['teams'][0]['power'], results[0]['power'])

    def test_all_five_colors_match_song_calculation_except_explicitly_excluded_tags(self):
        request = self.request()
        mids, sids = request['candidate_member_ids'], request['candidate_snap_ids']
        for awakening in (0, 4):
            for card in request['profile']['inventory']['members']:
                card['awakening_count'] = awakening
            normalized = t.parse_request(request, self.data)
            model = t.p.PowerModel(self.data, request['profile'], mids, sids)
            t.set_power_context(model, normalized['team_settings'])
            expected = deepcopy(model.static)
            for song_id in (100005, 100029, 100115, 100118):
                model.music(song_id, True)
                song = self.data.index['MasterLiveMusic'][song_id]
                for mid in mids:
                    card, rank = model.cards[mid], model.rank[mid]
                    rate = model.tag_base + rank['_musicTagBonusRate'] if set(card['_bestMusicTagIDs']) & set(song['_bestMusicTagIDs']) else 0
                    tag = t.p.dp._mul_floor(model.b[mid], (rate,) * 3)
                    self.assertEqual(tuple(a - b for a, b in zip(model.static[mid], tag)), expected[mid])

    def test_normal_scenarios_and_card_filters_remain_separate(self):
        request = self.request()
        request['team_settings']['mode'] = 'normal'
        for typ in (0, 2, 99):
            request['team_settings']['music_attribute'] = typ
            self.assertEqual(t.parse_request(request, self.data)['team_settings']['music_attribute'], typ)
        for typ in (6, 98, 100, True, '99'):
            request['team_settings']['music_attribute'] = typ
            with self.assertRaises(t.p.InputError):
                t.parse_request(request, self.data)
        request['team_settings'].update(music_attribute=99, member_type=99)
        with self.assertRaises(t.p.InputError):
            t.parse_request(request, self.data)

    def test_challenge_type_is_derived_instead_of_hardcoded_to_event_four(self):
        request = self.request()
        rows = deepcopy(self.data.tables['MasterChallengeMusic'])
        for row in rows:
            if row['_eventId'] == self.data.event_id:
                row['_musicType'] = 4
        with patch.dict(self.data.tables, {'MasterChallengeMusic': rows}):
            self.assertEqual(t.parse_request(request, self.data)['team_settings']['music_attribute'], 4)
        for row in rows:
            if row['_eventId'] == self.data.event_id:
                row['_musicType'] = 0
        with patch.dict(self.data.tables, {'MasterChallengeMusic': rows}):
            self.assertEqual(t.challenge_music_attributes(self.data), [3, 4, 5])
            request['team_settings']['music_attribute'] = 2
            self.assertEqual(t.parse_request(request, self.data)['team_settings']['music_attribute'], 2)
