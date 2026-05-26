"""Journal manuscript status monitor."""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import Config, PlatformAccount
from notification import EmailNotifier
from storage import ManuscriptStorage


class JournalMonitor:
    def __init__(self) -> None:
        self.storage = ManuscriptStorage(Config.DATA_FILE)
        self.notifier = EmailNotifier()
        self.driver: webdriver.Chrome | None = None

    def _init_driver(self) -> None:
        options = Options()
        if Config.HEADLESS:
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1440,1200")
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(Config.PAGE_LOAD_TIMEOUT)
        self.driver.implicitly_wait(2)

    def _close_driver(self) -> None:
        if self.driver:
            self.driver.quit()
            self.driver = None

    @property
    def wait(self) -> WebDriverWait:
        if not self.driver:
            raise RuntimeError("Browser driver is not initialized.")
        return WebDriverWait(self.driver, Config.WAIT_SECONDS)

    def _save_debug_artifacts(self, prefix: str) -> None:
        if not Config.SAVE_DEBUG_ARTIFACTS or not self.driver:
            return
        try:
            Path(Config.DEBUG_DIR).mkdir(parents=True, exist_ok=True)
            safe_prefix = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in prefix)
            self.driver.save_screenshot(str(Path(Config.DEBUG_DIR) / f"{safe_prefix}.png"))
            (Path(Config.DEBUG_DIR) / f"{safe_prefix}.html").write_text(
                self.driver.page_source,
                encoding="utf-8",
            )
            print(f"Saved debug artifacts for {prefix}.")
        except Exception as exc:
            print(f"Failed to save debug artifacts: {exc}")

    def _find_first(self, candidates: list[tuple[str, str]], timeout: int = 5):
        if not self.driver:
            raise RuntimeError("Browser driver is not initialized.")
        last_error: Exception | None = None
        for by, selector in candidates:
            try:
                return WebDriverWait(self.driver, timeout).until(EC.presence_of_element_located((by, selector)))
            except Exception as exc:
                last_error = exc
        raise TimeoutException(f"No element matched candidates: {candidates}") from last_error

    def _click_first(self, candidates: list[tuple[str, str]], timeout: int = 5) -> bool:
        if not self.driver:
            raise RuntimeError("Browser driver is not initialized.")
        for by, selector in candidates:
            try:
                element = WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable((by, selector)))
                element.click()
                return True
            except Exception:
                continue
        return False

    def fetch_ieee_manuscripts(self, account: PlatformAccount) -> List[Dict]:
        if not self.driver:
            raise RuntimeError("Browser driver is not initialized.")
        print(f"Opening IEEE ScholarOne: {account.url}")
        self.driver.get(account.url)
        time.sleep(2)

        try:
            email_input = self._find_first(
                [
                    (By.ID, "login"),
                    (By.NAME, "login"),
                    (By.CSS_SELECTOR, "input[type='email']"),
                    (By.CSS_SELECTOR, "input[type='text']"),
                    (By.XPATH, "//input[contains(@placeholder, 'User') or contains(@placeholder, 'Email') or contains(@placeholder, 'ID')]"),
                ]
            )
            password_input = self._find_first(
                [
                    (By.ID, "password"),
                    (By.NAME, "password"),
                    (By.CSS_SELECTOR, "input[type='password']"),
                ]
            )
            email_input.clear()
            email_input.send_keys(account.email or "")
            password_input.clear()
            password_input.send_keys(account.password or "")

            clicked = self._click_first(
                [
                    (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'log in')]"),
                    (By.XPATH, "//input[contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'log in')]"),
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.CSS_SELECTOR, "input[type='submit']"),
                ]
            )
            if not clicked:
                password_input.send_keys("\n")

            time.sleep(6)
            self._click_first(
                [
                    (By.LINK_TEXT, "Author"),
                    (By.PARTIAL_LINK_TEXT, "Author"),
                    (By.XPATH, "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'author')]"),
                ],
                timeout=8,
            )
            time.sleep(4)
        except Exception as exc:
            self._save_debug_artifacts("ieee_login_failed")
            raise RuntimeError(f"IEEE login failed: {exc}") from exc

        manuscripts = self._parse_table_rows("IEEE", self.driver.current_url)
        if not manuscripts:
            self._save_debug_artifacts("ieee_no_manuscripts")
        return manuscripts

    def fetch_elsevier_manuscripts(self, account: PlatformAccount) -> List[Dict]:
        if not self.driver:
            raise RuntimeError("Browser driver is not initialized.")
        print(f"Opening Elsevier Editorial Manager: {account.url}")
        self.driver.get(account.url)
        time.sleep(3)

        try:
            email_input = self._find_first(
                [
                    (By.CSS_SELECTOR, "input[type='email']"),
                    (By.NAME, "username"),
                    (By.NAME, "login"),
                    (By.ID, "username"),
                    (By.ID, "login"),
                    (By.CSS_SELECTOR, "input[type='text']"),
                ],
                timeout=8,
            )
            email_input.clear()
            email_input.send_keys(account.email or "")
            self._click_first(
                [
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]"),
                    (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'next')]"),
                ],
                timeout=4,
            )
            time.sleep(2)

            password_input = self._find_first([(By.CSS_SELECTOR, "input[type='password']")], timeout=10)
            password_input.clear()
            password_input.send_keys(account.password or "")
            clicked = self._click_first(
                [
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'sign in')]"),
                    (By.XPATH, "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'login')]"),
                ],
                timeout=5,
            )
            if not clicked:
                password_input.send_keys("\n")
            time.sleep(8)
        except Exception as exc:
            self._save_debug_artifacts("elsevier_login_failed")
            raise RuntimeError(f"Elsevier login failed: {exc}") from exc

        manuscripts = self._parse_table_rows("Elsevier", self.driver.current_url)
        if not manuscripts:
            self._save_debug_artifacts("elsevier_no_manuscripts")
        return manuscripts

    def _parse_table_rows(self, source: str, url: str) -> List[Dict]:
        if not self.driver:
            return []

        rows = self.driver.find_elements(By.XPATH, "//table//tr[td]")
        manuscripts_by_title: dict[str, dict] = {}
        seen: set[str] = set()

        for row in rows:
            raw_cells = [cell.text or "" for cell in row.find_elements(By.TAG_NAME, "td")]
            cells = [self._clean_cell(cell) for cell in raw_cells]
            cells = [cell for cell in cells if cell]
            if len(cells) < 3:
                continue

            row_text = " | ".join(cells)
            lowered = row_text.lower()
            if self._looks_like_navigation_row(lowered):
                continue

            status_index = self._find_status_cell_index(row, len(raw_cells))
            status = self._pick_status_from_raw_cells(raw_cells, status_index=status_index) or self._pick_status(cells)
            title = self._pick_title(cells, status=status)
            manuscript_id = self._pick_manuscript_id(cells)
            if not self._looks_like_manuscript_row(cells, manuscript_id, title, status):
                continue

            identity_title = self._manuscript_identity_title(title)
            unique_key = f"{source}:{identity_title or manuscript_id}".lower()
            if unique_key in seen:
                current = {
                    "id": manuscript_id or title[:80],
                    "title": self._display_title(title),
                    "status": status or "Unknown",
                    "source": source,
                    "url": url,
                }
                manuscripts_by_title[unique_key] = self._prefer_current_record(manuscripts_by_title[unique_key], current)
                continue
            seen.add(unique_key)

            manuscripts_by_title[unique_key] = {
                "id": manuscript_id or title[:80],
                "title": self._display_title(title),
                "status": status or "Unknown",
                "source": source,
                "url": url,
            }

        manuscripts = list(manuscripts_by_title.values())
        print(f"Parsed {len(manuscripts)} {source} manuscript(s).")
        return manuscripts

    @staticmethod
    def _clean_cell(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    @staticmethod
    def _cell_lines(value: str) -> list[str]:
        return [JournalMonitor._clean_cell(line) for line in (value or "").splitlines() if JournalMonitor._clean_cell(line)]

    @staticmethod
    def _looks_like_navigation_row(text: str) -> bool:
        blocked = [
            "logout",
            "log out",
            "help",
            "instructions",
            "privacy",
            "terms",
            "search",
            "create new submission",
        ]
        return any(token in text for token in blocked)

    @staticmethod
    def _looks_like_manuscript_row(cells: list[str], manuscript_id: str, title: str, status: str) -> bool:
        joined = " ".join(cells).lower()
        signals = [
            "submitted",
            "review",
            "decision",
            "revision",
            "editor",
            "manuscript",
            "accept",
            "reject",
            "awaiting",
            "processing",
        ]
        return bool((manuscript_id or len(title) > 20) and (status or any(signal in joined for signal in signals)))

    @staticmethod
    def _pick_manuscript_id(cells: list[str]) -> str:
        strong_id_patterns = [
            r"\b\d{2}-[A-Z]{1,8}-\d{2,}[-_A-Z0-9]*\b",
        ]
        id_patterns = [
            r"\b[A-Z]{1,8}[-_ ]?\d{2,}[-_A-Z0-9]*\b",
            r"\b\d{4,}[-_A-Z0-9]*\b",
        ]
        for cell in cells:
            compact = cell.strip()
            for pattern in strong_id_patterns:
                match = re.search(pattern, compact, flags=re.IGNORECASE)
                if match and not JournalMonitor._looks_like_date_token(match.group(0)):
                    return match.group(0)
            if len(compact) > 60:
                continue
            for pattern in id_patterns:
                match = re.search(pattern, compact, flags=re.IGNORECASE)
                if match and not JournalMonitor._looks_like_date_token(match.group(0)):
                    return match.group(0)
        return cells[0] if cells and len(cells[0]) <= 60 else ""

    @staticmethod
    def _looks_like_date_token(value: str) -> bool:
        text = str(value or "").strip().lower()
        months = r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec"
        patterns = [
            rf"(?:{months})[-_ ]?\d{{2,4}}",
            rf"\d{{1,2}}[-_ ](?:{months})[-_ ]\d{{2,4}}",
            r"\d{4}[-_/]\d{1,2}[-_/]\d{1,2}",
        ]
        return any(re.fullmatch(pattern, text) for pattern in patterns)

    @staticmethod
    def _normalize_title(value: str) -> str:
        text = JournalMonitor._clean_cell(value)
        action_markers = [
            r"\bView Submission\b.*$",
            r"\bSubmitting Author\b.*$",
            r"\bSubmitted Manuscripts?\b.*$",
            r"\bManuscript Files\b.*$",
        ]
        for pattern in action_markers:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
        return text.strip(" -|")

    @staticmethod
    def _strip_trailing_status_from_title(value: str) -> str:
        text = JournalMonitor._normalize_title(value)
        while True:
            match = re.search(r"\s+(\((?:[^()]|\([^()]*\))*\))\s*$", text)
            if not match:
                break
            suffix = match.group(1)
            if not JournalMonitor._status_score(suffix):
                break
            text = text[: match.start()].strip()
        return text

    @staticmethod
    def _display_title(value: str) -> str:
        return JournalMonitor._strip_trailing_status_from_title(value) or JournalMonitor._normalize_title(value) or "Untitled manuscript"

    @staticmethod
    def _manuscript_identity_title(value: str) -> str:
        title = JournalMonitor._strip_trailing_status_from_title(value)
        title = re.sub(r"\s+", " ", title).strip().lower()
        title = re.sub(r"[^\w\s:;-]", "", title)
        return re.sub(r"\s+", " ", title).strip()

    @staticmethod
    def _status_priority(status: object) -> int:
        text = str(status or "").lower()
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
        return JournalMonitor._status_score(text)

    @staticmethod
    def _id_quality(manuscript_id: object) -> int:
        text = str(manuscript_id or "").strip()
        if not text:
            return 0
        if JournalMonitor._looks_like_date_token(text):
            return -10
        if re.search(r"[A-Za-z]", text) and re.search(r"\d", text):
            return 10
        if re.search(r"\d", text):
            return 5
        return 1

    @staticmethod
    def _prefer_current_record(existing: dict, candidate: dict) -> dict:
        existing_score = JournalMonitor._status_priority(existing.get("status"))
        candidate_score = JournalMonitor._status_priority(candidate.get("status"))
        if candidate_score > existing_score:
            chosen = {**candidate}
            if JournalMonitor._id_quality(existing.get("id")) > JournalMonitor._id_quality(candidate.get("id")):
                chosen["id"] = existing.get("id", "")
            return chosen
        if candidate_score == existing_score and JournalMonitor._id_quality(candidate.get("id")) > JournalMonitor._id_quality(existing.get("id")):
            chosen = {**existing}
            chosen["id"] = candidate.get("id", "")
            return chosen
        return existing

    @staticmethod
    def _pick_title(cells: list[str], status: str = "") -> str:
        normalized = [JournalMonitor._normalize_title(cell) for cell in cells]
        blocked = {"contact journal", status.lower().strip()}
        candidates = []
        for cell in normalized:
            lower = cell.lower()
            if not cell or lower in blocked:
                continue
            if lower.startswith(("eic:", "adm:")):
                continue
            if JournalMonitor._looks_like_identifier_cell(cell):
                continue
            if JournalMonitor._status_score(cell):
                continue
            if len(cell) > 20:
                candidates.append(cell)
        if candidates:
            return max(candidates, key=len)
        long_cells = [cell for cell in normalized if len(cell) > 20]
        return max(long_cells, key=len) if long_cells else (normalized[-1] if normalized else "")

    @staticmethod
    def _looks_like_identifier_cell(value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        if re.search(r"\bREX-PROD\b", text, flags=re.IGNORECASE):
            return True
        if re.search(r"\b[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\b", text, flags=re.IGNORECASE):
            return True
        if re.fullmatch(r"\d{2}-[A-Z]{1,8}-\d{2,}.*", text, flags=re.IGNORECASE):
            return True
        return False

    @staticmethod
    def _status_score(value: str) -> int:
        text = value.lower()
        keywords = [
            "submitted",
            "review",
            "decision",
            "revision",
            "editor",
            "awaiting",
            "processing",
            "accept",
            "reject",
            "incomplete",
            "withdrawn",
            "published",
            "with editor",
            "with reviewer",
            "with associate editor",
            "with editor-in-chief",
        ]
        return sum(1 for keyword in keywords if keyword in text)

    @staticmethod
    def _line_is_status_candidate(line: str) -> bool:
        lower = line.lower().strip()
        if not lower:
            return False
        ignored_prefixes = (
            "contact journal",
            "eic:",
            "adm:",
            "view submission",
            "submitting author",
            "manuscript files",
            "action",
        )
        if lower.startswith(ignored_prefixes):
            return False
        return bool(JournalMonitor._status_score(line))

    @staticmethod
    def _status_date_key(line: str) -> tuple[int, int, int] | None:
        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "sept": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        match = re.search(r"\b(\d{1,2})[-/\s]([A-Za-z]{3,9})[-/\s](\d{2,4})\b", line)
        if match:
            day = int(match.group(1))
            month = month_map.get(match.group(2).lower()[:3])
            year = int(match.group(3))
            if year < 100:
                year += 2000
            if month:
                return (year, month, day)
        match = re.search(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", line)
        if match:
            return (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        return None

    @staticmethod
    def _status_lines_from_cell(raw_cell: str) -> list[str]:
        status_lines: list[str] = []
        lines = JournalMonitor._cell_lines(raw_cell)
        index = 0
        while index < len(lines):
            line = lines[index]
            cleaned = re.sub(r"^(current\s+)?status\s*:?\s*", "", line, flags=re.IGNORECASE).strip()
            if index + 1 < len(lines) and JournalMonitor._should_join_status_lines(cleaned, lines[index + 1]):
                cleaned = f"{cleaned} {lines[index + 1]}".strip()
                index += 1
            if JournalMonitor._line_is_status_candidate(cleaned):
                status_lines.append(cleaned)
            index += 1
        return status_lines

    @staticmethod
    def _should_join_status_lines(current: str, next_line: str) -> bool:
        current_text = str(current or "").strip()
        next_text = str(next_line or "").strip()
        if not current_text or not next_text:
            return False
        lower_next = next_text.lower()
        if current_text.count("(") > current_text.count(")"):
            return True
        if lower_next in {"processing"}:
            return True
        if re.fullmatch(r"\(?\d{1,2}[-/\s][A-Za-z]{3,9}[-/\s]?\d{2,4}\)?", next_text):
            return True
        if re.fullmatch(r"\d{2,4}\)?", next_text) and re.search(r"\([A-Za-z]{3,9}[-/\s]*$", current_text):
            return True
        return False

    @staticmethod
    def _choose_current_status(status_lines: list[str]) -> str:
        if not status_lines:
            return ""
        # ScholarOne renders the STATUS history newest -> oldest.
        # The visual top line is therefore the current status even if older
        # lines contain later-looking dates from revision activity.
        return status_lines[0]

    @staticmethod
    def _status_cell_score(raw_cell: str) -> int:
        lines = JournalMonitor._status_lines_from_cell(raw_cell)
        if not lines:
            return 0
        joined = " ".join(JournalMonitor._cell_lines(raw_cell)).lower()
        score = 10 + len(lines) * 5
        if re.search(r"\b(current\s+)?status\b", joined):
            score += 25
        if len(lines) > 1:
            score += 15
        if JournalMonitor._status_date_key(lines[0]) is not None:
            score += 10
        if any(JournalMonitor._status_date_key(line) is not None for line in lines):
            score += 5
        if re.search(r"\b(view submission|contact journal|manuscript files|submitting author)\b", joined):
            score -= 25
        if len(JournalMonitor._clean_cell(raw_cell)) > 500:
            score -= 10
        return score

    @staticmethod
    def _pick_status_from_raw_cells(raw_cells: list[str], status_index: int | None = None) -> str:
        if status_index is not None and 0 <= status_index < len(raw_cells):
            status = JournalMonitor._choose_current_status(JournalMonitor._status_lines_from_cell(raw_cells[status_index]))
            if status:
                return status

        scored_cells = [
            (JournalMonitor._status_cell_score(raw_cell), index, raw_cell)
            for index, raw_cell in enumerate(raw_cells)
        ]
        scored_cells = [item for item in scored_cells if item[0] > 0]
        if scored_cells:
            scored_cells.sort(key=lambda item: (-item[0], item[1]))
            return JournalMonitor._choose_current_status(JournalMonitor._status_lines_from_cell(scored_cells[0][2]))

        candidates: list[str] = []
        for raw_cell in raw_cells:
            candidates.extend(JournalMonitor._status_lines_from_cell(raw_cell))
        if not candidates:
            return ""
        return JournalMonitor._choose_current_status(candidates)

    @staticmethod
    def _find_status_cell_index(row: object, cell_count: int) -> int | None:
        try:
            cells = row.find_elements(By.TAG_NAME, "td")
            for index, cell in enumerate(cells):
                labels = [
                    cell.get_attribute("data-label") or "",
                    cell.get_attribute("aria-label") or "",
                    cell.get_attribute("headers") or "",
                ]
                if any(re.search(r"\bstatus\b", label, flags=re.IGNORECASE) for label in labels):
                    return index

            table = row.find_element(By.XPATH, "./ancestor::table[1]")
            header_rows = table.find_elements(By.XPATH, ".//tr[th]")
            for header_row in reversed(header_rows):
                headers = [JournalMonitor._clean_cell(th.text) for th in header_row.find_elements(By.TAG_NAME, "th")]
                if len(headers) != cell_count:
                    continue
                for index, header in enumerate(headers):
                    if re.search(r"\bstatus\b", header, flags=re.IGNORECASE):
                        return index
        except Exception:
            return None
        return None

    @staticmethod
    def _pick_status(cells: list[str]) -> str:
        scored = [(JournalMonitor._status_score(cell), len(cell), cell) for cell in cells if len(cell) <= 120]
        scored = [item for item in scored if item[0] > 0]
        if scored:
            scored.sort(key=lambda item: (-item[0], item[1]))
            return scored[0][2]
        return cells[1] if len(cells) > 1 and len(cells[1]) <= 120 else "Unknown"

    def collect_manuscripts(self) -> List[Dict]:
        manuscripts: list[dict] = []
        accounts = Config.configured_platforms()
        print("Configuration:", Config.summary(accounts))

        self._init_driver()
        try:
            for account in accounts:
                try:
                    if account.name == "IEEE":
                        manuscripts.extend(self.fetch_ieee_manuscripts(account))
                    elif account.name == "Elsevier":
                        manuscripts.extend(self.fetch_elsevier_manuscripts(account))
                except Exception as exc:
                    print(f"{account.name} fetch failed: {exc}")
        finally:
            self._close_driver()
        return manuscripts

    def run(self, mode: str) -> int:
        Config.validate(mode)
        if mode == "test":
            return 0 if self.notifier.send_test_email() else 1

        manuscripts = self.collect_manuscripts()
        print(f"Fetched {len(manuscripts)} manuscript(s).")

        if not manuscripts:
            message = "No manuscripts were fetched. Check credentials, URLs, page structure, or debug artifacts."
            print(message)
            return 1 if Config.FAIL_ON_EMPTY else 0

        changed = self.storage.compare_and_update(manuscripts)
        current = self.storage.get_all_manuscripts(include_archived=Config.INCLUDE_ARCHIVED_IN_REPORT)

        if mode == "daily_report":
            if self.storage.daily_report_already_sent():
                print("Daily report already sent today; skipping duplicate fallback run.")
                return 0
            sent = self.notifier.send_daily_report(current)
            if sent:
                self.storage.mark_daily_report_sent()
            return 0 if sent else 1
        if changed:
            return 0 if self.notifier.send_change_notification(changed) else 1

        print("No status changes detected.")
        return 0


def resolve_mode(cli_mode: str | None) -> str:
    if cli_mode:
        return cli_mode
    if os.getenv("DAILY_REPORT", "").lower() == "true":
        return "daily_report"
    return os.getenv("RUN_MODE", "normal").strip().lower()


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor journal manuscript status.")
    parser.add_argument("--mode", choices=["normal", "test", "daily_report"], help="Run mode.")
    args = parser.parse_args()
    mode = resolve_mode(args.mode)
    print(f"Run mode: {mode}")
    return JournalMonitor().run(mode)


if __name__ == "__main__":
    sys.exit(main())
