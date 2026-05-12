"""
HuggingFace-backed global leaderboard for Spaceship Game.

Uses HuggingFace datasets to share leaderboard entries across players.
Each player can publish their local scores to their own dataset, and the
app aggregates all community datasets tagged with LEADERBOARD_TAG.
"""

import json
import logging
import tempfile
import threading
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("spaceship_game.hf_leaderboard")

LEADERBOARD_TAG = "reachy_mini_spaceship_game_leaderboard"
HF_DATASETS_API_URL = "https://huggingface.co/api/datasets"
MAX_COMMUNITY_DATASETS = 100
LEADERBOARD_FILENAME = "leaderboard.json"


@dataclass
class LeaderboardEntry:
    score: int
    name: str
    date: str  # ISO 8601 format
    waves_completed: Optional[int] = None
    source_repo: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "LeaderboardEntry":
        known_fields = {"score", "name", "date", "waves_completed", "source_repo"}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        filtered.setdefault("score", 0)
        filtered.setdefault("name", "Anonymous")
        filtered.setdefault("date", datetime.now(timezone.utc).isoformat())
        return cls(**filtered)


@dataclass
class HFLeaderboardState:
    global_entries: list[LeaderboardEntry] = field(default_factory=list)
    last_sync: Optional[float] = None
    sync_error: Optional[str] = None
    is_syncing: bool = False
    hf_available: bool = False
    hf_logged_in: bool = False
    hf_username: Optional[str] = None


def _check_hf_availability() -> tuple[bool, bool, Optional[str]]:
    try:
        from huggingface_hub import HfApi
        try:
            from huggingface_hub import get_token
            token = get_token()
        except ImportError:
            from huggingface_hub import HfFolder
            token = HfFolder.get_token()

        if not token:
            return True, False, None

        api = HfApi()
        try:
            user_info = api.whoami()
            username = user_info.get("name") or user_info.get("username")
            return True, True, username
        except Exception:
            return True, False, None
    except ImportError:
        return False, False, None
    except Exception as e:
        logger.warning("Error checking HF availability: %s", e)
        return False, False, None


def _fetch_community_datasets() -> list[str]:
    import urllib.request

    candidates = []

    search_urls = [
        f"{HF_DATASETS_API_URL}?search=tag:{LEADERBOARD_TAG}&limit={MAX_COMMUNITY_DATASETS}",
        f"{HF_DATASETS_API_URL}?search={LEADERBOARD_TAG}&limit={MAX_COMMUNITY_DATASETS}",
        f"{HF_DATASETS_API_URL}?filter={LEADERBOARD_TAG}&limit={MAX_COMMUNITY_DATASETS}",
    ]

    for url in search_urls:
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
                if isinstance(data, list):
                    for item in data:
                        repo_id = item.get("id") or item.get("_id")
                        tags = item.get("tags", [])
                        if repo_id:
                            candidates.append((repo_id, tags or []))
                    if candidates:
                        break
        except Exception as e:
            logger.debug("Search strategy failed for %s: %s", url, e)
            continue

    if not candidates:
        try:
            from huggingface_hub import HfApi
            api = HfApi()
            datasets = api.list_datasets(tags=[LEADERBOARD_TAG], limit=MAX_COMMUNITY_DATASETS)
            for ds in datasets:
                if ds.id:
                    tags = getattr(ds, "tags", []) or []
                    candidates.append((ds.id, tags))
        except Exception as e:
            logger.debug("HfApi fallback failed: %s", e)

    repo_ids = []
    seen = set()
    for repo_id, tags in candidates:
        if LEADERBOARD_TAG in tags and repo_id not in seen:
            repo_ids.append(repo_id)
            seen.add(repo_id)

    if not repo_ids:
        for repo_id, _ in candidates:
            if repo_id not in seen:
                repo_ids.append(repo_id)
                seen.add(repo_id)

    return repo_ids


def _download_leaderboard_from_repo(repo_id: str) -> list[LeaderboardEntry]:
    entries = []
    try:
        from huggingface_hub import hf_hub_download

        local_path = hf_hub_download(
            repo_id=repo_id,
            filename=LEADERBOARD_FILENAME,
            repo_type="dataset",
        )

        with open(local_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    entry = LeaderboardEntry.from_dict(item)
                    entry.source_repo = repo_id
                    entries.append(entry)

    except Exception as e:
        logger.debug("Failed to download leaderboard from %s: %s", repo_id, e)

    return entries


def fetch_global_leaderboard() -> tuple[list[LeaderboardEntry], Optional[str]]:
    try:
        repo_ids = _fetch_community_datasets()
        if not repo_ids:
            return [], None

        all_entries = []
        for repo_id in repo_ids:
            entries = _download_leaderboard_from_repo(repo_id)
            all_entries.extend(entries)

        all_entries.sort(key=lambda e: e.score, reverse=True)
        return all_entries, None

    except Exception as e:
        logger.warning("Failed to fetch global leaderboard: %s", e)
        return [], str(e)


def publish_leaderboard(
    entries: list[dict],
    hf_username: str,
    dataset_slug: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[str]]:
    try:
        from huggingface_hub import HfApi

        api = HfApi()
        repo_name = dataset_slug or "spaceship-game-leaderboard"
        repo_id = f"{hf_username}/{repo_name}"

        formatted_entries = []
        for entry in entries:
            formatted = {
                "score": int(entry.get("score", 0)),
                "name": entry.get("name", "Anonymous"),
                "date": entry.get("date") or datetime.fromtimestamp(
                    entry.get("timestamp", time.time()), tz=timezone.utc
                ).isoformat(),
            }
            if "waves_completed" in entry and entry["waves_completed"] is not None:
                formatted["waves_completed"] = entry["waves_completed"]
            formatted_entries.append(formatted)

        with tempfile.TemporaryDirectory(prefix="spaceship-game-leaderboard-") as tmpdir:
            tmppath = Path(tmpdir)

            leaderboard_path = tmppath / LEADERBOARD_FILENAME
            with open(leaderboard_path, "w", encoding="utf-8") as f:
                json.dump(formatted_entries, f, indent=2)

            readme_content = _build_readme(formatted_entries, hf_username)
            readme_path = tmppath / "README.md"
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(readme_content)

            api.create_repo(
                repo_id=repo_id,
                repo_type="dataset",
                exist_ok=True,
                private=False,
            )

            api.upload_folder(
                folder_path=str(tmppath),
                repo_id=repo_id,
                repo_type="dataset",
            )

        repo_url = f"https://huggingface.co/datasets/{repo_id}"
        return True, None, repo_url

    except Exception as e:
        logger.warning("Failed to publish leaderboard: %s", e)
        return False, str(e), None


def _build_readme(entries: list[dict], username: str) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    top_score = entries[0]["score"] if entries else 0
    top_player = entries[0]["name"] if entries else "N/A"

    yaml_header = f"""---
tags:
  - {LEADERBOARD_TAG}
  - reachy-mini
  - game
  - leaderboard
license: apache-2.0
task_categories:
  - other
pretty_name: Spaceship Game Leaderboard
---
"""

    body = f"""# Spaceship Game - Leaderboard

This dataset contains leaderboard entries for the **Spaceship Game** on Reachy Mini.

## Stats

- **Entries**: {len(entries)}
- **Top Score**: {top_score} by {top_player}
- **Last Updated**: {now}
- **Published by**: {username}

## Format

The `leaderboard.json` file contains an array of entries:

| Field | Type | Description |
|-------|------|-------------|
| score | int | Final game score |
| name | string | Player name |
| date | string | ISO 8601 timestamp |
| waves_completed | int? | Number of waves completed |

## Top 10

| Rank | Player | Score | Date |
|------|--------|-------|------|
"""

    for i, entry in enumerate(entries[:10], 1):
        date_short = entry.get("date", "")[:10]
        name_escaped = entry["name"].replace("|", "\\|")
        body += f"| {i} | {name_escaped} | {entry['score']} | {date_short} |\n"

    body += """
## About

This leaderboard is part of the [Reachy Mini](https://github.com/pollen-robotics/reachy_mini)
ecosystem. Control your spaceship with Reachy Mini's head movements and antennas!

---

*Generated by Spaceship Game app*
"""

    return yaml_header + body


class GlobalLeaderboardManager:
    def __init__(self):
        self.state = HFLeaderboardState()
        self._lock = threading.Lock()
        self._sync_thread: Optional[threading.Thread] = None

    def check_status(self) -> dict:
        available, logged_in, username = _check_hf_availability()
        with self._lock:
            self.state.hf_available = available
            self.state.hf_logged_in = logged_in
            self.state.hf_username = username

        return {
            "available": available,
            "logged_in": logged_in,
            "username": username,
            "message": self._get_status_message(available, logged_in),
        }

    def _get_status_message(self, available: bool, logged_in: bool) -> Optional[str]:
        if not available:
            return "Install huggingface-hub to sync with the global leaderboard: pip install --upgrade huggingface_hub"
        if not logged_in:
            return "Log in to HuggingFace to publish your scores: huggingface-cli login"
        return None

    def get_state(self) -> dict:
        with self._lock:
            needs_status_check = not self.state.hf_available and self.state.hf_username is None
        if needs_status_check:
            self.check_status()

        with self._lock:
            should_auto_sync = self.state.last_sync is None and not self.state.is_syncing
        if should_auto_sync:
            self.sync_async()

        with self._lock:
            return {
                "entries": [e.to_dict() for e in self.state.global_entries[:50]],
                "last_sync": self.state.last_sync,
                "sync_error": self.state.sync_error,
                "is_syncing": self.state.is_syncing,
                "hf_available": self.state.hf_available,
                "hf_logged_in": self.state.hf_logged_in,
                "hf_username": self.state.hf_username,
            }

    def sync_async(self) -> None:
        with self._lock:
            if self.state.is_syncing:
                return
            self.state.is_syncing = True

        def _sync():
            try:
                entries, error = fetch_global_leaderboard()
                with self._lock:
                    self.state.global_entries = entries
                    self.state.last_sync = time.time()
                    self.state.sync_error = error
                    self.state.is_syncing = False
                if error:
                    logger.warning("Global leaderboard sync error: %s", error)
                else:
                    logger.info("Synced %d global leaderboard entries", len(entries))
            except Exception as e:
                with self._lock:
                    self.state.sync_error = str(e)
                    self.state.is_syncing = False
                logger.warning("Global leaderboard sync failed: %s", e)

        self._sync_thread = threading.Thread(target=_sync, daemon=True)
        self._sync_thread.start()

    def publish(self, local_entries: list[dict]) -> dict:
        status = self.check_status()
        if not status["available"]:
            return {"success": False, "error": status["message"], "repo_url": None}
        if not status["logged_in"]:
            return {"success": False, "error": status["message"], "repo_url": None}

        username = status["username"]
        if not username:
            return {"success": False, "error": "Could not determine HuggingFace username", "repo_url": None}

        success, error, repo_url = publish_leaderboard(local_entries, username)
        if success:
            self.sync_async()

        return {"success": success, "error": error, "repo_url": repo_url}


_manager: Optional[GlobalLeaderboardManager] = None


def get_manager() -> GlobalLeaderboardManager:
    global _manager
    if _manager is None:
        _manager = GlobalLeaderboardManager()
    return _manager
