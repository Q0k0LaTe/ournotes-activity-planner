"""Apply the pinned October 9 public Master and asset update to the release ZIP."""

from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
UPDATE = ROOT / "data_updates/2026-10-09"
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
    overrides[manifest_path] = _json_bytes(manifest)
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
    return overrides, patch


def copy_game_images(destination, patch):
    manifest_path = destination / "card-images/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_rows = [{"kind": "members", "card_id": 64, "asset_id": 64,
                   "source_url": "https://assets.bdon.moe/jp/ja/MemberCard/64/member_thumbnail/member_thumbnail.webp",
                   "saved_path": "web/card-images/members-64.webp",
                   "sha256": "e465337510e90962229a24fe03c23f9b55330073bb70e4e70d3bab0d313a52e1",
                   "file": ROOT / "data_updates/2026-10-03/members-64.webp"}]
    image_rows += [{"kind": row["kind"], "card_id": row["id"], "asset_id": row["id"],
                    "source_url": row["source_url"], "saved_path": "web/card-images/" + row["file"],
                    "sha256": row["sha256"], "file": UPDATE / row["file"]} for row in patch["images"]]
    for row in image_rows:
        payload = row.pop("file").read_bytes()
        if hashlib.sha256(payload).hexdigest() != row["sha256"]:
            raise ValueError(f"Card image checksum mismatch: {row['saved_path']}")
        target = destination / row["saved_path"].removeprefix("web/")
        target.write_bytes(payload)
        manifest["images"].append({**row, "bytes": len(payload)})
    manifest_path.write_bytes(_json_bytes(manifest))
