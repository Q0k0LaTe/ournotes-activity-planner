"""Native workbench regressions and browser oracle fixtures, synthetic only."""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'browser/tests'))
from baseline import load_baseline
load_baseline(ROOT / 'work/workbench-tests', optimized=True)
sys.path.insert(0, str(ROOT / 'workbench'))
import team_candidates as t
from sample import sample

if __name__ == '__main__':
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'workbench/tests'))
    if not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful():
        raise SystemExit(1)
    data = t.p.Data()
    dest = ROOT / 'work/validation'
    dest.mkdir(parents=True, exist_ok=True)
    request = sample(data)
    request['team_settings'].update(count=5, strategy='balanced', required_leader_id=59,
        required_bindings=[{'member_id': 59, 'snap_id': 33}], min_event_bonus_10000=100)
    result = t.optimize(request, data)
    (dest / 'workbench-native.json').write_text(json.dumps({'input': request, 'result': result}, ensure_ascii=False), 'utf-8')
    # New-event skills must agree in native Python and the shipped WASM runtime.
    import simulation
    halloween = sample(data)
    mids, sids = [71, 72, 73, 74, 59], [70, 75, 76, 77, 74]
    halloween['candidate_member_ids'], halloween['candidate_snap_ids'] = mids, sids
    halloween['profile']['inventory'] = {
        'members': [{'id': mid, 'level': 20, 'training_count': 0, 'awakening_count': 0,
                     'live_skill_level': 1, 'gekisou_skill_level': 1} for mid in mids],
        'snaps': [{'id': sid, 'level': 20, 'limit_break_count': 0} for sid in sids]}
    halloween['fixed_team'] = {'member_ids': mids, 'snap_ids': sids, 'leader_id': 72}
    halloween['team_settings'].update(count=1, required_leader_id=72,
        required_bindings=[{'member_id': mid, 'snap_id': sid} for mid, sid in zip(mids, sids)])
    team = t.evaluate(halloween, data)['teams'][0]
    recommended = t.optimize(halloween, data)['teams'][0]
    assert (recommended['power'], recommended['skill_area_raw']) == (team['power'], team['skill_area_raw'])
    cases = []
    for mode, song in (('normal', 100102), ('challenge', 100115)):
        raw = {'input': halloween, 'team': team, 'song_id': song, 'mode': mode,
               'difficulty': 'expert', 'method': 'ap', 'consumed': 200 if mode == 'challenge' else 4}
        cases.append({'input': raw, 'expected': simulation.simulate(raw, data)})
    (dest / 'halloween-native.json').write_text(json.dumps(cases, ensure_ascii=False), 'utf-8')
