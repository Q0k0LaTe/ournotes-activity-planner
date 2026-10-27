"""Apply the pinned JP Master update chain, preserving historical events."""

from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
UPDATES = tuple(ROOT / 'data_updates' / date for date in ('2026-10-09', '2026-10-18', '2026-10-27'))
LATEST = UPDATES[-1]
BASE_SNAPSHOT = 'research/2026-10-01/'


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def game_overrides(archive, prefix):
    manifest_path = BASE_SNAPSHOT + 'source_manifest.json'
    manifest = json.loads(archive.read(prefix + manifest_path))
    entries = {entry['local_path']: entry for entry in manifest['files']}
    conversion = json.loads(archive.read(prefix + BASE_SNAPSHOT + 'validation/public_chart_conversion.json'))
    overrides = {}
    manifest['game_updates'] = []
    manifest.pop('card_updates', None)
    for directory in UPDATES:
        patch = json.loads((directory / 'manifest.json').read_bytes())
        if patch['base_data_commit'] != manifest['data_commit']:
            raise ValueError(f'Game update does not match previous snapshot: {directory.name}')
        changed = {'raw/' + name for name in patch['tables']}
        unchanged = {path for path in entries if path.startswith('raw/')} - changed
        if unchanged != {'raw/' + name for name in patch['unchanged_tables']}:
            raise ValueError('Updated source table inventory is incomplete')
        for filename, source in patch['tables'].items():
            relative = 'raw/' + filename
            path = BASE_SNAPSHOT + relative
            previous = overrides[path] if path in overrides else archive.read(prefix + path)
            if hashlib.sha256(previous).hexdigest() != entries[relative]['sha256']:
                raise ValueError(f'Previous table changed: {filename}')
            payload = (directory / relative).read_bytes()
            blob = b'blob ' + str(len(payload)).encode('ascii') + b'\0' + payload
            if (hashlib.sha256(payload).hexdigest(), hashlib.sha1(blob).hexdigest()) != (source['sha256'], source['git_blob_sha']):
                raise ValueError(f'Updated table checksum mismatch: {filename}')
            rows = json.loads(payload)['_allData']
            if len(rows) != source['row_count'] or len({r['_id'] for r in rows}) != len(rows):
                raise ValueError(f'Updated table rows invalid: {filename}')
            overrides[path] = payload
            entries[relative].update(sha256=source['sha256'], git_blob_sha=source['git_blob_sha'],
                                     bytes=len(payload), row_count=len(rows))
        for filename, expected in patch['unchanged_tables'].items():
            entry = entries['raw/' + filename]
            if (entry['sha256'], entry['git_blob_sha']) != (expected['sha256'], expected['git_blob_sha']):
                raise ValueError(f'Unchanged source table differs: {filename}')
        for relative, entry in entries.items():
            if relative.startswith('raw/'):
                entry['commit'] = patch['source_commit']
                entry['source_url'] = (f"https://raw.githubusercontent.com/{patch['source_repository']}/"
                                       f"{patch['source_commit']}/{patch['source_path']}/{Path(relative).name}")
        manifest['data_commit'] = patch['source_commit']
        manifest['collected_at_utc'] = patch.get('collected_at_utc', '2026-10-09T18:14:00+00:00')
        manifest['game_updates'].append({key: patch[key] for key in ('update_id', 'source_commit', 'active_event_id')})
        event_id = patch['active_event_id']
        normalized = json.loads((directory / f'event_{event_id}.json').read_bytes())
        if normalized['event_id'] != event_id or normalized['provenance']['master_commit'] != patch['source_commit']:
            raise ValueError('Normalized event does not match the update')
        overrides[BASE_SNAPSHOT + f'normalized/event_{event_id}.json'] = _json_bytes(normalized)
        charts = json.loads((directory / 'chart_conversion.json').read_bytes())['charts']
        for chart in charts:
            score_id = chart['score_id']
            chart_name = f'{score_id // 100 % 10000:04d}_{score_id % 100:02d}.json'
            # The first increment predates archived original chart assets.
            if 'source_url' in chart:
                source_bytes = (directory / 'charts' / chart_name).read_bytes()
                if hashlib.sha256(source_bytes).hexdigest() != chart['source_sha256']:
                    raise ValueError(f'Source chart checksum mismatch: {chart_name}')
            path = chart['saved_path']
            payload = (directory / path).read_bytes()
            if hashlib.sha256(payload).hexdigest() != chart['converted_record_sha256'] or json.loads(payload)['scoreId'] != score_id:
                raise ValueError(f'Converted chart checksum or ID mismatch: {path}')
            overrides[BASE_SNAPSHOT + path] = payload
        conversion['charts'].extend(charts)
    # JP now includes Abracadabra #70 with its own skill IDs. Keep those rows
    # verbatim; reapplying the older international overlay would duplicate IDs.
    manifest['snapshot_version_scope'] = 'Base archive game-client version metadata; raw Master tables refreshed at data_commit'
    manifest['table_row_count'] = sum(entry['row_count'] for path, entry in entries.items() if path.startswith('raw/'))
    conversion['data_commit'] = patch['source_commit']
    conversion['charts_checked'] = len(conversion['charts'])
    overrides[BASE_SNAPSHOT + 'validation/public_chart_conversion.json'] = _json_bytes(conversion)
    overrides[manifest_path] = _json_bytes(manifest)
    return overrides, patch


def copy_game_images(destination, patch):
    manifest_path = destination / 'card-images/manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    images = {(row['kind'], row['card_id']): row for row in manifest['images']}
    source = ROOT / 'data_updates/2026-10-03/members-64.webp'
    raw = source.read_bytes()
    digest = 'e465337510e90962229a24fe03c23f9b55330073bb70e4e70d3bab0d313a52e1'
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Birthday member thumbnail checksum mismatch')
    (destination / 'card-images/members-64.webp').write_bytes(raw)
    images['members', 64] = {'kind': 'members', 'card_id': 64, 'asset_id': 64,
        'source_url': 'https://assets.bdon.moe/jp/ja/MemberCard/64/member_thumbnail/member_thumbnail.webp',
        'saved_path': 'web/card-images/members-64.webp', 'sha256': digest, 'bytes': len(raw)}
    for directory in UPDATES:
        update = json.loads((directory / 'manifest.json').read_bytes())
        for row in update['images']:
            if 'source_file' in row and hashlib.sha256((directory / row['source_file']).read_bytes()).hexdigest() != row['source_sha256']:
                raise ValueError(f"Source image checksum mismatch: {row['source_file']}")
            payload = (directory / row['file']).read_bytes()
            if len(payload) != row['bytes'] or hashlib.sha256(payload).hexdigest() != row['sha256']:
                raise ValueError(f"Card image checksum mismatch: {row['file']}")
            (destination / 'card-images' / row['file']).write_bytes(payload)
            images[row['kind'], row['id']] = {'kind': row['kind'], 'card_id': row['id'], 'asset_id': row['id'],
                'source_url': row['source_url'], 'saved_path': 'web/card-images/' + row['file'],
                'source_sha256': row.get('source_sha256', row['sha256']), 'conversion': row.get('conversion'),
                'sha256': row['sha256'], 'bytes': len(payload)}
    manifest['images'] = list(images.values())
    manifest_path.write_bytes(_json_bytes(manifest))
