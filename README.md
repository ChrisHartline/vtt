# VTT

VTT is a local-first tabletop RPG authority. It owns campaign state, dice,
event history, and the boundary between DM-only knowledge and player-visible
actions. Everwood, Lyra, and other hosts should consume its public API rather
than copy its implementation.

## Install profiles

The base install contains lightweight models, dice, storage, and player
contracts:

```powershell
python -m pip install .
```

Select optional capabilities explicitly:

```powershell
python -m pip install ".[dm]"       # LangGraph + Anthropic prototype DM
python -m pip install ".[rag]"      # Query an existing Chroma module index
python -m pip install ".[ingest]"   # Docling PDF ingestion + RAG stack
python -m pip install ".[dev,dm,rag,ingest]"
```

Docling is intentionally an ingestion-only dependency. It is not imported by
the base package or normal state/player operations.

## Host-owned storage

Library consumers must pass `storage_dir` or set `VTT_DATA_DIR`. Campaign-aware
operations are stored below `campaigns/<campaign_id>/` so two campaigns cannot
silently share state.

```python
from vtt import PlayerContext, PlayerGateway

player = PlayerGateway(
    PlayerContext(
        campaign_id="everwood-friday-night",
        player_id="chris",
        character_id="rhea",
    ),
    storage_dir=r"V:\VTTData",
)

character = player.get_my_character()
action = player.submit_player_action(
    "Inspect the sealed door without touching it.",
    action_id="door-inspection-001",
)
result = player.get_action_result(action.action_id)
```

`PlayerGateway` deliberately provides no direct character, scene, event, or
module mutation methods. The DM authority resolves submitted actions and
records only a player-visible result.

## Local commands

The prototype DM CLI uses `VTT_DATA_DIR` when set and otherwise chooses
`./data` explicitly at the application boundary:

```powershell
$env:VTT_DATA_DIR = "V:\VTTData"
vtt
```

PDF ingestion remains an offline administration task:

```powershell
vtt-ingest
```

See [docs/integration-architecture.md](docs/integration-architecture.md) for
the Everwood/Lyra boundary and the path to local or Internet-hosted MCP.
