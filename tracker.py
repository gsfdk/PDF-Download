import json
import os

TRACKER_FILE = os.path.join(os.path.dirname(__file__), "downloaded.json")


def _load() -> set:
    if not os.path.exists(TRACKER_FILE):
        return set()
    with open(TRACKER_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def _save(records: set):
    with open(TRACKER_FILE, "w", encoding="utf-8") as f:
        json.dump(list(records), f, indent=2)


def is_downloaded(message_id: str, attachment_id: str) -> bool:
    records = _load()
    return f"{message_id}::{attachment_id}" in records


def mark_downloaded(message_id: str, attachment_id: str):
    records = _load()
    records.add(f"{message_id}::{attachment_id}")
    _save(records)
