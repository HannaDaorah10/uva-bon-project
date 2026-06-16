# Simple Overview: connect-synthesis

Date: 2026-06-16

Scope: internal/student prototype only. This is not public, client-ready, official, municipal-endorsed, or validated evidence.

## What changed

The backend now has a new broad retrieval route called `workflow_rag`.

This route connects `/api/query` to the controlled Diver/Curator workflow:

```text
/home/hans/.openclaw/workspace/tools/diver_curator_workflow.py
```

The default retrieval namespace is:

```text
student_combined_baseline
```

That combined baseline is meant to cover:

- IUCN Resolutions chunks.
- BON in a Box student summaries.
- IUCN Red List CSV student summaries.
- Kroonvolume Den Haag curated summaries.

The existing safer routes are still present:

- `score_table` for approved Kroonvolume CSV rows.
- `map_raster` for approved map/raster pointers for human review.
- `text_rag` for the older frozen JSONL text route, which still refuses unless its gates open.
- `refusal` for unsupported or unsafe questions.

The frontend was updated so it can display both old frozen-manifest citations and new retrieval trace citations. It can now show chunk IDs, document IDs, relevance labels, cosine distance, namespace, and internal-readiness labels such as "internal trace" or "not citation-ready".

Two supporting handoffs are also present:

- `docs/agent_handoffs/codebase_scan_connect_synthesis_2026-06-16.md`
- `docs/agent_handoffs/data_citation_inventory_connect_synthesis_2026-06-16.md`

## How it works

The request flow is now:

```text
frontend question
  -> POST /api/query
  -> preflight refusal checks
  -> route classifier
  -> evidence gate
  -> route handler
  -> citation validation
  -> frontend answer or refusal
```

Important safety order:

1. The preflight gate refuses export, archive, download, service mutation, database/vector changes, official claims, public-ready claims, and similar unsafe requests before routing.
2. The router can now choose `workflow_rag`. There are also simple keyword heuristics for IUCN, BON, Red List, Kroonvolume, Groenmonitor, The Hague, South Holland, NDVI, protected areas, indigenous peoples, and related baseline topics.
3. `workflow_rag` does not open a frozen manifest row. Instead, it is gated by the retrieval contract.
4. The new handler runs the Diver/Curator script as a subprocess and expects JSON containing both `retrieval_package.v1` and `source_assessment.v1`.
5. The handler refuses if the workflow is missing, times out, fails, returns invalid JSON, lacks the required schemas, says evidence is insufficient, or returns only weak/unusable traces.
6. The handler only uses chunks that have required trace fields, internal allowed-use labels, `share_with_external_llm=false`, and `train_allowed=false`.
7. The backend still validates citations before returning any non-refusal answer.

The answer text for `workflow_rag` is extractive and cautious. It lists the retrieved traces and says human review is still needed.

## Things done

- Added `workflow_rag` to the backend route list.
- Added route instructions for `workflow_rag` to the local Qwen router prompt.
- Added heuristic routing for broad student-baseline topics so some questions can route without calling the model.
- Added fail-closed refusal reasons for retrieval workflow problems.
- Wired `workflow_rag` into `main.py`.
- Added `backend/server/handlers/workflow_rag.py`.
- Added retrieval-contract citation validation.
- Added deterministic workflow answer synthesis.
- Updated the frozen evidence gate so `workflow_rag` uses the retrieval contract instead of pretending to be a normal frozen-manifest row.
- Updated frontend citation parsing and display for retrieval traces.
- Updated backend README with the new route, environment variables, and runtime caveat.
- Added tests for router parsing, workflow routing, evidence gating, workflow handler success/refusal, and final citation validation.
- Added handoff documentation for codebase structure, data/citation inventory, route contracts, verification, and next-agent guidance.

## Weak points and blockers

- This remains internal prototype behavior. The workflow can return internal traces that are not public, not client-ready, not official, and not citation-ready for final use.
- The workflow route depends on local runtime access to the Diver/Curator script, Ollama, and pgvector/PostgreSQL.
- If the backend runs as Linux user `uva-bon`, PostgreSQL may still need a read-only `uva-bon` role or authentication rule for the local `biodiversity` database.
- The route should refuse if that DB access is missing. It should not fall back to raw files or filesystem search.
- The `workflow_rag` answer is not a full expert synthesis. It is mostly a careful extractive answer from selected chunks.
- The router keyword heuristic is useful for demos, but it can route broad keyword questions to `workflow_rag` before the model is asked.
- The frontend shows citation traces, but it still does not show the full backend `router` and `evidence` objects.
- The handoffs record a progression in verification: an earlier code scan saw 33 backend tests and a frontend build blocked by cache permissions; the later data/citation inventory records 39 backend tests and frontend build passing after local ACL/cache repair.

## How Hans or the students should continue

1. Keep this branch as an internal/student prototype until an explicit readiness decision changes that.
2. Fix or confirm PostgreSQL read-only access for the runtime identity that will run the backend.
3. Start the backend and test the two important live paths:
   - an IUCN/BON/Kroonvolume broad question that should route to `workflow_rag`;
   - a The Hague crown-surface 2021 question that should route to `score_table`.
4. Test refusals for official, public-ready, export, download, service-change, live-data, and unsupported causal questions.
5. Decide whether `workflow_rag` should return trace-only answers in the student UI or whether it should first show a review-only result.
6. If more evidence should become answer-facing, update the governed manifest/readiness package and tests. Do not mass-open rows in code.
7. If the UI should help students debug routing, expose the backend `router` and `evidence` metadata in a small internal-only panel.
8. Keep `backend/inputRouting/run_workflow.py` and live BON execution out of `/api/query` unless a separate action/export gate is designed.

## Verification results

What I checked directly for this overview:

- Confirmed branch/status with Git using a per-command `safe.directory` override.
- Read the current git diff.
- Read `backend/server/README.md`.
- Read both existing handoffs.
- Read the new `workflow_rag` handler and relevant backend/frontend diffs.
- Ran `git diff --check`; it returned clean output.

I did not rerun backend tests or frontend build in this final overview pass because the instruction allowed writing only this overview file, and test/build tools can create caches or output files.

Verification reported by the latest handoff:

- Backend unit tests: `python3 -m unittest -v` passed, 39 tests.
- Frontend type checks and lint passed.
- Frontend build passed after repairing local generated-cache/output ACLs.
- API smoke for an IUCN indigenous/protected-area question routed to `workflow_rag` and returned 5 source traces.
- API smoke for The Hague crown-surface 2021 routed to `score_table` and returned 1 frozen-manifest citation.
- API smoke for official/validated/public-ready claims refused with `unsupported_claim`.

