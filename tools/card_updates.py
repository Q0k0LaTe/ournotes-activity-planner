"""Apply narrowly scoped, hash-pinned card additions to the public runtime."""

from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
UPDATE = ROOT / "data_updates/2026-10-03/member-64.json"


def card_overrides(archive, prefix):
    patch = json.loads(UPDATE.read_text(encoding="utf-8"))
    manifest_path = "research/2026-10-01/source_manifest.json"
    manifest = json.loads(archive.read(prefix + manifest_path))
    if manifest["data_commit"] != patch["base_data_commit"]:
        raise ValueError("Card update does not match the pinned base snapshot")
    entries = {entry["local_path"]: entry for entry in manifest["files"]}
    overrides = {}
    for name, addition in patch["tables"].items():
        relative = f"raw/{name}.json"
        path = "research/2026-10-01/" + relative
        base = archive.read(prefix + path)
        entry = entries[relative]
        if hashlib.sha256(base).hexdigest() != entry["sha256"]:
            raise ValueError(f"Base card table changed: {name}")
        document = json.loads(base)
        rows = document["_allData"]
        existing = {row["_id"] for row in rows}
        added_ids = [row["_id"] for row in addition["rows"]]
        if len(set(added_ids)) != len(added_ids) or existing.intersection(added_ids):
            raise ValueError(f"Duplicate card update ID: {name}")
        document["_allData"] = rows + addition["rows"]
        raw = (json.dumps(document, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
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
                                  ("update_id", "source_repository", "source_commit", "member_ids")}]
    overrides[manifest_path] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    return overrides, patch


def copy_card_images(destination, patch):
    info = patch["thumbnail"]
    source = UPDATE.parent / info["file"]
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != info["sha256"]:
        raise ValueError("Card thumbnail checksum mismatch")
    target = destination / "card-images" / info["file"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw)
    manifest_path = destination / "card-images/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["images"].append({"kind": "members", "card_id": patch["member_ids"][0],
                               "asset_id": patch["member_ids"][0],
                               "source_url": info["source_url"],
                               "saved_path": "web/card-images/" + info["file"],
                               "sha256": info["sha256"], "bytes": len(raw)})
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
