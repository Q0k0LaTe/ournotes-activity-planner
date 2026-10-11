"""Add the pinned international Abracadabra EX Snapshot to the JP baseline."""

from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
UPDATE = ROOT / "data_updates/2026-10-11/snap-70.json"


def _json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def apply_snap_update(overrides, manifest, entries):
    patch = json.loads(UPDATE.read_text(encoding="utf-8"))
    if manifest["data_commit"] != patch["base_data_commit"]:
        raise ValueError("Snap update does not match the pinned JP snapshot")
    if patch["snap_ids"] != [70] or set(patch["tables"]) != {"MasterSupportCard", "MasterText"}:
        raise ValueError("Unexpected Abracadabra update contents")
    for name, addition in patch["tables"].items():
        relative = f"raw/{name}.json"
        path = "research/2026-10-01/" + relative
        base = overrides[path]
        entry = entries[relative]
        if hashlib.sha256(base).hexdigest() != entry["sha256"]:
            raise ValueError(f"Base snap table changed: {name}")
        document = json.loads(base)
        rows = document["_allData"]
        existing = {row["_id"] for row in rows}
        added_ids = [row["_id"] for row in addition["rows"]]
        if len(set(added_ids)) != len(added_ids) or existing.intersection(added_ids):
            raise ValueError(f"Duplicate snap update ID: {name}")
        document["_allData"] = rows + addition["rows"]
        raw = _json_bytes(document)
        overrides[path] = raw
        blob = b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        entry.update({"sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                      "row_count": len(document["_allData"]), "repository": "local-derived",
                      "commit": patch["source_commit"], "path": path, "source_url": None,
                      "git_blob_sha": hashlib.sha1(blob).hexdigest(),
                      "derived_from": [{"repository": manifest["data_repository"],
                                        "commit": patch["base_data_commit"]},
                                       {"repository": patch["source_repository"],
                                        "commit": patch["source_commit"],
                                        "path": f"{patch['source_path']}/{name}.json",
                                        "sha256": addition["source_sha256"],
                                        "git_blob_sha": addition["source_blob_sha"]}]})
    manifest["table_row_count"] += sum(len(v["rows"]) for v in patch["tables"].values())
    manifest["card_updates"] = [{k: patch[k] for k in
                                 ("update_id", "source_repository", "source_commit", "snap_ids")}]
    return patch


def copy_snap_image(destination, patch):
    info = patch["thumbnail"]
    source = UPDATE.parent / info["file"]
    raw = source.read_bytes()
    if len(raw) != info["bytes"] or hashlib.sha256(raw).hexdigest() != info["sha256"]:
        raise ValueError("Abracadabra thumbnail checksum mismatch")
    target = destination / "card-images" / info["file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    manifest_path = destination / "card-images/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["images"].append({"kind": "snaps", "card_id": 70, "asset_id": 70,
                               "source_url": info["source_url"],
                               "saved_path": "web/card-images/" + info["file"],
                               "sha256": info["sha256"], "bytes": len(raw)})
    manifest_path.write_bytes(_json_bytes(manifest))
