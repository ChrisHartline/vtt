from datetime import datetime, timezone

import pytest

from vtt import (
    CharacterSheet,
    EventLogEntry,
    PlayerActionResult,
    PlayerContext,
    PlayerGateway,
    SceneState,
    StateStore,
    VTTConfigurationError,
)


def _character(character_id: str) -> CharacterSheet:
    return CharacterSheet.model_validate(
        {
            "id": character_id,
            "name": "Rhea",
            "class": "Wizard",
            "level": 3,
            "hp": {"current": 14, "max": 18},
            "armor_class": 12,
            "abilities": {
                "str": 8,
                "dex": 14,
                "con": 12,
                "int": 17,
                "wis": 13,
                "cha": 10,
            },
            "personality": {"traits": ["analytical"], "goals": ["learn"]},
        }
    )


def test_library_store_requires_explicit_configuration(monkeypatch):
    monkeypatch.delenv("VTT_DATA_DIR", raising=False)
    with pytest.raises(VTTConfigurationError):
        StateStore()


def test_campaign_storage_is_namespaced(tmp_path):
    first = StateStore(tmp_path, campaign_id="campaign-one")
    second = StateStore(tmp_path, campaign_id="campaign-two")
    first.save_character(_character("rhea"))

    assert first.get_character("rhea") is not None
    assert second.get_character("rhea") is None
    assert first.storage_dir == tmp_path.resolve() / "campaigns" / "campaign-one"


def test_player_gateway_binds_identity_and_submits_idempotently(tmp_path):
    context = PlayerContext(
        campaign_id="friday-night",
        player_id="chris",
        character_id="rhea",
    )
    store = StateStore(tmp_path, campaign_id=context.campaign_id)
    store.save_character(_character("rhea"))
    store.save_character(_character("secret-npc"))
    store.save_scene(
        SceneState(
            scene_id="threshold",
            description="A sealed door stands to the north.",
            active_entities=["rhea"],
            events=[
                EventLogEntry(
                    event_id="dm-secret",
                    session=1,
                    actor="dm",
                    type="hidden",
                    description="The door is a mimic.",
                    outcome="Not yet revealed.",
                )
            ],
        )
    )
    gateway = PlayerGateway(context, tmp_path)

    assert gateway.get_my_character().id == "rhea"
    player_scene = gateway.get_player_scene()
    assert player_scene.description == "A sealed door stands to the north."
    assert not hasattr(player_scene, "events")
    assert not hasattr(gateway, "update_character")

    first = gateway.submit_player_action(
        "Inspect the sealed door.", action_id="act-door-1"
    )
    repeated = gateway.submit_player_action(
        "Inspect the sealed door.", action_id="act-door-1"
    )
    assert repeated == first
    assert gateway.get_action_result(first.action_id).status == "pending"

    with pytest.raises(ValueError):
        gateway.submit_player_action(
            "Kick down the sealed door.", action_id="act-door-1"
        )


def test_player_gateway_returns_only_owned_action_results(tmp_path):
    context = PlayerContext(
        campaign_id="friday-night",
        player_id="chris",
        character_id="rhea",
    )
    gateway = PlayerGateway(context, tmp_path)
    action = gateway.submit_player_action("Cast light.", action_id="act-light-1")
    dm_store = StateStore(tmp_path, campaign_id=context.campaign_id)
    dm_store.log_player_action_result(
        PlayerActionResult(
            action_id=action.action_id,
            campaign_id=context.campaign_id,
            status="resolved",
            public_outcome="The wand begins to glow.",
            resolved_at=datetime.now(timezone.utc),
        )
    )

    result = gateway.get_action_result(action.action_id)
    assert result.status == "resolved"
    assert result.public_outcome == "The wand begins to glow."

    other = PlayerGateway(
        PlayerContext(
            campaign_id="friday-night",
            player_id="other-player",
            character_id="other-character",
        ),
        tmp_path,
    )
    with pytest.raises(KeyError):
        other.get_action_result(action.action_id)


def test_importing_public_api_does_not_load_docling():
    import sys
    import vtt  # noqa: F401

    assert "docling" not in sys.modules
