"""Tests for the dependency-free helpers in vtt.rag.ingest (no Docling needed)."""
import json

from vtt.rag.ingest import (
    load_source_info,
    source_metadata,
    split_inline_rooms,
    strip_watermarks,
)


def test_strip_watermarks_removes_order_lines_only():
    md = "Room text.\n\nJane Doe (Order #12345678)\n\nMore text."
    out = strip_watermarks(md)
    assert "Order #" not in out
    assert "Room text." in out and "More text." in out


def test_inline_rooms_split_with_clean_labels():
    text = (
        "## Level Dungeon Key\n\nIntro notes.\n\n"
        "1.  Owlbear Lair: musty caves.\n\nThe owlbear fights.\n\n"
        "2. Entry  Doors: two oak doors.\n\n"
        "3. Guard Room: empty.\n"
    )
    pieces = split_inline_rooms(text, "Level Dungeon Key")
    labels = [label for _, label in pieces]
    assert labels == [
        "Level Dungeon Key",
        "Room 1: Owlbear Lair",
        "Room 2: Entry Doors",
        "Room 3: Guard Room",
    ]
    assert "The owlbear fights." in pieces[1][0]


def test_short_or_unordered_lists_are_left_alone():
    two = "1. One: a\n2. Two: b\n"
    assert split_inline_rooms(two, "S") == [(two, "S")]
    unordered = "3. C: a\n1. A: b\n2. B: c\n"
    assert split_inline_rooms(unordered, "S") == [(unordered, "S")]
    repeats = "1. A: a\n2. B: b\n1. C: c\n2. D: d\n"
    assert split_inline_rooms(repeats, "S") == [(repeats, "S")]


def test_two_column_shuffle_still_splits():
    text = "".join(f"{n}. Room {n}: text\n" for n in (1, 2, 3, 4, 6, 7, 5, 8, 9))
    labels = [label for _, label in split_inline_rooms(text, "Key")]
    assert len(labels) == 9 and "Room 5: Room 5" in labels


def test_source_metadata_longest_prefix_and_default(tmp_path):
    (tmp_path / "sources.json").write_text(json.dumps({
        "FR": {"era": "generic"},
        "FRQ1": {"era": "c. 1360 DR", "edition": "AD&D 2e"},
    }))
    info = load_source_info(str(tmp_path))
    assert source_metadata("FRQ1_Haunted.pdf", info) == {"era": "c. 1360 DR", "edition": "AD&D 2e"}
    assert source_metadata("B3_Palace.pdf", info) == {"era": "unknown", "edition": "unknown"}
    assert load_source_info(str(tmp_path / "missing")) == {}
