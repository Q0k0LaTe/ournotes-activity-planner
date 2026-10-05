"""Reproducible synthetic checks of event #1 team-composition claims.

No player inventory is read. All candidate teams own the same five Snaps.
After installing project dependencies, run with
PYTHONPATH=workbench:workbench/runtime python3 -B tools/event_claim_experiments.py.
JSON is written under work/.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'workbench'), str(ROOT / 'workbench/runtime')]
import planner_core as p
from sample import sample
import simulation
import song_optimizer


SONGS = (100056, 100063, 100109)
SNAPS = (52, 61, 62, 63, 64)
TEAMS = {
    '3SSR+2R': (61, 62, 59, 11, 14),
    '2SSR+3R': (61, 62, 11, 13, 14),
    '1SSR+活动SR+3R': (61, 63, 11, 12, 14),
    '2SSR+活动SR+2R': (61, 62, 63, 11, 14),
    '5R': (11, 12, 13, 14, 15),
}


def make_input(data, members, stage):
    request = sample(data)
    member_cards = {card['id']: card for card in data.catalog()['members']}
    snap_cards = {card['id']: card for card in data.catalog()['snaps']}
    request['candidate_member_ids'] = list(members)
    request['candidate_snap_ids'] = list(SNAPS)
    request['profile']['inventory']['members'] = [
        {'id': mid, 'level': member_cards[mid]['caps'][stage],
         'training_count': stage, 'awakening_count': stage,
         'live_skill_level': 5, 'gekisou_skill_level': 1}
        for mid in members]
    request['profile']['inventory']['snaps'] = [
        {'id': sid, 'level': snap_cards[sid]['caps'][stage], 'limit_break_count': stage}
        for sid in SNAPS]
    return request


def main():
    data = p.Data()
    report = {'snapshot': data.snapshot_label, 'event_id': 1,
              'assumptions': {'snap_ids': SNAPS, 'challenge_cp': 200,
                              'growth_stages': [0, 1], 'member_live_skill_level': 5,
                              'character_rank': 5, 'facilities': 'sample levels, up to 3',
                              'method': 'theoretical AP, worst of 120 skill orders'},
              'teams': dict(TEAMS), 'rows': [], 'difficulty_rows': [],
              'skip_comparisons': [], 'challenge_goal_comparison': {}}
    for stage in (0, 1):
        for song in SONGS:
            for label, members in TEAMS.items():
                request = make_input(data, members, stage)
                optimum = song_optimizer.optimize({
                    'input': request, 'mode': 'challenge', 'song_id': song,
                    'difficulty': 'expert', 'method': 'ap', 'consumed': 200,
                    'objective': 'event_pt'}, data)['team']
                report['rows'].append({
                    'stage': stage, 'song_id': song, 'composition': label,
                    'member_ids': optimum['member_ids'], 'snap_ids': optimum['snap_ids'],
                    'leader_id': optimum['leader_id'], 'score': optimum['score']['minimum_score'],
                    'rank': optimum['score']['rank'],
                    'pt_bonus_10000': optimum['bonuses_10000']['event_pt'],
                    'event_pt': optimum['per_live']['event_pt'],
                    'badges': optimum['per_live']['shop_pt']})
                print(stage, song, label, optimum['score']['rank'], optimum['per_live']['event_pt'], flush=True)
                if stage == 0 and label in ('3SSR+2R', '1SSR+活动SR+3R', '5R'):
                    scores = {}
                    for difficulty in ('easy', 'normal', 'hard', 'expert'):
                        if difficulty == 'expert':
                            scores[difficulty] = optimum['score']['minimum_score']
                        else:
                            check = simulation.simulate({
                                'input': request, 'team': optimum,
                                'mode': 'challenge', 'song_id': song,
                                'difficulty': difficulty, 'method': 'ap', 'consumed': 200}, data)
                            scores[difficulty] = check['score']['minimum_score']
                    report['difficulty_rows'].append({
                        'song_id': song, 'composition': label, 'scores': scores,
                        'easy_to_expert': round(scores['easy'] / scores['expert'], 6),
                        'easy_to_other_mean': round(scores['easy'] /
                                                    (sum(scores[d] for d in ('normal', 'hard', 'expert')) / 3), 6)})

    low_members, low_snaps = [59, 11, 55, 26, 3], [33, 37, 52, 61, 3]
    low = sample(data)
    low['candidate_member_ids'], low['candidate_snap_ids'] = low_members, low_snaps
    low['profile']['inventory']['members'] = [
        {'id': mid, 'level': 1, 'training_count': 0, 'awakening_count': 0,
         'live_skill_level': 1, 'gekisou_skill_level': 1} for mid in low_members]
    low['profile']['inventory']['snaps'] = [
        {'id': sid, 'level': 1, 'limit_break_count': 0} for sid in low_snaps]
    high = make_input(data, TEAMS['2SSR+活动SR+2R'], 1)
    for label, request, song, leader in (
        ('low_growth', low, 100001, 59),
        ('high_growth', high, 100109, 61),
    ):
        team = {'member_ids': request['candidate_member_ids'],
                'snap_ids': request['candidate_snap_ids'], 'leader_id': leader}
        comparison = {'label': label, 'song_id': song, 'team': team,
                      'growth': 'all member/Snap Lv1, skill Lv1' if label == 'low_growth'
                                else 'stage 1 caps, skill Lv5', 'results': {}}
        for method in ('ap', 'skip'):
            result = simulation.simulate({
                'input': request, 'team': team, 'mode': 'normal', 'song_id': song,
                'difficulty': 'expert', 'method': method, 'consumed': 4}, data)
            comparison['results'][method] = {
                'rank': result['score']['rank'], 'score': result['score']['minimum_score'],
                'per_live': result['per_live']}
        report['skip_comparisons'].append(comparison)

    challenge = sample(data)
    challenge['candidate_member_ids'] = [59, 11, 55, 26, 38, 63]
    challenge['candidate_snap_ids'] = low_snaps
    challenge['profile']['inventory']['members'] = [
        row for row in challenge['profile']['inventory']['members'] if row['id'] != 3]
    challenge['profile']['inventory']['members'] += [
        {'id': mid, 'level': level, 'training_count': 0, 'awakening_count': 0,
         'live_skill_level': 1, 'gekisou_skill_level': 1}
        for mid, level in ((38, 30), (63, 1))]
    for objective in ('score', 'event_pt'):
        result = song_optimizer.optimize({
            'input': challenge, 'mode': 'challenge', 'song_id': 100109,
            'difficulty': 'expert', 'method': 'ap', 'consumed': 200,
            'objective': objective}, data)['team']
        report['challenge_goal_comparison'][objective] = {
            'member_ids': result['member_ids'], 'snap_ids': result['snap_ids'],
            'leader_id': result['leader_id'], 'score': result['score']['minimum_score'],
            'rank': result['score']['rank'], 'per_live': result['per_live']}
    destination = ROOT / 'work/event-claim-experiments.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(destination)


if __name__ == '__main__':
    main()
