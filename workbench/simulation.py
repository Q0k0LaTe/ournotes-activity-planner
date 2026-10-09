"""Fixed-team, chart-specific reward estimates for the event planning UI.

The scoring and reward arithmetic are delegated to the verified public model.
This module only validates the chosen team and joins its existing APIs.
"""
from __future__ import annotations

import planner_core as p
import team_candidates as teams


def simulate(raw, data):
    if not isinstance(raw, dict):
        raise p.InputError('歌曲模拟请求格式不正确。')
    source = raw.get('input')
    team = raw.get('team')
    if not isinstance(source, dict) or not isinstance(team, dict):
        raise p.InputError('请先选择已完成计算的队伍。')
    mids, sids = team.get('member_ids'), team.get('snap_ids')
    leader = team.get('leader_id', 0)
    # Reuse the fixed-team validator, including owned cards and actual growth.
    teams.evaluate({**source, 'fixed_team': {'member_ids': mids, 'snap_ids': sids,
                                             'leader_id': leader}}, data)
    mode = raw.get('mode')
    if mode not in ('normal', 'challenge'):
        raise p.InputError('请选择普通或挑战演出。')
    song_id = p.integer(raw.get('song_id'), '歌曲 ID', 1)
    song = data.index['MasterLiveMusic'].get(song_id)
    if song is None:
        raise p.InputError('当前数据快照没有这首歌。')
    challenge = mode == 'challenge'
    if challenge and not any(row['_eventId'] == data.event_id and row['_liveMusicId'] == song_id
                             for row in data.tables['MasterChallengeMusic']):
        raise p.InputError(f'这首歌不属于活动 {data.event_id} 的挑战演出。')
    difficulty, method = raw.get('difficulty'), raw.get('method')
    if difficulty not in ('easy', 'normal', 'hard', 'expert') or method not in ('ap', 'skip'):
        raise p.InputError('请选择已支持的谱面难度和打法。')
    if challenge and method == 'skip':
        raise p.InputError('游戏跳过功能仅用于普通单人演出，挑战演出请选择手动 AP 参考。')
    consumed = teams.live_consumption(raw.get('consumed'), mode, data)

    model = p.PowerModel(data, source['profile'], mids, sids)
    model.music(song_id, challenge)
    if leader:
        rates = p.leader_rates(data, model.cards[leader], model.own[leader],
                               [model.cards[m] for m in mids], [model.chars[m] for m in mids],
                               model.music_type)
        vectors = [p.dp._mul_floor(model.b[m], rate) for m, rate in zip(mids, rates)]
    else:
        leader, vectors = model.best_leader(tuple(mids))
    power = model.total(mids, sids, vectors)
    bonuses = model.bonuses(mids, sids)
    scorer = p.Scores(data, {'song_id': song_id, 'difficulty': difficulty, 'method': method}, challenge)
    slots = None
    if method == 'ap':
        contract = p.sk.derive_ap_skill_contract(data.snapshot, source['profile'], mids, sids,
                                                 _verified_inputs=data.skill_inputs)
        slots = contract['slots']
    score = scorer.evaluate(power, slots)
    preview = p.rw.preview_challenge_rewards if challenge else p.rw.preview_normal_rewards
    rewards = preview(data.snapshot, score['rank'], consumed, bonuses['event_pt'],
                      bonuses['shop_pt'], _context=data.reward_context)['gained']
    return {'song_id': song_id, 'song_title': data.text[song['_titleTextID']],
            'difficulty': difficulty, 'mode': mode, 'method': method, 'consumed': consumed,
            'team': {'member_ids': mids, 'snap_ids': sids, 'leader_id': leader},
            'power': power, 'bonuses_10000': bonuses, 'score': score, 'per_live': rewards,
            'source': {'snapshot': data.snapshot_label, 'event_id': data.event_id, 'basis': 'model_estimate'}}
