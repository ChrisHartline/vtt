from pathlib import Path
from uuid import uuid4

from .config import validate_identifier
from .state.models import (
    CharacterSheet,
    PlayerAction,
    PlayerActionResult,
    PlayerContext,
    PlayerScene,
)
from .state.store import StateStore


class PlayerGateway:
    """A context-bound API that cannot directly mutate authoritative mechanics.

    A host creates one gateway after deciding which campaign, player, and
    character the caller owns. The same methods can later be exposed through
    MCP without giving the player raw access to StateStore.
    """

    def __init__(
        self,
        context: PlayerContext,
        storage_dir: str | Path | None = None,
    ):
        self.context = PlayerContext(
            campaign_id=validate_identifier(context.campaign_id, "campaign_id"),
            player_id=validate_identifier(context.player_id, "player_id"),
            character_id=validate_identifier(context.character_id, "character_id"),
        )
        self._store = StateStore(storage_dir, campaign_id=self.context.campaign_id)

    def get_my_character(self) -> CharacterSheet | None:
        return self._store.get_character(self.context.character_id)

    def get_player_scene(self) -> PlayerScene | None:
        scene = self._store.get_scene()
        if scene is None:
            return None
        return PlayerScene(
            scene_id=scene.scene_id,
            description=scene.description,
            active_entities=scene.active_entities,
        )

    def submit_player_action(
        self,
        description: str,
        target: str | None = None,
        action_id: str | None = None,
        metadata: dict | None = None,
    ) -> PlayerAction:
        if action_id:
            validate_identifier(action_id, "action_id")
            existing = self._store.get_player_action(action_id)
            if existing:
                same_request = (
                    existing.campaign_id == self.context.campaign_id
                    and existing.player_id == self.context.player_id
                    and existing.character_id == self.context.character_id
                    and existing.description == description
                    and existing.target == target
                    and existing.metadata == (metadata or {})
                )
                if not same_request:
                    raise ValueError(
                        f"Action ID '{action_id}' was already used for a different request."
                    )
                return existing

        action = PlayerAction(
            action_id=validate_identifier(
                action_id or f"act_{uuid4().hex}", "action_id"
            ),
            campaign_id=self.context.campaign_id,
            player_id=self.context.player_id,
            character_id=self.context.character_id,
            description=description,
            target=target,
            metadata=metadata or {},
        )
        return self._store.submit_player_action(action)

    def get_action_result(self, action_id: str) -> PlayerActionResult:
        validate_identifier(action_id, "action_id")
        action = self._store.get_player_action(action_id)
        if not action or (
            action.campaign_id != self.context.campaign_id
            or action.player_id != self.context.player_id
            or action.character_id != self.context.character_id
        ):
            raise KeyError(f"Action '{action_id}' is not available to this player.")
        return self._store.get_player_action_result(action_id) or PlayerActionResult(
            action_id=action_id,
            campaign_id=self.context.campaign_id,
            status="pending",
        )
