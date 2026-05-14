"""Persistent manuscript storage and change detection."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

from config import Config


class ManuscriptStorage:
    def __init__(self, data_file: str):
        self.data_file = data_file
        self._ensure_data_dir()

    def _ensure_data_dir(self) -> None:
        data_dir = os.path.dirname(self.data_file)
        if data_dir:
            os.makedirs(data_dir, exist_ok=True)

    def load_manuscripts(self) -> Dict:
        if not os.path.exists(self.data_file):
            return {}
        try:
            with open(self.data_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            print(f"Failed to read data file: {exc}")
            return {}

    def save_manuscripts(self, manuscripts: Dict) -> None:
        cleaned = self._cleanup_old_records(manuscripts, Config.RETENTION_DAYS)
        tmp_file = f"{self.data_file}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as file:
            json.dump(cleaned, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")
        os.replace(tmp_file, self.data_file)
        print(f"Saved manuscript data to {self.data_file}")

    @staticmethod
    def _parse_time(value: str | None) -> datetime | None:
        if not value:
            return None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        return None

    def _cleanup_old_records(self, manuscripts: Dict, days: int) -> Dict:
        if days <= 0:
            return manuscripts
        threshold = datetime.now() - timedelta(days=days)
        cleaned = {}
        removed = 0
        for key, data in manuscripts.items():
            if data.get("archived"):
                cleaned[key] = data
                continue
            last_checked = self._parse_time(data.get("last_checked"))
            if last_checked is None or last_checked >= threshold:
                cleaned[key] = data
            else:
                removed += 1
        if removed:
            print(f"Removed {removed} stale active manuscript record(s).")
        return cleaned

    @staticmethod
    def _key(manuscript: Dict) -> str:
        source = str(manuscript.get("source", "unknown")).strip() or "unknown"
        manuscript_id = str(manuscript.get("id", "")).strip()
        title = str(manuscript.get("title", "")).strip()
        return f"{source}:{manuscript_id or title}"

    def compare_and_update(self, new_manuscripts: List[Dict]) -> List[Dict]:
        old_data = self.load_manuscripts()
        updated_data = old_data.copy()
        changed = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        seen_keys = set()
        for manuscript in new_manuscripts:
            key = self._key(manuscript)
            if key in seen_keys:
                continue
            seen_keys.add(key)

            current_status = str(manuscript.get("status", "Unknown")).strip() or "Unknown"
            title = str(manuscript.get("title", "Untitled")).strip() or "Untitled"
            old_record = old_data.get(key)
            old_archived = bool(old_record and old_record.get("archived"))
            now_terminal = Config.is_terminal_status(current_status)

            if old_archived:
                # Terminal articles are intentionally ignored after archival.
                updated_data[key] = {
                    **old_record,
                    "last_seen_status": current_status,
                    "last_checked": current_time,
                }
                continue

            if old_record:
                old_status = old_record.get("status")
                if old_status != current_status:
                    changed.append(
                        {
                            "id": manuscript.get("id", ""),
                            "title": title,
                            "source": manuscript.get("source", "Unknown"),
                            "old_status": old_status,
                            "new_status": current_status,
                            "changed_at": current_time,
                            "url": manuscript.get("url", ""),
                        }
                    )
                    print(f"Status changed: {title}: {old_status} -> {current_status}")
            else:
                print(f"New manuscript recorded: {title} ({current_status})")

            record = {
                "id": manuscript.get("id", ""),
                "title": title,
                "status": current_status,
                "source": manuscript.get("source", "Unknown"),
                "url": manuscript.get("url", ""),
                "last_checked": current_time,
                "first_seen": old_record.get("first_seen", current_time) if old_record else current_time,
                "archived": now_terminal,
            }
            if now_terminal:
                record["archived_at"] = old_record.get("archived_at", current_time) if old_record else current_time
                record["archive_reason"] = "terminal_status"
                print(f"Archived terminal manuscript: {title} ({current_status})")
            updated_data[key] = record

        self.save_manuscripts(updated_data)
        print(f"Processed {len(seen_keys)} manuscript key(s).")
        return changed

    def get_all_manuscripts(self, include_archived: bool = False) -> List[Dict]:
        records = list(self.load_manuscripts().values())
        if include_archived:
            return records
        return [record for record in records if not record.get("archived")]

    def clear_data(self) -> None:
        if os.path.exists(self.data_file):
            os.remove(self.data_file)
            print(f"Removed data file: {self.data_file}")