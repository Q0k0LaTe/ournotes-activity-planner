"""Apply pinned JP Master updates and the international Snapshot overlay."""

from pathlib import Path
import hashlib
import json
from snap_updates import apply_snap_update, copy_snap_image

ROOT = Path(__file__).resolve().parents[1]
UPDATE = ROOT / "data_updates/2026-10-09"
LATEST = ROOT / "data_updates/2026-10-18"
BASE_SNAPSHOT = "research/2026-10-01/"


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def game_overrides(archive, prefix):
    patch = json.loads((UPDATE / "manifest.json").read_text(encoding="utf-8"))
    manifest_path = BASE_SNAPSHOT + "source_manifest.json"
    manifest = json.loads(archive.read(prefix + manifest_path))
    if manifest["data_commit"] != patch["base_data_commit"]:
        raise ValueError("Game update does not match the pinned base snapshot")
    entries = {entry["local_path"]: entry for entry in manifest["files"]}
    overrides = {}
    for filename, source in patch["tables"].items():
        relative = "raw/" + filename
        previous = archive.read(prefix + BASE_SNAPSHOT + relative)
        if hashlib.sha256(previous).hexdigest() != entries[relative]["sha256"]:
            raise ValueError(f"Base table changed: {filename}")
        payload = (UPDATE / relative).read_bytes()
        if hashlib.sha256(payload).hexdigest() != source["sha256"]:
            raise ValueError(f"Updated table checksum mismatch: {filename}")
        rows = json.loads(payload)["_allData"]
        if len(rows) != source["row_count"] or len({r["_id"] for r in rows}) != len(rows):
            raise ValueError(f"Updated table rows invalid: {filename}")
        overrides[BASE_SNAPSHOT + relative] = payload
        entry = entries[relative]
        entry.update({"commit": patch["source_commit"],
                      "source_url": f"https://raw.githubusercontent.com/{patch['source_repository']}/{patch['source_commit']}/{patch['source_path']}/{filename}",
                      "git_blob_sha": source["git_blob_sha"], "sha256": source["sha256"],
                      "bytes": len(payload), "row_count": len(rows)})
    # Every unchanged table is byte-identical in the pinned source commit.
    # Keep its original hash and point provenance to the same source revision.
    changed = {"raw/" + name for name in patch["tables"]}
    unchanged = {relative for relative in entries if relative.startswith("raw/")} - changed
    if unchanged != {"raw/" + name for name in patch["unchanged_tables"]}:
        raise ValueError("Updated source table inventory is incomplete")
    for relative, entry in entries.items():
        if relative in unchanged:
            expected = patch["unchanged_tables"][Path(relative).name]
            if entry["sha256"] != expected["sha256"] or entry["git_blob_sha"] != expected["git_blob_sha"]:
                raise ValueError(f"Unchanged source table differs from pinned revision: {relative}")
            entry["commit"] = patch["source_commit"]
            entry["source_url"] = (f"https://raw.githubusercontent.com/{patch['source_repository']}/"
                                   f"{patch['source_commit']}/{patch['source_path']}/{Path(relative).name}")
    manifest["data_commit"] = patch["source_commit"]
    manifest["collected_at_utc"] = "2026-10-09T18:14:00+00:00"
    manifest["snapshot_version_scope"] = "Base archive game-client version metadata; raw Master tables refreshed at data_commit"
    manifest["table_row_count"] = sum(entry["row_count"] for path, entry in entries.items() if path.startswith("raw/"))
    manifest["game_updates"] = [{"update_id": patch["update_id"], "source_commit": patch["source_commit"],
                                  "active_event_id": patch["active_event_id"]}]
    manifest.pop("card_updates", None)
    normalized = json.loads((UPDATE / "event_2.json").read_text(encoding="utf-8"))
    if normalized["event_id"] != patch["active_event_id"]:
        raise ValueError("Normalized event ID does not match the update")
    overrides[BASE_SNAPSHOT + "normalized/event_2.json"] = _json_bytes(normalized)
    conversion = json.loads(archive.read(prefix + BASE_SNAPSHOT + "validation/public_chart_conversion.json"))
    conversion["data_commit"] = patch["source_commit"]
    conversion["charts"].extend(json.loads((UPDATE / "chart_conversion.json").read_text(encoding="utf-8"))["charts"])
    conversion["charts_checked"] = len(conversion["charts"])
    overrides[BASE_SNAPSHOT + "validation/public_chart_conversion.json"] = _json_bytes(conversion)
    for chart in json.loads((UPDATE / "chart_conversion.json").read_text(encoding="utf-8"))["charts"]:
        path = chart["saved_path"]
        payload = (UPDATE / path).read_bytes()
        if hashlib.sha256(payload).hexdigest() != chart["converted_record_sha256"]:
            raise ValueError(f"Converted chart checksum mismatch: {path}")
        overrides[BASE_SNAPSHOT + path] = payload
    latest = json.loads((LATEST / "manifest.json").read_text(encoding="utf-8"))
    if latest["base_data_commit"] != manifest["data_commit"]:
        raise ValueError("Latest update does not match the previous JP snapshot")
    for filename, source in latest["tables"].items():
        relative = "raw/" + filename
        path = BASE_SNAPSHOT + relative
        previous = overrides.get(path, archive.read(prefix + path))
        if hashlib.sha256(previous).hexdigest() != entries[relative]["sha256"]:
            raise ValueError(f"Previous table changed: {filename}")
        payload = (LATEST / relative).read_bytes()
        if hashlib.sha256(payload).hexdigest() != source["sha256"]:
            raise ValueError(f"Latest table checksum mismatch: {filename}")
        rows = json.loads(payload)["_allData"]
        if len(rows) != source["row_count"] or len({r["_id"] for r in rows}) != len(rows):
            raise ValueError(f"Latest table rows invalid: {filename}")
        overrides[path] = payload
        entries[relative].update({"commit": latest["source_commit"],
                                  "source_url": f"https://raw.githubusercontent.com/{latest['source_repository']}/{latest['source_commit']}/{latest['source_path']}/{filename}",
                                  "git_blob_sha": source["git_blob_sha"], "sha256": source["sha256"],
                                  "bytes": len(payload), "row_count": len(rows)})
    if {"raw/" + name for name in latest["unchanged_tables"]} != {
            path for path in entries if path.startswith("raw/")} - {"raw/" + name for name in latest["tables"]}:
        raise ValueError("Latest source table inventory is incomplete")
    for filename, expected in latest["unchanged_tables"].items():
        entry = entries["raw/" + filename]
        if (entry["sha256"], entry["git_blob_sha"]) != (expected["sha256"], expected["git_blob_sha"]):
            raise ValueError(f"Latest unchanged table differs: {filename}")
        entry["commit"] = latest["source_commit"]
        entry["source_url"] = f"https://raw.githubusercontent.com/{latest['source_repository']}/{latest['source_commit']}/{latest['source_path']}/{filename}"
    manifest["data_commit"] = latest["source_commit"]
    manifest["collected_at_utc"] = latest["collected_at_utc"]
    manifest["table_row_count"] = sum(entry["row_count"] for path, entry in entries.items() if path.startswith("raw/"))
    manifest["game_updates"].append({"update_id": latest["update_id"], "source_commit": latest["source_commit"],
                                      "active_event_id": latest["active_event_id"]})
    normalized = json.loads((LATEST / "event_3.json").read_text(encoding="utf-8"))
    if normalized["event_id"] != latest["active_event_id"]:
        raise ValueError("Latest normalized event ID does not match the update")
    overrides[BASE_SNAPSHOT + "normalized/event_3.json"] = _json_bytes(normalized)
    conversion["data_commit"] = latest["source_commit"]
    chart_report = LATEST / "chart_conversion.json"
    if chart_report.exists():
        charts = json.loads(chart_report.read_text(encoding="utf-8"))["charts"]
        conversion["charts"].extend(charts)
        for chart in charts:
            score_id = chart["score_id"]
            chart_name = f"{score_id // 100 % 10000:04d}_{score_id % 100:02d}.json"
            source_bytes = (LATEST / "charts" / chart_name).read_bytes()
            if hashlib.sha256(source_bytes).hexdigest() != chart["source_sha256"]:
                raise ValueError(f"Source chart checksum mismatch: {chart_name}")
            path = chart["saved_path"]
            payload = (LATEST / path).read_bytes()
            if hashlib.sha256(payload).hexdigest() != chart["converted_record_sha256"]:
                raise ValueError(f"Converted chart checksum mismatch: {path}")
            if json.loads(payload)["scoreId"] != score_id:
                raise ValueError(f"Converted chart score ID mismatch: {path}")
            overrides[BASE_SNAPSHOT + path] = payload
    conversion["charts_checked"] = len(conversion["charts"])
    overrides[BASE_SNAPSHOT + "validation/public_chart_conversion.json"] = _json_bytes(conversion)
    snap_patch = apply_snap_update(overrides, manifest, entries, expected_jp_commit=latest["source_commit"])
    overrides[manifest_path] = _json_bytes(manifest)
    latest["snap_update"] = snap_patch
    return overrides, latest


def copy_game_images(destination, patch):
    manifest_path = destination / "card-images/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_rows = [{"kind": "members", "card_id": 64, "asset_id": 64,
                   "source_url": "https://assets.bdon.moe/jp/ja/MemberCard/64/member_thumbnail/member_thumbnail.webp",
                   "saved_path": "web/card-images/members-64.webp",
                   "sha256": "e465337510e90962229a24fe03c23f9b55330073bb70e4e70d3bab0d313a52e1",
                   "file": ROOT / "data_updates/2026-10-03/members-64.webp"}]
    prior_images = json.loads((UPDATE / "manifest.json").read_text(encoding="utf-8"))["images"]
    image_rows += [{"kind": row["kind"], "card_id": row["id"], "asset_id": row["id"],
                    "source_url": row["source_url"], "saved_path": "web/card-images/" + row["file"],
                    "sha256": row["sha256"], "file": UPDATE / row["file"]} for row in prior_images]
    for row in image_rows:
        payload = row.pop("file").read_bytes()
        if hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise ValueError(f"Card image checksum mismatch: {row['saved_path']}")
        target = destination / row["saved_path"].removeprefix("web/")
        target.write_bytes(payload)
        manifest["images"].append({**row, "bytes": len(payload)})
    for row in patch["images"]:
        if "source_file" in row:
            source_payload = (LATEST / row["source_file"]).read_bytes()
            if hashlib.sha256(source_payload).hexdigest() != row["source_sha256"]:
                raise ValueError(f"Latest source image checksum mismatch: {row['source_file']}")
        payload = (LATEST / row["file"]).read_bytes()
        if len(payload) != row["bytes"] or hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise ValueError(f"Latest card image checksum mismatch: {row['file']}")
        (destination / "card-images" / row["file"]).write_bytes(payload)
        manifest["images"].append({"kind": row["kind"], "card_id": row["id"], "asset_id": row["id"],
                                   "source_url": row["source_url"], "saved_path": "web/card-images/" + row["file"],
                                   "source_sha256": row.get("source_sha256", row["sha256"]),
                                   "conversion": row.get("conversion"),
                                   "sha256": row["sha256"], "bytes": len(payload)})
    manifest_path.write_bytes(_json_bytes(manifest))
    copy_snap_image(destination, patch["snap_update"])
