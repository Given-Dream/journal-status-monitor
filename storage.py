"""Persistent manuscript storage and change detection."""
from __future__ import annotations

import json
import os
import re
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
        cleaned = self._merge_duplicate_records(manuscripts)
        cleaned = self._cleanup_old_records(cleaned, Config.RETENTION_DAYS)
        tmp_file = f"{self.data_file}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as file:
            json.dump(cleaned, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")
        os.replace(tmp_file, self.data_file)
        print(f"Saved manuscript data to {self.data_file}")

    def _meta_file(self) -> str:
        root, ext = os.path.splitext(self.data_file)
        return f"{root}.meta{ext or '.json'}"

    def load_meta(self) -> Dict:
        meta_file = self._meta_file()
        if not os.path.exists(meta_file):
            return {}
        try:
            with open(meta_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            print(f"Failed to read meta file: {exc}")
            return {}

    def save_meta(self, meta: Dict) -> None:
        meta_file = self._meta_file()
        tmp_file = f"{meta_file}.tmp"
        with open(tmp_file, "w", encoding="utf-8") as file:
            json.dump(meta, file, ensure_ascii=False, indent=2, sort_keys=True)
            file.write("\n")
        os.replace(tmp_file, meta_file)
        print(f"Saved monitor meta to {meta_file}")

    def daily_report_already_sent(self, today: str | None = None) -> bool:
        today = today or datetime.now().strftime("%Y-%m-%d")
        return self.load_meta().get("last_daily_report_date") == today

    def mark_daily_report_sent(self, today: str | None = None) -> None:
        today = today or datetime.now().strftime("%Y-%m-%d")
        meta = self.load_meta()
        meta["last_daily_report_date"] = today
        meta["last_daily_report_sent_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_meta(meta)

    @staticmethod
    def _status_score(value: object) -> int:
        text = str(value or "").lower()
        if any(keyword in text for keyword in ("accept", "accepted", "published")):
            return 100
        if any(keyword in text for keyword in ("reject", "rejected", "withdrawn")):
            return 90
        if "decision" in text:
            return 70
        if "revision" in text:
            return 50
        if "review" in text:
            return 40
        if "submitted" in text:
            return 30
        return 0

    @staticmethod
    def _looks_like_date_token(value: object) -> bool:
        text = str(value or "").strip().lower()
        months = r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
        patterns = [
            rf"(?:{months})[-_ ]?\d{{2,4}}",
            rf"\d{{1,2}}[-_ ](?:{months})[-_ ]\d{{2,4}}",
            r"\d{4}[-_/]\d{1,2}[-_/]\d{1,2}",
        ]
        return any(re.fullmatch(pattern, text) for pattern in patterns)

    @staticmethod
    def _id_quality(value: object) -> int:
        text = str(value or "").strip()
        if not text:
            return 0
        if ManuscriptStorage._looks_like_date_token(text):
            return -10
        if re.search(r"[A-Za-z]", text) and re.search(r"\d", text):
            return 10
        if re.search(r"\d", text):
            return 5
        return 1

    @staticmethod
    def _strip_trailing_status_from_title(value: object) -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        while True:
            match = re.search(r"\s+(\((?:[^()]|\([^()]*\))*\))\s*$", text)
            if not match:
                break
            suffix = match.group(1)
            if ManuscriptStorage._status_score(suffix) <= 0:
                break
            text = text[: match.start()].strip()
        return text

    @staticmethod
    def _identity_title(value: object) -> str:
        title = ManuscriptStorage._strip_trailing_status_from_title(value)
        title = re.sub(r"\s+", " ", title).strip().lower()
        title = re.sub(r"[^\w\s:;-]", "", title)
        return re.sub(r"\s+", " ", title).strip()

    @staticmethod
    def _display_title(value: object) -> str:
        return ManuscriptStorage._strip_trailing_status_from_title(value) or str(value or "").strip() or "Untitled"

    @staticmethod
    def _prefer_record(existing: Dict, candidate: Dict) -> Dict:
        existing_score = ManuscriptStorage._status_score(existing.get("status"))
        candidate_score = ManuscriptStorage._status_score(candidate.get("status"))
        chosen = candidate.copy() if candidate_score > existing_score else existing.copy()
        other = existing if chosen is candidate else candidate
        if ManuscriptStorage._id_quality(other.get("id")) > ManuscriptStorage._id_quality(chosen.get("id")):
            chosen["id"] = other.get("id", "")
        chosen["title"] = ManuscriptStorage._display_title(chosen.get("title"))
        if existing.get("first_seen") and candidate.get("first_seen"):
            chosen["first_seen"] = min(str(existing.get("first_seen")), str(candidate.get("first_seen")))
        if existing.get("archived") or candidate.get("archived") or Config.is_terminal_status(chosen.get("status")):
            chosen["archived"] = True
            chosen.setdefault("archived_at", existing.get("archived_at") or candidate.get("archived_at") or chosen.get("last_checked"))
            chosen.setdefault("archive_reason", "terminal_status")
        return chosen

    def _merge_duplicate_records(self, manuscripts: Dict) -> Dict:
        merged: Dict = {}
        for key, data in manuscripts.items():
            if not isinstance(data, dict):
                continue
            source = str(data.get("source", "unknown")).strip() or "unknown"
            identity = self._identity_title(data.get("title")) or str(data.get("id", "")).strip() or str(key)
            merged_key = f"{source}:{identity}"
            normalized = data.copy()
            normalized["title"] = self._display_title(normalized.get("title"))
            if merged_key in merged:
                merged[merged_key] = self._prefer_record(merged[merged_key], normalized)
            else:
                merged[merged_key] = normalized
        return merged

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
        identity_title = ManuscriptStorage._identity_title(title)
        return f"{source}:{identity_title or manuscript_id or title}"

    @staticmethod
    def _first_seen_old_status() -> str:
        return "\u9996\u6b21\u8bb0\u5f55\uff08\u65e0\u5386\u53f2\u72b6\u6001\uff09"

    @staticmethod
    def _is_silent_first_seen_status(status: object) -> bool:
        text = str(status or "").strip().lower()
        if not text or text == "unknown":
            return True
        silent_keywords = getattr(
            Config,
            "FIRST_SEEN_SILENT_STATUS_KEYWORDS",
            ["submitted", "submission", "draft", "incomplete"],
        )
        return any(keyword in text for keyword in silent_keywords)

    @staticmethod
    def _notify_on_first_seen(status: object) -> bool:
        if not getattr(Config, "NOTIFY_ON_FIRST_SEEN", True):
            return False
        if Config.is_terminal_status(status):
            return False
        return not ManuscriptStorage._is_silent_first_seen_status(status)

    @staticmethod
    def _change_item(manuscript: Dict, title: str, old_status: object, new_status: str, changed_at: str) -> Dict:
        return {
            "id": manuscript.get("id", ""),
            "title": title,
            "source": manuscript.get("source", "Unknown"),
            "old_status": old_status,
            "new_status": new_status,
            "changed_at": changed_at,
            "url": manuscript.get("url", ""),
        }

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
            title = self._display_title(manuscript.get("title", "Untitled"))
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
                        self._change_item(manuscript, title, old_status, current_status, current_time)
                    )
                    print(f"Status changed: {title}: {old_status} -> {current_status}")
            else:
                print(f"New manuscript recorded: {title} ({current_status})")
                if self._notify_on_first_seen(current_status):
                    changed.append(
                        self._change_item(
                            manuscript,
                            title,
                            self._first_seen_old_status(),
                            current_status,
                            current_time,
                        )
                    )
                    print(f"First-seen status notification queued: {title}: {current_status}")

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
