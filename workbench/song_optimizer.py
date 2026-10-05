"""Exact score or event-reward search over an owned pool for one chart.

For a fixed five-member team and a fixed multiset of AP skill effects, a
larger integer power cannot lower any note score. The matching DP therefore
keeps only the strongest binding for each skill multiset and constraint state.
No selected card is dropped. An overflowing DP falls back to complete binding
enumeration; cancellation never publishes a partial optimum.
"""
from __future__ import annotations

from collections import Counter
from types import SimpleNamespace
import itertools
import math
import time

import planner_core as p
import solver_search as upstream_solver
import team_candidates as teams


def _score_upper(scorer, power, slots):
    """One legal activation order bounds the minimum over all orders above."""
    ordered = sorted(slots, key=lambda slot: p.Scores.skill_key([slot])[0])
    signature = scorer.order_signature(ordered, tuple(range(5)))
    chart = scorer.chart
    return sum(n * p.ms.note_score(power, chart['level'], chart['denominator'],
                                   chart['adjustment'], pct, chart['perfect_percent'],
                                   base, factor)
               for (pct, base, factor), n in signature)


def _bindings(model, members, sids, tokens, required, fixed, cancelled, progress):
    """Keep the best power per exact AP skill multiset and required-Snap mask."""
    required_ids = tuple(sorted(required))
    required_bits = {sid: 1 << i for i, sid in enumerate(required_ids)}
    all_required = (1 << len(required_ids)) - 1
    layers = [{(0, 0, 0, 0, ()): (0, (0,) * 5)}] + [{} for _ in range(5)]
    states = 1
    for index, sid in enumerate(sids):
        bit = required_bits.get(sid, 0)
        event_bonus = model.sb[sid]['event_pt_bonus_10000']
        shop_bonus = model.sb[sid]['shop_pt_bonus_10000']
        for size in range(4, -1, -1):
            for (mask, used, event, shop, skills), (power, assigned) in list(layers[size].items()):
                for slot, mid in enumerate(members):
                    if mask & (1 << slot) or (mid in fixed and fixed[mid] != sid) or (sid in fixed.values() and fixed.get(mid) != sid):
                        continue
                    signature = tuple(sorted(skills + (tokens[mid, sid],))) if tokens is not None else ()
                    key = (mask | (1 << slot), used | bit, event + event_bonus, shop + shop_bonus, signature)
                    value = (power + sum(model.pair[mid, sid]), assigned[:slot] + (sid,) + assigned[slot+1:])
                    previous = layers[size+1].get(key)
                    if previous is None or value[0] > previous[0] or (value[0] == previous[0] and value[1] < previous[1]):
                        if previous is None:
                            states += 1
                            if states > p.MAX_MATCH_STATES:
                                raise p.MatchingOverflow()
                        layers[size+1][key] = value
        if cancelled():
            raise p.Cancelled()
        progress(snap_index=index+1, snap_count=len(sids), matching_states=states)
    return sorted((value[1] for (mask, used, _, _, _), value in layers[5].items() if used == all_required),
                  key=lambda assigned: -sum(sum(model.pair[m, s]) for m, s in zip(members, assigned)))


def optimize(raw, data, progress=lambda **kw: None, cancelled=lambda: False):
    started = time.monotonic()
    if not isinstance(raw, dict):
        raise p.InputError('单曲配队请求格式不正确。')
    request = teams.parse_request(raw.get('input'), data)
    settings = request['team_settings']
    mode, difficulty, method = raw.get('mode'), raw.get('difficulty'), raw.get('method')
    objective = raw.get('objective', 'score')
    if mode not in ('normal', 'challenge') or difficulty not in ('easy', 'normal', 'hard', 'expert') or method not in ('ap', 'skip'):
        raise p.InputError('请选择演出类型、谱面难度和打法。')
    if objective not in ('score', 'event_pt', 'shop_pt'):
        raise p.InputError('请选择理论分数、活动 PT 或活动徽章目标。')
    if mode == 'challenge' and method == 'skip':
        raise p.InputError('游戏跳过功能仅用于普通单人演出，挑战演出请选择手动 AP 参考。')
    if method == 'skip' and objective == 'score':
        raise p.InputError('跳过不会更新最高分；请选择活动 PT、活动徽章目标或改用手动 AP。')
    song_id = p.integer(raw.get('song_id'), '歌曲 ID', 1)
    song = data.index['MasterLiveMusic'].get(song_id)
    if song is None:
        raise p.InputError('当前数据快照没有这首歌。')
    challenge = mode == 'challenge'
    if challenge and not any(row['_eventId'] == 1 and row['_liveMusicId'] == song_id
                             for row in data.tables['MasterChallengeMusic']):
        raise p.InputError('这首歌不属于活动 1 的挑战演出。')
    consumed = teams.live_consumption(raw.get('consumed'), mode, data)
    mids, sids = request['candidate_member_ids'], request['candidate_snap_ids']
    model = p.PowerModel(data, request['profile'], mids, sids)
    model.music(song_id, challenge)
    scorer = p.Scores(data, {'song_id': song_id, 'difficulty': difficulty, 'method': method}, challenge)
    preview = p.rw.preview_challenge_rewards if challenge else p.rw.preview_normal_rewards
    pairs = {}
    if method == 'ap':
        progress(stage='核对所有候选卡的技能', done=0, total=1)
        helper = SimpleNamespace(mids=mids, sids=sids, model=model, data=data, request=request,
                                 specs={'normal': [{'method': 'ap'}]},
                                 check=lambda: (_ for _ in ()).throw(p.Cancelled()) if cancelled() else None,
                                 emit=lambda: None)
        upstream_solver.Search.prepare_pairs(helper)
        pairs = helper.pairs
    grouped = {}
    for mid in mids:
        grouped.setdefault(model.cards[mid]['_characterID'], []).append(mid)
    teams_iter = p.MemberTeams(grouped)
    total = len(teams_iter)
    required_m = set(settings['required_member_ids'])
    required_s = set(settings['required_snap_ids'])
    fixed = {row['member_id']: row['snap_id'] for row in settings['required_bindings']}
    required_leader = settings['required_leader_id']
    best = None
    visited, evaluated, overflow_count = 0, 0, 0
    last_emit = 0.0
    for members in teams_iter:
        if cancelled():
            raise p.Cancelled()
        visited += 1
        if not required_m.issubset(members) or (settings['pure_type'] and len({model.cards[m]['_cardType'] for m in members}) != 1):
            continue
        if required_leader:
            leader = required_leader
            rates = p.leader_rates(data, model.cards[leader], model.own[leader],
                                   [model.cards[m] for m in members], [model.chars[m] for m in members], model.music_type)
            vectors = [p.dp._mul_floor(model.b[m], rate) for m, rate in zip(members, rates)]
        else:
            leader, vectors = model.best_leader(members)
        tokens = None
        if method == 'ap':
            token_ids = {}
            tokens = {(m, s): token_ids.setdefault(p.Scores.skill_key([pairs[m, s]])[0], len(token_ids))
                      for m in members for s in sids}
        try:
            bindings = _bindings(model, members, sids, tokens, required_s, fixed, cancelled,
                                 lambda **kw: progress(stage='匹配留影', done=visited-1, total=total, **kw)
                                 if time.monotonic() - last_emit > .4 else None)
        except p.MatchingOverflow:
            overflow_count += 1
            bindings = (binding for chosen in itertools.combinations(sids, 5) if required_s.issubset(chosen)
                        for binding in itertools.permutations(chosen)
                        if all(dict(zip(members, binding)).get(m) == s for m, s in fixed.items()))
        for binding in bindings:
            if cancelled():
                raise p.Cancelled()
            power = model.total(members, binding, vectors)
            slots = [pairs[m, s] for m, s in zip(members, binding)] if method == 'ap' else None
            bonuses = model.bonuses(members, binding)
            if bonuses['event_pt'] < settings['min_event_bonus_10000'] or bonuses['shop_pt'] < settings['min_shop_bonus_10000']:
                continue
            if (objective == 'score' and best is not None and method == 'ap'
                    and _score_upper(scorer, power, slots) < best['score']['minimum_score']):
                continue
            score = scorer.evaluate(power, slots)
            evaluated += 1
            rewards = preview(data.snapshot, score['rank'], consumed,
                              bonuses['event_pt'], bonuses['shop_pt'],
                              _context=data.reward_context)['gained']
            if objective == 'event_pt':
                key = (rewards['event_pt'], rewards['shop_pt'], score['minimum_score'], power)
            elif objective == 'shop_pt':
                key = (rewards['shop_pt'], rewards['event_pt'], score['minimum_score'], power)
            else:
                key = (score['minimum_score'], score['maximum_score'], power,
                       rewards['event_pt'], rewards['shop_pt'])
            if best is None or key > best['_key']:
                best = {'_key': key, 'member_ids': list(members), 'snap_ids': list(binding),
                        'leader_id': leader, 'power': power, 'score': score,
                        'bonuses_10000': bonuses, 'per_live': rewards}
        now = time.monotonic()
        if now - last_emit > .35:
            progress(stage='比较指定谱面的完整卡池', done=visited, total=total,
                     evaluated_bindings=evaluated, elapsed_seconds=round(now-started, 1))
            last_emit = now
    if best is None:
        raise p.InputError('当前必带卡、固定绑定和筛选条件下没有可用队伍。')
    best.pop('_key')
    return {'status': 'complete_song_optimum', 'song_id': song_id,
            'song_title': data.text[song['_titleTextID']], 'difficulty': difficulty,
            'mode': mode, 'method': method, 'objective': objective,
            'consumed': consumed, 'team': best,
            'search': {'complete': True, 'scope': 'selected_owned_pool', 'member_teams': total,
                       'visited_member_teams': visited, 'evaluated_bindings': evaluated,
                       'matching_overflows': overflow_count, 'elapsed_seconds': round(time.monotonic()-started, 2),
                       'criterion': (('maximum conservative event points' if objective == 'event_pt' else
                                      'maximum conservative event badges') if objective != 'score' else
                                     'maximum minimum theoretical score over 120 AP skill orders' if method == 'ap' else
                                     'maximum skip score')},
            'source': {'snapshot': data.snapshot_label, 'event_id': 1, 'basis': 'model_estimate'}}
