import json
import os
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import ValidationError
from .models import CharacterSheet, EventLogEntry, SceneState

# store.py -> state/ -> vtt/ -> src/ -> repo root.
_REPO_ROOT = Path(__file__).resolve().parents[3]

class StateStore:
    def __init__(self, storage_dir: str | None = None):
        # Default resolves to the repo root, not the process's cwd -- a
        # bare "data" here previously meant campaign state silently landed
        # in whatever directory the game happened to be launched from
        # (e.g. src/data/ instead of data/ if run from inside src/),
        # producing two divergent, un-erroring copies of the same
        # campaign. VTT_DATA_DIR overrides for a host (e.g. Everwood) that
        # wants state somewhere else entirely.
        self.storage_dir = storage_dir or os.environ.get("VTT_DATA_DIR") or str(_REPO_ROOT / "data")
        os.makedirs(self.storage_dir, exist_ok=True)
        self.characters_path = os.path.join(self.storage_dir, "characters.json")
        self.events_path = os.path.join(self.storage_dir, "events.jsonl")
        self.scene_path = os.path.join(self.storage_dir, "scene.json")

    # Character logic
    def _read_characters(self) -> Dict[str, dict]:
        if not os.path.exists(self.characters_path):
            return {}
        with open(self.characters_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_characters(self, chars: Dict[str, dict]):
        with open(self.characters_path, "w", encoding="utf-8") as f:
            json.dump(chars, f, indent=2)

    def get_character(self, character_id: str) -> Optional[CharacterSheet]:
        chars = self._read_characters()
        if character_id in chars:
            try:
                return CharacterSheet(**chars[character_id])
            except ValidationError as e:
                print(f"Validation error for character {character_id}: {e}")
        return None

    def save_character(self, character: CharacterSheet):
        chars = self._read_characters()
        chars[character.id] = character.model_dump(by_alias=True)
        self._write_characters(chars)

    def update_character(self, character_id: str, patch: dict) -> bool:
        """Applies a dictionary patch to a character and saves it."""
        char_data = self._read_characters().get(character_id)
        if not char_data:
            return False
            
        # Merge patch
        for k, v in patch.items():
            if isinstance(v, dict) and k in char_data and isinstance(char_data[k], dict):
                char_data[k].update(v)
            else:
                char_data[k] = v
                
        try:
            # Validate patched data
            updated_char = CharacterSheet(**char_data)
            self.save_character(updated_char)
            return True
        except ValidationError as e:
            print(f"Validation error updating character {character_id}: {e}")
            return False

    # Event logic
    def log_event(self, event: EventLogEntry):
        with open(self.events_path, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def get_events(self) -> List[EventLogEntry]:
        if not os.path.exists(self.events_path):
            return []
        events = []
        with open(self.events_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(EventLogEntry.model_validate_json(line))
        return events

    # Scene logic
    def get_scene(self) -> Optional[SceneState]:
        if not os.path.exists(self.scene_path):
            return None
        with open(self.scene_path, "r", encoding="utf-8") as f:
            return SceneState.model_validate_json(f.read())

    def save_scene(self, scene: SceneState):
        with open(self.scene_path, "w", encoding="utf-8") as f:
            f.write(scene.model_dump_json(indent=2))
