from nocturne.knowledge import AnalystThesis, ThesisRegistry


def thesis(thesis_id="t1"):
    return AnalystThesis(
        thesis_id=thesis_id,
        author="analyst",
        created_at="2026-11-03T12:00:00Z",
        information_cutoff="2026-11-03T11:55:00Z",
        instrument_id="NQ",
        side="SHORT",
        thesis_tags=["failed_auction"],
        referenced_levels=[28800.0],
        note_refs=["vault/note.md"],
        rationale="VAH rejection with weak breadth",
        invalidation="close above 28950",
        horizon_seconds=86400,
    )


def test_thesis_registry_roundtrip(tmp_path):
    registry = ThesisRegistry(tmp_path / "theses.jsonl")
    registry.append(thesis())
    assert registry.get("t1").side == "SHORT"
    assert len(registry.list()) == 1


def test_duplicate_thesis_rejected(tmp_path):
    registry = ThesisRegistry(tmp_path / "theses.jsonl")
    registry.append(thesis())
    try:
        registry.append(thesis())
    except ValueError:
        pass
    else:
        raise AssertionError("duplicate thesis was accepted")


def test_resolve_thesis(tmp_path):
    registry = ThesisRegistry(tmp_path / "theses.jsonl")
    registry.append(thesis())
    updated = registry.resolve("t1", "LOSS")
    assert updated.followup_outcome == "LOSS"
