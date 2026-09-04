import json
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import ValidationError

from ..config import resolve_data_dir, validate_identifier
from .models import (
    CharacterSheet,
    EventLogEntry,
    PlayerAction,
    PlayerActionResult,
    SceneState,
)

class StateStore:
    def __init__(
        self,
        storage_dir: str | Path | None = None,
        campaign_id: str | None = None,
    ):
        base_dir = resolve_data_dir(storage_dir)
        self.campaign_id = (
            validate_identifier(campaign_id, "campaign_id") if campaign_id else None
        )
        self.storage_dir = (
            base_dir / "campaigns" / self.campaign_id
            if self.campaign_id
            else base_dir
        )
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.characters_path = self.storage_dir / "characters.json"
        self.events_path = self.storage_dir / "events.jsonl"
        self.scene_path = self.storage_dir / "scene.json"
        self.actions_path = self.storage_dir / "player_actions.jsonl"
        self.action_results_path = self.storage_dir / "player_action_results.jsonl"

    # Character logic
    def _read_characters(self) -> Dict[str, dict]:
        if not self.characters_path.exists():
            return {}
        with self.characters_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_characters(self, chars: Dict[str, dict]):
        with self.characters_path.open("w", encoding="utf-8") as f:
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
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def get_events(self) -> List[EventLogEntry]:
        if not self.events_path.exists():
            return []
        events = []
        with self.events_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(EventLogEntry.model_validate_json(line))
        return events

    # Scene logic
    def get_scene(self) -> Optional[SceneState]:
        if not self.scene_path.exists():
            return None
        with self.scene_path.open("r", encoding="utf-8") as f:
            return SceneState.model_validate_json(f.read())

    def save_scene(self, scene: SceneState):
        with self.scene_path.open("w", encoding="utf-8") as f:
            f.write(scene.model_dump_json(indent=2))

    def submit_player_action(self, action: PlayerAction) -> PlayerAction:
        validate_identifier(action.action_id, "action_id")
        validate_identifier(action.campaign_id, "campaign_id")
        validate_identifier(action.player_id, "player_id")
        validate_identifier(action.character_id, "character_id")
        if self.campaign_id and action.campaign_id != self.campaign_id:
            raise ValueError("Player action campaign does not match this store.")
        existing = self.get_player_action(action.action_id)
        if existing:
            if existing != action:
                raise ValueError(
                    f"Action ID '{action.action_id}' was already used for a different request."
                )
            return existing
        with self.actions_path.open("a", encoding="utf-8") as f:
            f.write(action.model_dump_json() + "\n")
        return action

    def get_player_action(self, action_id: str) -> Optional[PlayerAction]:
        if not self.actions_path.exists():
            return None
        with self.actions_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    action = PlayerAction.model_validate_json(line)
                    if action.action_id == action_id:
                        return action
        return None

    def log_player_action_result(self, result: PlayerActionResult) -> None:
        if result.status == "pending":
            raise ValueError("Only resolved or rejected action results may be logged.")
        if self.campaign_id and result.campaign_id != self.campaign_id:
            raise ValueError("Action result campaign does not match this store.")
        action = self.get_player_action(result.action_id)
        if action is None:
            raise ValueError(
                f"Cannot resolve unknown action '{result.action_id}'."
            )
        with self.action_results_path.open("a", encoding="utf-8") as f:
            f.write(result.model_dump_json() + "\n")

    def get_player_action_result(self, action_id: str) -> Optional[PlayerActionResult]:
        if not self.action_results_path.exists():
            return None
        latest = None
        with self.action_results_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    result = PlayerActionResult.model_validate_json(line)
                    if result.action_id == action_id:
                        latest = result
        return latest
