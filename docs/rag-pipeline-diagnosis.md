# Why the DM "reads the whole dungeon" — diagnosis and fix plan

**Symptom:** the AI DM doesn't hold a consistent DM point of view. It leaks
information it shouldn't have yet, and doesn't stay scoped to "what's actually
happening in this room right now."

**Context:** the long-term plan is for this engine to run a real session —
Doug (DM) running a module for the Everwood Tier0 avatars (Clara, Rhea, Abbie,
Amy...) as player characters, meeting at Ezra's bookstore. So the DM/player
knowledge boundary isn't a nice-to-have, it's the actual product requirement:
Doug has to know things the players don't.

---

## Current architecture (as of this diagnosis)

```
                    ┌─────────────────────────────┐
                    │   knowledge_base/dnd/*.pdf   │   <- paid modules
                    └───────────────┬───────────────┘
                                    │  ingest.py
                                    │  (Docling -> markdown -> 1000-char chunks)
                                    ▼
                    ┌─────────────────────────────┐
                    │  Chroma vector DB            │
                    │  metadata: {"source": file}  │   <- that's ALL the metadata
                    │  no room/section/visibility  │
                    └───────────────┬───────────────┘
                                    │  retriever.py
                                    │  similarity_search(query, k=3)
                                    │  <- searches the WHOLE corpus, every time
                                    ▼
                    ┌─────────────────────────────┐
                    │  query_adventure_module tool │
                    │  "...module text, rules,     │
                    │   AND SECRETS" (its own      │
                    │   docstring says this)       │
                    └───────┬───────────────┬───────┘
                            │               │
                  ┌─────────▼──────┐ ┌───────▼─────────┐
                  │    dm_node     │ │   player_node    │
                  │  GAME_TOOLS    │ │  GAME_TOOLS      │   <- SAME tool list.
                  │  (all 7 tools) │ │  (all 7 tools)   │      player_node can
                  └────────────────┘ └──────────────────┘      call the secrets
                                                                 tool directly.

  state["messages"] replays EVERY past message (incl. every past tool
  result) into BOTH nodes, every single turn, forever. Nothing prunes it.
```

## The four root causes

1. **Retrieval has no scope.**
   `src/rag/retriever.py::query_knowledge()` runs
   `vector_store.similarity_search(query, k=3)` against the *entire* Chroma
   DB — every ingested module, every room, all at once. There's no concept of
   "only search the current room." A player action in Room 1 can retrieve
   text from Room 12.

2. **Ingestion throws away structure.**
   `src/rag/ingest.py::ingest_pdfs()` converts each PDF straight to markdown
   and chunks it by raw character count (`MarkdownTextSplitter(chunk_size=1000)`).
   The only metadata kept is `{"source": filename}`. There's no room ID, no
   tag for "this is read-aloud text vs. a DM-only secret vs. a stat block."
   Nothing downstream *can* filter by relevance or by who's allowed to see it,
   because that information was never captured.

3. **Nothing prunes retrieved text out of context.**
   `src/engine/orchestrator.py` — both `dm_node` and `player_node` build their
   prompt as `messages = [prompt] + state["messages"]`, replaying the *full*
   message history every turn, including every past `ToolMessage`. Once
   `query_adventure_module` returns a chunk, it's in context permanently and
   compounds turn over turn. This alone would produce "wants to read the
   whole dungeon" even with perfect retrieval scoping.

4. **No knowledge wall between DM and player.**
   `player_node` is bound to the exact same `GAME_TOOLS` list as `dm_node` —
   including `query_adventure_module`, whose own docstring says it returns
   "official adventure module text, rules, **and secrets**." The player agent
   can query DM secrets directly. There is currently no architectural
   separation of what each role is allowed to know.

---

## Fix plan (in priority order)

1. **Split the tool belt.**
   `dm_node` keeps `query_adventure_module`, `set_scene`, `write_event`.
   `player_node` loses `query_adventure_module` entirely — keeps
   `roll_dice`, `read_character`, `update_character`. This is the direct fix
   for DM/player POV bleed.

2. **Scope retrieval to the current room.**
   Add a `location` field to `GameState` (and to `scene.json`). Tag each
   Chroma chunk with a room/section ID at ingest time. Filter
   `similarity_search` with `where={"room": current_location}` instead of
   searching the whole corpus.

3. **Re-ingest with structure-aware chunking.**
   Split on the module's own room/section headers (Docling preserves headers
   in its markdown output) instead of pure character-count chunking. Tag each
   chunk `read_aloud` / `dm_secret` / `stat_block` so the DM prompt can
   distinguish "safe to paraphrase to players" from "keep to yourself."

4. **Stop replaying raw tool results forever.**
   Summarize or drop old `ToolMessage`s from history after a turn or two, so
   a RAG pull from three turns ago stops bleeding into current narration.

5. **(Later, when this connects to Everwood)** generalize `player_node` from
   one hardcoded PC (Rhea) into one agent instance per avatar at the table.

---

*Written 2026-07-26 as a reference doc — not code. See the fix plan above for
the actual implementation order when you're ready to start.*
