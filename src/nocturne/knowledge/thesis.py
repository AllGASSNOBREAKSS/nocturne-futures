"""Governed analyst thesis records, separate from runtime model inputs."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class AnalystThesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thesis_id: str = Field(min_length=1)
    author: str = Field(min_length=1)
    created_at: str
    information_cutoff: str
    instrument_id: str = Field(min_length=1)
    side: str
    thesis_tags: list[str] = Field(default_factory=list)
    referenced_levels: list[float] = Field(default_factory=list)
    note_refs: list[str] = Field(default_factory=list)
    rationale: str = Field(min_length=1)
    invalidation: str = Field(min_length=1)
    horizon_seconds: int = Field(ge=1)
    confidence_type: str = "QUALITATIVE"
    expire_at: str | None = None
    followup_outcome: str | None = None


class ThesisRegistry:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _all(self) -> list[AnalystThesis]:
        if not self.path.exists():
            return []
        return [
            AnalystThesis.model_validate_json(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def append(self, thesis: AnalystThesis) -> None:
        if any(item.thesis_id == thesis.thesis_id for item in self._all()):
            raise ValueError(f"duplicate thesis_id {thesis.thesis_id}")
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(thesis.model_dump_json() + "\n")

    def list(self) -> list[AnalystThesis]:
        return self._all()

    def get(self, thesis_id: str) -> AnalystThesis | None:
        for thesis in self._all():
            if thesis.thesis_id == thesis_id:
                return thesis
        return None

    def resolve(self, thesis_id: str, outcome: str) -> AnalystThesis:
        thesis = self.get(thesis_id)
        if thesis is None:
            raise ValueError(f"unknown thesis {thesis_id}")
        updated = thesis.model_copy(update={"followup_outcome": outcome})
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(updated.model_dump_json() + "\n")
        return updated
