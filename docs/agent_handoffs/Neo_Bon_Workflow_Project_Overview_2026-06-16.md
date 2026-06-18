# Team Platypus NatureDesk / BON Challenge Overview

Generated on: 2026-06-16
Refreshed on: 2026-06-18
Repo inspected: `/home/uva-bon/naturedesk/uva-bon-project`
Branch inspected: `Neo_Bon_Workflow`
Current branch head: `e7de688 Add safe local query understanding for workflow RAG`

## 1. Short Summary

This project is an internal student prototype for the NatureDesk / BON in a Box challenge. The main goal is to build an assistant that can answer biodiversity and workflow questions only when it has approved local evidence, and that refuses when the evidence is missing, unsafe, not ready, or outside the challenge scope.

The current branch adds and documents a NEO SignalEyes / Boombasis workflow route for BON in a Box. It also keeps the existing assistant route that connects the frontend to a FastAPI backend, local routing logic, frozen evidence gates, retrieval handlers, and a citation validation step.

The important idea is simple:

> The assistant should not behave like a general chatbot. It should behave like a guarded evidence desk: route the question, check whether evidence is allowed, answer with source traces, or refuse clearly.

This is still an internal/student prototype. It is not official, public-ready, client-ready, municipal-endorsed, or scientifically validated for final external claims.

## 2. What The Challenge Is About

The challenge is about making biodiversity workflow evidence easier to use and explain. The team is working around The Hague / Den Haag, BON in a Box workflows, Kroonvolume / tree crown proxy data, NEO SignalEyes / Boombasis tree data, and broader NatureDesk evidence such as IUCN and student baseline material.

The project has two connected tracks:

1. Build a usable assistant interface.
2. Keep the assistant safe by forcing it to use approved local evidence only.

The assistant is meant to help a student or reviewer ask questions like:

- What approved evidence do we have for The Hague?
- What does the NEO / Boombasis baseline contain?
- What does the Kroonvolume crown-surface proxy table say?
- Can the system show an approved map/raster pointer?
- Is a claim unsupported or outside the safe boundary?

The assistant is not meant to:

- browse live web or GBIF data during a question;
- export source packages from the chat route;
- update databases or rerun pipelines from `/api/query`;
- claim that NEO is ground truth;
- claim official Groenmonitor equivalence;
- claim municipal validation or public/client readiness.

## 3. What Has Been Built So Far

The branch contains these main pieces of progress:

- A React frontend in `frontend/bon-ui` with a search box, answer/refusal display, source tabs, and retrieval trace display.
- A FastAPI backend in `backend/server` with one main assistant endpoint: `POST /api/query`.
- A local route classifier using heuristics first and local Ollama/Qwen second.
- A frozen evidence manifest that controls which local files may be used for answer-facing routes.
- Several backend handlers: `workflow_rag`, `score_table`, `text_rag`, and `map_raster`.
- A broad retrieval route called `workflow_rag`, which calls the controlled Diver/Curator workflow and expects `retrieval_package.v1` plus `source_assessment.v1`.
- A safe local query-understanding step inside `workflow_rag` for broad The Hague / Den Haag inventory questions. It can canonicalize vague questions such as "What info do you have of The Hague?" into a richer approved retrieval query, then fall back to the literal user question if the canonical retrieval is insufficient.
- NEO-specific routing to the `neo_den_haag_student_baseline` namespace for NEO / SignalEyes / Boombasis questions.
- NEO refusal rules for unsafe wording such as ground truth, proof, official alignment, municipal equivalence, or Groenmonitor equivalence.
- A standalone NEO BON workflow wrapper in `backend/inputRouting/neo_workflow.py`.
- Edge-case NEO run folders under `backend/inputRouting/runs/neo_edgecases`.
- Handoff documentation under `docs/agent_handoffs`.

Verification from this inspection:

- Backend tests passed: `python3 -m unittest -v` in `backend/server` ran 58 tests and returned `OK`.
- Frontend build passed: `npm run build` in `frontend/bon-ui` completed successfully.
- Git status for the repo was clean before and after verification.

## 4. Repo Structure And How The Code Connects

### `frontend/bon-ui`

This is the visible web app. It is a Vite + React + TypeScript frontend.

Important files:

- `src/App.tsx`: main UI logic.
- `src/App.css`: styling.
- `vite.config.ts`: proxies `/api` requests to the backend.
- `package.json`: frontend scripts such as `dev`, `build`, and `lint`.

How it works:

- The user types a question into the search box.
- `runQuery()` calls `fetchSynthesis()`.
- `fetchSynthesis()` sends `POST /api/query` with JSON like `{ "question": "..." }`.
- The frontend receives either an answer or a refusal.
- It renders the answer, source cards, and trace details.

Important design detail: the model menu and file upload controls are frontend-only right now. They make the UI feel realistic, but they do not change the backend route yet. Uploaded files are not sent into the assistant pipeline.

### `backend/server`

This is the active assistant backend.

Important files:

- `main.py`: FastAPI app, `/health`, `/api/query`, request/response models, route dispatch, final citation validation.
- `router_classifier.py`: classifies questions into routes.
- `frozen_evidence.py`: preflight refusals and frozen evidence gates.
- `frozen_evidence_manifest.json`: local evidence index and readiness metadata.
- `citation_validator.py`: final citation checks for every non-refusal answer.
- `handlers/workflow_rag.py`: broad controlled retrieval route.
- `handlers/score_table_dynamic.py`: structured CSV/table route.
- `handlers/text_rag.py`: older lexical JSONL text route.
- `handlers/map_raster.py`: approved map/raster pointer route.
- `synthesis.py`: deterministic answer text helpers used by the active backend.
- `test_*.py`: backend tests.

This folder is the real server path. It is the part that the frontend talks to.

### `backend/inputRouting`

This folder contains standalone workflow wrappers for BON in a Box.

Important files:

- `neo_workflow.py`: current NEO SignalEyes / Boombasis workflow wrapper.
- `neo_howto.md`: detailed Dutch guide for running and interpreting the NEO workflow safely.
- `run_workflow.py`: older NDVI prompt-to-BON workflow.
- `build_bon_json.py`: helper for building BON JSON input from a config.
- `templates/bon_ndvi_template.json`: older NDVI template.
- `runs/neo_edgecases`: committed NEO test run artifacts.

This folder is not directly connected to `/api/query`. That is deliberate. It can start BON runs and download outputs, so wiring it into the assistant would cross an action/export boundary. For now, it is a workflow execution/debugging lane, not the chat answer lane.

### `backend/synthesis`

This is an older synthesis prototype and prompt scaffold.

Important files:

- `synthesis_prompt.md`: intended rules for evidence-only answer synthesis.
- `OVERVIEW_Synthesis.md`: overview of that prototype.
- `qwen_synthesis.py`, `bon_synthesis.py`, validators, examples, and dummy chunks.

Important distinction: this is not the active FastAPI synthesis module. The active backend imports `backend/server/synthesis.py`. The `backend/synthesis` folder is useful as a prompt/spec reference, but it is not the current server entry point.

### `docs/agent_handoffs`

This folder contains concise handoff documents for future agents or students:

- `simple_overview_connect_synthesis_2026-06-16.md`
- `codebase_scan_connect_synthesis_2026-06-16.md`
- `data_citation_inventory_connect_synthesis_2026-06-16.md`

These are helpful for understanding how the retrieval route was connected and what data is currently answer-facing.

## 5. Current Data And Evidence Boundary

The assistant has two main evidence modes.

### Frozen manifest evidence

The file `backend/server/frozen_evidence_manifest.json` contains 64 rows. They are grouped mainly into:

- `kroonvolume_internal_proxy`
- `south_holland_student_retrieval`
- `prototype_proof`
- `method_context`

Only 5 rows currently pass the strict answer/citation gates:

- `gm0518_kroonvolume_proxy_v1.csv`
- `uncertainty_register_v1.csv`
- `ahn5_gm0518_kroonvolume_proxy_v2.csv`
- `ahn5_validation_readiness_matrix_v2.csv`
- `stac_collection.json`

These are still internal prototype rows. They are not approved for export, external LLM sharing, training, public release, or official claims.

### Controlled retrieval contract evidence

The `workflow_rag` route does not use one frozen manifest row. Instead, it calls:

`/home/hans/.openclaw/workspace/tools/diver_curator_workflow.py`

It expects two schemas back:

- `retrieval_package.v1`
- `source_assessment.v1`

The default namespace is `student_combined_baseline`. NEO questions are routed to `neo_den_haag_student_baseline`.

The broad baseline can include IUCN, BON in a Box student summaries, IUCN Red List student summaries, Kroonvolume Den Haag summaries, and NEO explainer chunks. The NEO namespace exposes governed explainer traces, not raw NEO exports.

## 6. NEO Workflow Work On This Branch

The branch adds `backend/inputRouting/neo_workflow.py`, which translates a user prompt into a small NEO BON intent, then starts the BON Pipeline 41 run.

The NEO flow is:

1. User writes a natural-language prompt.
2. Local Qwen through Ollama turns the prompt into intent JSON.
3. The wrapper applies defaults and validates the intent.
4. The wrapper converts the intent into BON internal input keys.
5. The wrapper posts the run to BON at `http://127.0.0.1:3001`.
6. The wrapper asks BON for output folders.
7. It downloads known output files into a timestamped run folder.

Supported NEO modes:

- `metadata`: schema/metadata check.
- `tiny_aoi`: small technical smoke test.
- `full_city`: full GM0518 Den Haag capture, heavier and slower.

Supported entities:

- `crown`: tree crown polygons.
- `centerpoint`: tree/object centerpoints.

The committed edge-case folders show successful metadata and tiny AOI tests:

- metadata for `crown` and `centerpoint`;
- tiny AOI for both entities;
- tiny AOI crown-only;
- tiny AOI centerpoint-only;
- tiny AOI with context labels for stadsdeel, wijk, and buurt.

The tiny AOI runs retrieved 1 page and 6 features per requested entity. The branch also records a full-city run request folder, but that folder only contains prompt/config/run/output-folder files and no downloaded full-city summary in this repo. So the repo proves the full-city run was started/recorded, not that the full-city capture completed inside this branch.

Important NEO wording:

- Safe: licensed comparator, benchmark, reference layer.
- Unsafe: ground truth, validation proof, official Groenmonitor equivalence, municipal validation.

## 7. Why These Design Decisions Were Made

The main decisions are safety and traceability decisions.

Local-only routing was chosen so the project does not send restricted or internal evidence to external services during ordinary answering. The router uses local Ollama/Qwen when heuristics do not decide the route.

The frozen manifest exists so files are not used just because they are present on disk. A file must have the right family, type, path, readiness fields, and citation gates.

The backend fails closed. If the route is unknown, evidence is unreadable, metadata is missing, readiness is closed, citations are invalid, or the retrieval workflow fails, the assistant refuses instead of guessing.

The NEO route uses explainer traces instead of raw NEO exports because NEO is licensed data. The assistant can describe the controlled baseline, but it should not expose raw coordinates, credentials, raw GeoJSON, feature-level dumps, export bundles, external LLM sharing, or model training data.

The BON workflow wrapper is separate from `/api/query` because running a BON pipeline is an action. A chat answer route should not secretly start runs, mutate services, or export files unless a separate action gate is designed.

The frontend has model/upload controls, but they are not wired into the backend yet. This avoids giving a false impression that arbitrary uploaded files or selected models are already part of the governed evidence route.

## 8. Full Assistant Route: From Query To Output

This is the full zoomed-in route for the active assistant path.

1. The user opens the React app in `frontend/bon-ui`.
2. The user types a question into the input.
3. The React state variable `question` updates on every keystroke.
4. The user presses Enter or clicks the search button.
5. `handleSubmit()` prevents normal form submission and calls `runQuery(question)`.
6. `runQuery()` trims the question. If it is empty, it stops.
7. The UI sets status to `loading` and clears any previous error.
8. `fetchSynthesis()` sends a POST request to `/api/query`.
9. In development, Vite proxies `/api` to the backend target from `vite.config.ts`, currently defaulting to `http://127.0.0.1:8001`.
10. FastAPI receives the request in `backend/server/main.py`.
11. Pydantic validates the request against `QueryRequest`, which requires a non-empty `question` string.
12. The backend calls `preflight_question_gate(question)` before classification.
13. The preflight gate refuses unsafe request types immediately: NEO as ground truth/proof/equivalence, export/archive/download/bundle/source-index requests, service/database/vector/pipeline mutation requests, and official/public/client/validated claims.
14. If preflight refuses, the backend returns a refusal response with no citations.
15. If preflight passes, the backend calls `classify_question(question)`.
16. Classification first checks deterministic regex heuristics: The Hague crown-surface questions route to `score_table`; map/raster/catalog/spatial pointer questions route to `map_raster`; broad IUCN/BON/NEO/Kroonvolume/Groenmonitor/The Hague/South Holland baseline terms route to `workflow_rag`.
17. If no heuristic matches, the classifier calls local Ollama at `http://127.0.0.1:11434/api/generate` with model `qwen2.5:7b`.
18. The model is only asked to choose a route. It is not asked to answer the ecological question.
19. The classifier parses the model JSON and validates that the route is one of `text_rag`, `workflow_rag`, `score_table`, `map_raster`, or `refusal`.
20. If the classifier fails, the backend refuses with `classifier_unavailable`.
21. If the classifier returns `refusal`, the backend returns a refusal answer.
22. If the route is not refusal, `gate_query_evidence(route)` runs.
23. For `score_table`, `text_rag`, and `map_raster`, the gate loads `frozen_evidence_manifest.json`.
24. The gate filters manifest rows by route family/type.
25. Each candidate row is checked for required fields, readiness booleans, approval scope, denied public/training/external uses, allowed roots, denylisted path fragments, local readability, and optional checksum match.
26. If no row passes, the backend refuses with `no_approved_evidence` or `readiness_gate_blocked`.
27. For `workflow_rag`, the manifest gate allows the route through as `student_combined_baseline`, because the actual evidence gate is the retrieval contract returned by the Diver/Curator workflow.
28. The backend selects the route handler from `HANDLERS`.
29. For `score_table`, `handlers/score_table_dynamic.py` reopens only approved rows. For crown-surface questions it selects a municipality GM0518 row and the requested/closest acquisition-period proxy. For other table questions it returns a safe table preview.
30. For `map_raster`, the handler reads an approved local catalog/pointer and returns pointer metadata only. It does not render or export map files.
31. For `text_rag`, the handler reads an approved JSONL file and does lexical chunk matching. This route is mostly closed because current text rows are not answer-ready.
32. For `workflow_rag`, the handler builds a retrieval plan from the user question.
33. The retrieval plan first uses deterministic place-inventory recognition. Known The Hague aliases include The Hague, Den Haag, 's-Gravenhage, gemeente Den Haag, and GM0518.
34. Broad inventory questions about a known place are rewritten to a fixed canonical query: `Den Haag The Hague Kroonvolume Groenmonitor NEO Boombasis urban biodiversity tree canopy evidence overview source holdings caveats`.
35. If the deterministic check cannot decide, a bounded local Ollama query-understanding call may classify only `place_inventory` versus `literal_retrieval`. It is not allowed to answer, retrieve evidence, or invent a custom query.
36. The local query-understanding fallback is skipped for blocked/narrow topics such as current/live, mayor, weather, safety, policy, proof, official, validated, export, and restart/action wording.
37. The literal user question is kept as a fallback after the canonical query. The handler only tries the literal fallback when the canonical retrieval returns `insufficient_evidence`; it does not retry after workflow unavailability or contract failure.
38. `workflow_rag` chooses a namespace. NEO terms route to `neo_den_haag_student_baseline` with default top-k 8; otherwise it uses `student_combined_baseline` with default top-k 5.
39. `workflow_rag` runs `diver_curator_workflow.py` as a subprocess with `--namespace`, `--question`, and `--top-k`.
40. The subprocess must return valid JSON.
41. The handler requires both `retrieval_package` and `source_assessment`.
42. The retrieval package must have status `success`.
43. The source assessment must have status `success` and `sufficient_evidence=true`.
44. The handler keeps only chunks assessed as strong, moderate, usable, or partial.
45. Each kept chunk must have required trace fields, allowed internal use, `share_with_external_llm=false`, and `train_allowed=false`.
46. The handler creates citation objects from the source traces.
47. The handler calls deterministic synthesis helpers in `backend/server/synthesis.py`.
48. The answer is extractive and cautious. It includes sections such as Answer, Evidence used, Uncertainty and gaps, Assumptions, and Human review needed.
49. The result returns to `main.py` as a `HandlerResponse`.
50. Before sending any non-refusal answer, `citations_are_valid(result.citations)` runs.
51. If citations are missing or invalid, the backend refuses with `citation_validation_failed`.
52. If citations pass, the backend returns `QueryResponse` with `refused=false`, `answer`, `citations`, router metadata, and evidence metadata.
53. The frontend receives the JSON.
54. `toSynthesisResponse()` normalizes the backend response into frontend citation objects.
55. `OutputPanel` displays either loading, error, refusal, or answer state.
56. If it is an answer, `AnswerView` splits the Markdown sections.
57. The Answer tab shows the main answer and clickable citation markers.
58. The Sources tab shows source cards.
59. The Trace tab shows locators, relevance labels, namespaces, and readiness labels.
60. The user receives either a cited answer or a clear refusal. The system should never silently guess.

## 9. Main Weak Points

- The whole project is still an internal/student prototype, not a production assistant.
- Many evidence files live outside the repo under `/home/hans/.openclaw/...`, so the repo is not self-contained.
- `workflow_rag` depends on local runtime services: the Diver/Curator script, Ollama, pgvector/PostgreSQL, and local file permissions.
- The new query-understanding step depends on local Ollama only as a bounded intent helper. If it is disabled or unavailable, the handler falls back to deterministic/literal retrieval rather than broadening evidence access.
- If the backend runs as Linux user `uva-bon`, PostgreSQL may need a read-only role/auth rule for the local `biodiversity` database.
- The frontend shows source/trace data, but it still does not expose all router/evidence debugging metadata in an internal panel.
- The model menu and upload button are UI-only and can mislead users if this is not explained.
- NEO admin selectors are currently context/provenance labels. They do not yet select a real stadsdeel/wijk/buurt AOI.
- The full-city NEO run is recorded in the repo but not represented by downloaded summary/count/provenance output files in that run folder.
- There is some code duplication and historical drift: `score_table.py` vs `score_table_dynamic.py`, older NDVI workflow code vs NEO workflow code, and `backend/synthesis` vs active `backend/server/synthesis.py`.
- The branch tracks two Python `__pycache__` files even though `.gitignore` ignores them. Those should be removed from Git tracking later.
- The branch commits many NEO run artifacts. They are useful proof files, but future commits should be careful not to commit raw licensed data, secrets, large generated output, or files that should only live in controlled source roots.
- The current answers are cautious and extractive. That is safe, but not yet a polished expert synthesis.
- The assistant refuses many things by design. For grading, this should be presented as a safety feature, not as a failure.

## 10. What Would Make The Challenge Better Overall

The project would improve most by making the prototype easier to run, easier to inspect, and harder to misunderstand.

Useful improvements:

- Add one top-level `README.md` that explains setup, run commands, ports, and the difference between the assistant route and BON workflow wrappers.
- Add an architecture diagram showing frontend -> backend -> router -> gates -> handlers -> citations -> UI.
- Make environment variables explicit in `.env.example` without real secrets.
- Move generated run artifacts out of Git unless they are intentionally small proof fixtures.
- Add a clean fixture folder with tiny non-sensitive examples for tests and demos.
- Add an internal debug panel in the UI showing route, refusal reason, evidence family, manifest IDs, and blocked gates.
- Add a proper runtime health page checking backend, Ollama, Diver/Curator workflow, PostgreSQL, and BON separately.
- Add a read-only database setup note for the `uva-bon` user.
- Turn NEO admin-unit selectors into real AOI selectors if stadsdeel/wijk/buurt analysis is required.
- Decide whether `workflow_rag` should remain trace-only or evolve into a richer synthesis route after review.

## 11. Concrete Tasks To Further Improve The Assistant

1. Create a top-level `README.md` with exact run commands for backend and frontend.
2. Add an `.env.example` documenting `NATUREDESK_BACKEND_URL`, `NATUREDESK_DIVER_CURATOR_WORKFLOW`, `NATUREDESK_RETRIEVAL_NAMESPACE`, `NATUREDESK_RETRIEVAL_TOP_K`, and `NATUREDESK_RETRIEVAL_TIMEOUT_SECONDS`.
3. Remove tracked `backend/server/__pycache__/*.pyc` files from Git.
4. Add a UI debug drawer for router route, confidence, evidence family, manifest IDs, and blocked gates.
5. Add backend health checks for Ollama, Diver/Curator workflow availability, PostgreSQL access, and BON availability.
6. Confirm or create a read-only PostgreSQL role/auth path for the `uva-bon` runtime user.
7. Add live smoke tests for `workflow_rag` using a small safe fixture or mocked Diver/Curator payload, including broad The Hague inventory wording and literal-fallback behavior.
8. Add a clear "frontend-only" label or disablement for model selection and upload until they are actually wired.
9. Replace NEO context-only admin selectors with real AOI boundary selection if the team needs stadsdeel/wijk/buurt outputs.
10. Add a safe derived NEO metrics file, such as `neo_metrics.json`, for each run folder instead of relying on raw GeoJSON previews.
11. Add a short `neo_conclusion.md` generator that writes safe wording: technical success, counts, provenance, and explicit non-claims.
12. Keep raw NEO data and credentials out of the repo; commit only small governed summaries or fixtures.
13. Consolidate old and current synthesis code so future readers know exactly which module is active.
14. Keep tests that prove unsafe NEO wording still refuses.
15. Keep tests that prove export/action/official/public-ready requests still refuse.
16. Keep tests that prove every non-refusal answer has at least one valid citation.
17. Decide which extra manifest rows should become answer-facing, and update readiness gates through the governed evidence process rather than code shortcuts.
18. Write a short grader demo script with three successful questions and three expected refusals.
19. Add one architecture diagram to the docs so the full query-to-output path is visible at a glance.
20. Keep the project labelled as internal/student prototype until a formal readiness review says otherwise.
