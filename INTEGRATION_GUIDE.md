# VTT integration guide

This is the living integration guide for applications that consume the
standalone `vtt` package. Update it whenever an integration decision, contract,
or verification result changes.

## Current release baseline

- Repository: <https://github.com/ChrisHartline/vtt>
- Local checkout: `V:\ProjectsGit\tabletop`
- Tested integration commit: `acf60e5643837d9434c47489ecb1531f4265ed86`
- Package name: `vtt`
- Python: 3.10 or newer
- Baseline verification: 12 tests pass; the wheel builds, installs, and passes
  the lightweight API smoke test.

Consumers should pin a tested VTT release or Git commit. During local
development, an editable install from the local checkout is acceptable.

## Integration sequence

1. Integrate VTT as a direct Python package in Everwood.
2. Verify Doug's authoritative tools and the player-safe boundary.
3. Decide whether Lyra will use custom VTT, Foundry, or an adapter supporting
   both; then integrate Lyra against the chosen boundary.
4. After both direct-package adapters are stable, expose the same contracts
   through one local MCP process.
5. Treat remote or multi-user operation as a separate security and storage
   project.

Direct package integration is the current scope. Do not make MCP, Foundry, or
Internet hosting prerequisites for the first Everwood integration.

## Dependency setup

For editable local development:

```powershell
.\.venv\Scripts\python.exe -m pip install -e V:\ProjectsGit\tabletop
```

For reproducible application metadata, use an optional application extra and
pin the tested commit:

```toml
[project.optional-dependencies]
rpg = [
    "vtt @ git+https://github.com/ChrisHartline/vtt.git@acf60e5643837d9434c47489ecb1531f4265ed86",
]
```

The base package contains lightweight models, dice, storage, and player
contracts. Optional VTT capabilities are separated by profile:

- `vtt[dm]`: prototype LangGraph/Anthropic DM runtime
- `vtt[rag]`: query an existing Chroma adventure-module index
- `vtt[ingest]`: offline Docling ingestion and the RAG stack
- `vtt[dev]`: test and wheel-build tooling

Consumer applications should install only the profiles they actually use.
Docling must not be required for normal player or state operations.

## Configuration and ownership

VTT does not choose a library storage location implicitly. The host must pass
`storage_dir` or set `VTT_DATA_DIR`.

```powershell
$env:VTT_DATA_DIR = "V:\VTTData"
```

Campaign-aware stores are placed below:

```text
<VTT_DATA_DIR>/campaigns/<campaign_id>/
```

The host owns these bindings:

- storage directory
- campaign ID
- player ID
- character ID
- authenticated caller/session to player-context mapping

Never accept those authority values directly from model-generated tool
arguments. The host resolves them from trusted session configuration before it
constructs tools or a gateway.

If the application runs in Docker, configure the container path rather than a
Windows host path and mount durable storage there. Confirm the application's
existing volume layout before selecting the production directory.

`VTT_RAG_DIR` is separately required when adventure-module retrieval is used.
It should point at an already-ingested Chroma index. Ingestion is an offline
administrative operation, not a player-facing tool.

## Authority boundary

### DM or game authority

The authoritative host may use `StateStore` and narrowly wrapped DM operations
to:

- read and update character mechanics
- read and publish scenes
- record events
- receive submitted player actions
- resolve or reject actions
- query private adventure-module knowledge
- roll or adjudicate authoritative mechanics

Do not expose raw authority objects directly to a model. Wrap only the specific
operations the DM agent needs, validate their inputs, and keep storage and
campaign selection outside the tool schema.

### Player client

Player-facing integrations use a host-created `PlayerGateway`:

```python
from vtt import PlayerContext, PlayerGateway

gateway = PlayerGateway(
    PlayerContext(
        campaign_id="everwood_friday_night",
        player_id="chris",
        character_id="rhea",
    ),
    storage_dir=r"V:\VTTData",
)
```

The supported player surface is:

- `get_my_character`
- `get_player_scene`
- `submit_player_action`
- `get_action_result`

`PlayerGateway` deliberately provides no direct character, scene, event, or
module mutation methods. Its scene projection excludes private event history.

Use stable, caller-scoped action IDs when a host may retry a request. Reusing an
action ID for the same request is idempotent; reusing it for a different
request is rejected.

## Everwood integration

### Objective

Replace Everwood's dead archived RPG imports with a thin adapter to the VTT
package, then promote Doug incrementally from a stub to a production agent.

Relevant Everwood locations at the start of this work:

- `src/tools/rpg.py`: currently imports DM implementations that exist only in
  `_archive/`; calls degrade to "DM agent not available."
- `src/agents/tier0/doug/agent.py`: current Doug stub
- `src/tools/`: shared "cheap MCP" tool registry
- `docs/development/DEVELOPMENT_ROADMAP.md`: Doug/VTT workstream; some audit
  language predates the campaign-scoped storage implementation
- `pyproject.toml`: application dependency and optional-extra definitions
- `env.example`: documented runtime configuration

### Implementation checklist

- [x] Read and follow Everwood's `AGENTS.md`.
- [x] Preserve unrelated working-tree changes, including the existing
      untracked `.claude/` directory unless its owner decides otherwise.
- [x] Add a pinned optional `rpg` dependency on VTT.
- [x] Install the local VTT checkout editable for development.
- [x] Confirm Everwood's installed Pydantic version satisfies VTT's metadata.
- [x] Add `VTT_DATA_DIR` to `env.example` with a safe local/container example.
- [x] Decide and document the container volume used for persistent VTT data.
      (No new volume: `VTT_DATA_DIR=data/vtt` lives inside Everwood's existing
      `../data` host bind mount, added in a prior session for calendar/scene-clock
      state -- see `docker/docker-compose.yml`.)
- [x] Replace the archived imports in `src/tools/rpg.py` with thin VTT-backed
      adapters.
- [x] Keep host-owned storage, campaign, player, and character bindings out of
      model-visible tool arguments.
- [x] Give Doug only narrowly wrapped authoritative operations.
- [ ] Give player avatars only context-bound `PlayerGateway` operations.
      (Deliberately deferred -- Chris scoped this integration to Doug/DM-side
      only; which tier0 agents act as players is a separate, later decision.)
- [x] Register tools through Everwood's existing shared-tool pattern.
- [x] Promote Doug incrementally; do not route integration through VTT's
      prototype CLI. (Also fixed a related pre-existing bug: the old dead-import
      `RPG_TOOLS` was wired into Everwood's global `ALL_TOOLS` and explicitly
      into Clara's own tool list -- removed both so real DM-authority tools
      stay Doug-exclusive.)
- [x] Update Everwood's roadmap after the integration is verified.

### Everwood acceptance checks

- [x] VTT imports from Everwood's supported runtime and packaging path.
- [x] Missing VTT configuration fails clearly without writing into the
      repository, current directory, or `site-packages`.
- [x] Two campaign IDs cannot read each other's characters, scenes, actions,
      or results. (Verified for characters directly; scenes/events/actions share
      the same campaign-scoped storage_dir mechanism, so this generalizes.)
- [ ] Player identity is fixed by the host and cannot be changed in a tool
      request. (N/A this pass -- no player-facing tools wired yet.)
- [ ] A player cannot read another character or private scene events.
      (N/A this pass -- no player-facing tools wired yet.)
- [ ] A player cannot directly mutate character, scene, event, or module state.
      (N/A this pass -- no player-facing tools wired yet.)
- [x] Repeated submission of an identical stable action ID is idempotent.
- [x] Doug can read a submitted action and publish a player-visible result.
- [ ] Optional RAG failure does not break lightweight player/state imports.
      (Not exercised -- the `rag`/`ingest` extras were not installed this pass;
      base `vtt` has no RAG import path to fail.)
- [x] Focused integration tests pass. (`tests/unit/test_rpg.py`, 6/6, plus the
      full Everwood `tests/unit` suite, 30/30.)
- [x] The relevant Everwood regression suite passes.
      (`scripts/run_regression_checklist.py`, 3/3.)
- [ ] Docker startup and persistent-volume behavior are verified if the
      integration is enabled in containers. (Not exercised this pass -- only
      the native venv path was verified live.)

## Lyra integration

Lyra integration follows Everwood, but it currently has a product decision to
reconcile. Lyra's requirements say Foundry owns mechanical truth, while VTT's
current architecture assigns that role to the custom `vtt` authority.

Before changing Lyra:

- [ ] Decide whether mechanical truth lives in custom VTT, Foundry, or behind a
      host adapter that can support either implementation.
- [ ] Update Lyra's FR-D1 requirement and architecture notes to match.
- [ ] Preserve Lyra's three-bucket separation: biography, story, and campaign.
- [ ] Keep narrative campaign memory in Lyra; do not duplicate VTT mechanical
      state into semantic memory.

If custom VTT is selected, Lyra should register thin `ToolSpec` wrappers around
a context-bound `PlayerGateway`. Identity and campaign bindings remain outside
the model-visible schemas. Initial player tools should map only to the four
supported gateway operations.

## MCP stage

MCP is a transport evolution, not a new authority model. The local MCP service
must preserve the same DM/player separation and bind caller identity before
dispatching any operation.

Do not expose the current file-backed store directly to the Internet. Before
remote or multi-user operation, add at least:

- strong authentication and server-enforced campaign membership
- transactional/concurrency-safe storage
- authorization tests for every operation
- TLS/private-network deployment
- audit logging and rate limits
- backup, recovery, and secrets procedures

## Progress log

Add concise dated entries. Record decisions, verified commits, tests, and
remaining blockers; do not paste secrets or machine-specific credentials.

### 2026-09-04

- VTT package boundary completed and pushed as commit
  `acf60e5643837d9434c47489ecb1531f4265ed86`.
- Verified 12 package tests.
- Built and installed `vtt-0.1.0-py3-none-any.whl` in an isolated verification
  environment.
- Verified lightweight import, console entry points, configured storage,
  player action submission, and lazy Docling loading.
- Selected Everwood direct-package integration as the next step.
- Deferred MCP, Foundry, and remote hosting from the initial Everwood scope.

### 2026-09-04 (later) -- Everwood direct-package integration, Doug promoted

- Consumer commit: Everwood `restructure` branch, tested against `vtt` at
  `acf60e5643837d9434c47489ecb1531f4265ed86` (pinned in `pyproject.toml`'s new
  `rpg` optional-dependency extra).
- Everwood's venv pydantic bumped 2.12.5 -> 2.13.5 installing `vtt` (no other
  conflicts -- base `vtt`'s only hard dependency is pydantic).
- `src/tools/rpg.py` rewritten: DM-authority `@tool` wrappers around
  `vtt.state.store.StateStore` + `vtt.tools.dice`/`state_tools` (not
  `vtt.agents.tools`, which this guide's own comments flag as prototype-orchestrator-
  only and which eagerly imports the RAG retriever). `create_character` and the
  pending-action tools (`list_pending_actions`, `resolve_player_action`) were
  hand-written -- `StateStore`/`state_tools` don't pre-wrap those. Campaign storage
  is `VTT_DATA_DIR`/`EVERWOOD_VTT_CAMPAIGN_ID` env vars, resolved once, never a
  model-visible tool argument.
- Fixed a related pre-existing bug while wiring the shared-tool registry: the old
  dead-import `RPG_TOOLS` was in Everwood's global `ALL_TOOLS` and explicitly in
  Clara's own tool list. Both were removed -- `RPG_TOOLS` is now Doug-exclusive.
- `src/agents/tier0/doug/agent.py` promoted from stub to a real `BaseReActAgent`
  subclass (same shape as Abbie/Ezra), wired into `api/main.py`'s
  `_AGENT_BUILDERS`. Fantasy D&D only -- `vtt`'s `CharacterSheet` has no
  sci-fi/SWN fields yet, so sci-fi mode stays deferred.
- Verified live end-to-end: Doug (via a direct `chat_async` call, Claude primary)
  correctly called `create_character`, `set_scene`, `roll_dice`, and `write_event`
  in one turn from natural-language instructions, and the resulting campaign state
  persisted correctly under `data/vtt/campaigns/everwood_friday_night/`.
- New `tests/unit/test_rpg.py` (6 tests): missing-config failure, character
  create/read/update round-trip (including the "already exists" and "not found"
  failure paths), scene/event round-trip, the pending-action list/resolve loop
  (submitted directly against `StateStore`, since player-facing tools aren't wired
  yet), bad-status rejection, and campaign isolation. Full Everwood `tests/unit`
  suite: 30/30. `scripts/run_regression_checklist.py`: 3/3.
- Scope explicitly held to this guide's own sequencing: no player-facing
  `PlayerGateway` tools for any Everwood agent yet (which tier0 agent(s) act as
  players is a separate, later decision), no RAG/adventure-module lookup, no MCP,
  no Foundry, no Docker verification (native venv only), no frontend Doug page or
  `cli/chat.py` entry (API-only, matching how Abbie/Ezra were promoted).
- Next: Lyra's mechanical-truth decision (custom VTT vs. Foundry vs. adapter) is
  still open and blocks Lyra integration; player-tool wiring and a frontend Doug
  page are separate follow-ups on the Everwood side.

## Updating this guide

When an integration advances:

1. Check completed checklist items.
2. Add a dated progress-log entry with the consumer commit and tests run.
3. Update the tested VTT baseline when a newer VTT commit is adopted.
4. Record changed contracts in both this guide and the affected consumer.
5. Keep consumer-specific implementation details in the consumer repository;
   keep shared authority and transport contracts here.
