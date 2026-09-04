# Everwood and Lyra integration architecture

## Decision

VTT is a separately versioned campaign authority. Everwood and Lyra are
clients. During local development they may import the lightweight package
directly; the durable integration boundary is the same player/DM contract
exposed over MCP.

One human currently plays with AI avatars. This lets the first deployment use
a trusted local process and context binding instead of a full account and role
system. The API still prevents an avatar from accidentally mutating mechanics,
reading another character, or bypassing DM pacing. Authentication becomes
mandatory before exposing the service beyond the local machine.

## Capability boundary

Player-facing operations:

- `get_my_character`
- `get_player_scene`
- `submit_player_action`
- `get_action_result`
- later: `get_public_events`, `list_campaigns`, `open_campaign`, `end_session`

DM-only operations:

- adventure-module retrieval and hidden state
- authoritative dice and rules resolution
- character, scene, inventory, and encounter mutation
- action-result publication

The DM should reveal one actionable scene at a time. Module retrieval remains
section-scoped, and player clients never receive retrieved source text or the
private DM prompt. This preserves the existing protection against narrating an
entire dungeon before the characters interact with it.

## Deployment stages

1. **Local package:** editable install for development and direct Python use.
2. **Local MCP:** one VTT process owns state; Everwood and Lyra connect over
   stdio or localhost. This is the recommended six-month operating mode.
3. **Private remote MCP:** host the same server behind TLS and strong client
   authentication. Use a private network such as Tailscale before considering
   a public endpoint.
4. **Multi-user:** add server-enforced accounts, campaign membership, player
   ownership, rate limits, audit logs, and concurrency-safe transactional
   storage before inviting other people.

Do not expose the current file-backed state service directly to the Internet.
JSONL append is sufficient for a single local authority but is not a remote
multi-writer database.

## Additional RPG systems

The transport and action envelope should remain system-neutral. D&D, Stars
Without Number, and future games should be ruleset modules behind the same
authority rather than separate copies of the service. A later ruleset protocol
should own:

- ruleset identifier and version
- character-sheet validation and player-visible projection
- action validation and resolution
- dice conventions
- encounter/initiative mechanics
- optional module-ingestion conventions

The current `CharacterSheet` is D&D-shaped (`class`, armor class, spells), so it
must not become the universal cross-system contract. Preserve it as the first
D&D ruleset model and introduce the ruleset interface before adding the second
game. Avoid creating a plugin abstraction with only one implementation.

Python entry points can provide third-party rulesets later, for example through
a `vtt.rulesets` entry-point group. Built-in rulesets can live under
`vtt.rulesets.<system>` while sharing the same player/MCP surface.

## Dependency and release policy

VTT uses minimum-version constraints rather than exact pins in published
metadata. Consumer applications should select a tested VTT release or Git
commit; their lock files should capture the resolved transitive environment.
This allows routine dependency upgrades without making every fresh install an
untested moving target.

Docling stays in the `ingest` extra. Runtime clients should not install it.
The RAG and DM stacks remain separate extras so Lyra can use the player client
without inheriting Tabletop's model and vector-store dependencies.
