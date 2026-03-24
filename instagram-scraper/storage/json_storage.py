from __future__ import annotations

import json
from pathlib import Path

from models.video_metadata import StorageResult, VideoMetadata


class JsonVideoStorage:
    def __init__(self, file_path: str | Path) -> None:
        self._file_path = Path(file_path)

    def load_all(self) -> list[VideoMetadata]:
        self._ensure_file()

        with self._file_path.open("r", encoding="utf-8") as file:
            raw_data = json.load(file)

        if not isinstance(raw_data, list):
            raise ValueError(f"Expected a list in {self._file_path}")

        return [VideoMetadata.model_validate(item) for item in raw_data]

    def append_unique(self, items: list[VideoMetadata]) -> StorageResult:
        existing_items = self.load_all()
        existing_ids = {item.video_id for item in existing_items}

        inserted_count = 0
        skipped_duplicates = 0

        for item in items:
            if item.video_id in existing_ids:
                skipped_duplicates += 1
                continue

            existing_items.append(item)
            existing_ids.add(item.video_id)
            inserted_count += 1

        self._write_all(existing_items)
        return StorageResult(
            received_count=len(items),
            inserted_count=inserted_count,
            skipped_duplicates=skipped_duplicates,
        )

    def _ensure_file(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self._file_path.exists():
            self._file_path.write_text("[]", encoding="utf-8")

    def _write_all(self, items: list[VideoMetadata]) -> None:
        self._ensure_file()
        payload = [item.model_dump(mode="json") for item in items]
        temp_path = self._file_path.with_suffix(f"{self._file_path.suffix}.tmp")

        with temp_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2, ensure_ascii=False)
        temp_path.replace(self._file_path)
