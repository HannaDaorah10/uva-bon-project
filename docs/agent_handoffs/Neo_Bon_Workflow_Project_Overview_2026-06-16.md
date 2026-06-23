# Team Platypus NatureDesk / BON Challenge Project Briefing

Generated on: 2026-06-16
Updated on: 2026-06-23
Repo inspected: `/home/uva-bon/naturedesk/uva-bon-project`
Branch inspected: `Neo_Bon_Workflow`
Current branch head: `079ac1c created working data upload for approved file types in session only`

## 1. Short Summary

This repo is an internal student prototype for the UvA BON / NatureDesk challenge.

The project builds a small assistant that can answer biodiversity and BON workflow questions from controlled local evidence. The key idea is simple:

> The assistant should not act like a general chatbot. It should first check what local evidence is allowed, then answer with source traces, or refuse clearly.

The project has two main tracks:

1. A web assistant for asking questions.
2. BON in a Box workflow helpers, especially for NEO SignalEyes / Boombasis data.

This is still an internal/student prototype. It is not official, public-ready, client-ready, municipal-endorsed, or scientifically validated for final external claims.

## 2. What This Project Is For

The challenge is about making biodiversity workflow evidence easier to inspect and explain.

The current project focuses on:

- The Hague / Den Haag / GM0518.
- BON in a Box workflows.
- Kroonvolume tree crown proxy data.
- NEO SignalEyes / Boombasis tree data.
- Broader NatureDesk evidence, such as IUCN and student baseline material.

The assistant is useful for questions like:

- What approved evidence do we have about The Hague?
- What does the NEO / SignalEyes / Boombasis baseline contain?
- What does the Kroonvolume proxy table say?
- Can the system show an approved map or raster pointer?
- Is this claim unsupported or outside the safe boundary?

The assistant is not meant to:

- browse the live web during a question;
- query live GBIF during a question;
- export raw evidence bundles from the chat route;
- update services, databases, vectors, or pipelines from `/api/query`;
- claim that NEO is ground truth;
- claim official Groenmonitor equivalence;
- claim municipal validation or public/client readiness.

## 3. Repo Structure

Simple view:

```text
.
|-- backend/
|   |-- server/
|   |   |-- main.py
|   |   |-- router_classifier.py
|   |   |-- frozen_evidence.py
|   |   |-- frozen_evidence_manifest.json
|   |   |-- citation_validator.py
|   |   |-- scratch_upload.py
|   |   |-- synthesis.py
|   |   |-- handlers/
|   |   |-- test_*.py
|   |   `-- README.md
|   |-- inputRouting/
|   |   |-- neo_workflow.py
|   |   |-- neo_howto.md
|   |   |-- run_workflow.py
|   |   |-- build_bon_json.py
|   |   |-- templates/
|   |   `-- runs/neo_edgecases/
|   `-- synthesis/
|       |-- synthesis_prompt.md
|       |-- qwen_synthesis.py
|       |-- bon_synthesis.py
|       `-- validation examples
|-- frontend/
|   `-- bon-ui/
|       |-- src/App.tsx
|       |-- src/App.css
|       |-- vite.config.ts
|       |-- package.json
|       `-- public/
`-- docs/
    `-- agent_handoffs/
```

What each folder means:

- `frontend/bon-ui`: the visible React web app.
- `backend/server`: the active FastAPI backend used by the web app.
- `backend/server/handlers`: the answer routes. Each handler answers a different type of question.
- `backend/inputRouting`: standalone BON workflow wrappers. These can start BON runs, so they are kept separate from chat.
- `backend/inputRouting/runs/neo_edgecases`: small recorded NEO workflow test runs.
- `backend/synthesis`: older synthesis prototype and prompt material. It is useful background, but it is not the active server route.
- `docs/agent_handoffs`: project handoff documents.

## 4. Architecture In Plain Language

The project is easiest to understand as a guarded pipeline:

```text
React frontend
  -> FastAPI backend
  -> preflight safety check
  -> local model / heuristic router
  -> evidence gate
  -> route handler
  -> citation validator
  -> answer or refusal
```

### Frontend: `frontend/bon-ui`

Why it exists:

- It gives the student or reviewer a simple web screen to ask questions.
- It shows answers, refusals, sources, and trace metadata.

How it works:

- The main UI is in `frontend/bon-ui/src/App.tsx`.
- The user types a question.
- The frontend sends `POST /api/query`.
- The frontend also sends the selected local model name.
- If a file was uploaded, the frontend first sends it to `POST /api/upload`, then sends the returned `upload_id` with the question.
- In development, `vite.config.ts` proxies `/api` to `NATUREDESK_BACKEND_URL`, defaulting to `http://127.0.0.1:8000`.

When it is used:

- Every normal user interaction starts here.
- It does not decide evidence safety itself. It displays what the backend returns.

### Backend API: `backend/server/main.py`

Why it exists:

- It is the main server that connects the UI to the controlled evidence routes.

How it works:

- `GET /health` returns a basic health response.
- `POST /api/upload` stores one uploaded file in backend memory for a short time.
- `POST /api/query` answers a question or refuses it.
- The normal evidence route uses preflight checks, routing, evidence gates, handlers, and citation validation.
- The upload route is separate and returns an "unverified uploaded file" answer, not an approved NatureDesk evidence answer.

When it is used:

- Use `/api/query` for all assistant questions.
- Use `/api/upload` only when testing the session-only file feature.

### Local Model Selection

Why it exists:

- The UI can choose which local Ollama model the backend should use for routing or upload answers.

How it works:

- The frontend sends a `model` field with `/api/query`.
- The backend checks the requested model against an allowlist.
- Allowed models include `qwen2.5:7b`, `qwen3.5:7b`, `qwen3.5:14b`, `llama3.1:8b`, `mistral:7b`, `gemma2:9b`, and `phi3:mini`.
- For the normal evidence route, an invalid model is refused.

When it is used:

- The router may use the selected local model if keyword rules do not decide the route.
- `workflow_rag` may use the selected model for narrow query-understanding.
- The scratch upload path uses the selected model to answer from the uploaded text.

### Scratch Uploads: `backend/server/scratch_upload.py`

Why it exists:

- It lets a user ask about a file they upload during the current session.

How it works:

- Supported types include YAML, JSON, JSONL, Markdown, text, CSV, HTML, PDF, and DOCX.
- The backend extracts up to 8,000 characters.
- The extracted text is kept only in process memory.
- Uploads expire after 30 minutes.
- The answer includes a warning that the uploaded file is unverified and not part of the approved evidence corpus.

When it is used:

- Only when the request includes an `upload_id`.
- It is useful for trying a file quickly.
- It should not be presented as approved evidence.

Important difference:

- Normal `/api/query` answers must pass approved evidence and citation gates.
- Upload answers are from the user file only and are marked unverified.

### Router: `backend/server/router_classifier.py`

Why it exists:

- Different questions need different evidence routes.
- A numeric table question should not go to the same handler as a broad evidence overview.

How it works:

- First it checks simple keyword and regex rules.
- The Hague crown-surface questions route to `score_table`.
- Map, raster, GeoTIFF, GeoJSON, GPKG, STAC, and spatial pointer questions route to `map_raster`.
- IUCN, BON, Red List, NEO, SignalEyes, Boombasis, Kroonvolume, Groenmonitor, The Hague, South Holland, and similar baseline questions route to `workflow_rag`.
- If those simple checks do not decide, it asks local Ollama to choose a route.
- The model is only allowed to choose a route. It is not asked to answer the biodiversity question.

When it is used:

- It runs after preflight checks and before evidence loading.

### Preflight Safety Gate: `preflight_question_gate`

Why it exists:

- Some requests are unsafe before any evidence search starts.

How it works:

- It refuses export, archive, download, bundle, and source-index requests.
- It refuses update, install, restart, rerun, database, vector, evidence-gate, or pipeline mutation requests.
- It refuses official, municipal, validated, public-ready, client-ready, ecological-decision, and management-action claims.
- It refuses unsafe NEO wording such as ground truth, proof, official alignment, municipal equivalence, or Groenmonitor equivalence.

When it is used:

- It runs at the start of the normal `/api/query` route.

### Frozen Evidence Gate: `backend/server/frozen_evidence.py`

Why it exists:

- Files should not become answer evidence just because they exist on disk.
- The project needs a clear list of approved, readable, internal-use evidence.

How it works:

- It loads `backend/server/frozen_evidence_manifest.json`.
- It checks route family, file type, approval fields, readiness fields, allowed paths, denied path fragments, readability, and optional checksums.
- For `workflow_rag`, it does not use one manifest row. It allows the route through to the separate Diver/Curator retrieval contract.

When it is used:

- It runs after the router selects a normal evidence route.

### Citation Validator: `backend/server/citation_validator.py`

Why it exists:

- The backend should not return an answer without a valid source trace.

How it works:

- Frozen-manifest citations must include required fields and readiness values.
- Retrieval-contract citations must include chunk ID, document ID, title, citation string, source path, namespace, retrieval mode, relevance label, schema versions, and safe-use metadata.
- If citations are missing or invalid, the backend turns the answer into a refusal.

When it is used:

- It runs just before any non-refusal answer is sent back to the UI.

### Active Synthesis Helpers: `backend/server/synthesis.py`

Why it exists:

- It turns approved rows or retrieval traces into careful answer text.

How it works:

- It writes deterministic Markdown sections like Answer, Evidence used, Caveats, and Human review needed.
- It keeps answers cautious and source-based.

When it is used:

- The active handlers call this file when they need answer text.

Important difference:

- `backend/server/synthesis.py` is active.
- `backend/synthesis/` is an older prototype/spec folder.

### Diver/Curator Workflow Route

Why it exists:

- Some questions need broader retrieval across the student baseline, not just one CSV row.

How it works:

- `workflow_rag` calls:

```text
/home/hans/.openclaw/workspace/tools/diver_curator_workflow.py
```

- The workflow returns two required schemas:
  - `retrieval_package.v1`
  - `source_assessment.v1`
- The handler only uses chunks assessed as strong, moderate, usable, or partial.
- Chunks must also block external LLM sharing and training use.

When it is used:

- Broad IUCN, BON, Kroonvolume, NEO, Groenmonitor, The Hague, and South Holland baseline questions.

### BON Workflow Wrappers: `backend/inputRouting`

Why they exist:

- They help translate user prompts into BON in a Box runs.

How they work:

- `neo_workflow.py` turns a natural-language prompt into NEO intent JSON.
- It validates the intent.
- It converts the intent into BON internal input keys.
- It starts BON Pipeline 41 at `http://127.0.0.1:3001`.
- It downloads known output files into a timestamped run folder.

When they are used:

- For workflow execution, debugging, and recorded NEO tests.
- They are not wired into `/api/query`.

Important difference:

- `/api/query` answers questions.
- `backend/inputRouting/neo_workflow.py` can start runs and download outputs.
- Starting a BON run is an action, so it should stay separate unless a future action gate is designed.

## 5. Handler Differences

The backend has several handlers. They are not interchangeable.

| Handler | What it answers | Data source | Safe behavior |
|---|---|---|---|
| `workflow_rag` | Broad evidence questions | Diver/Curator retrieval contract | Refuses if workflow, schemas, source assessment, or safe trace metadata fail |
| `score_table` | Approved numeric/table questions | Frozen manifest CSV rows | Reads only approved CSV rows and returns cautious table/proxy answers |
| `map_raster` | Map/raster/catalog pointer questions | Frozen manifest map/raster pointer rows | Returns pointer metadata only; does not render or export maps |
| `text_rag` | Older approved JSONL text chunks | Frozen manifest text row | Mostly closed because current text rows are not answer-ready |
| scratch upload | User-uploaded session file | In-memory uploaded text | Marked unverified; not part of approved NatureDesk evidence |
| `refusal` | Unsafe or unsupported requests | No answer evidence | Explains why the system declined |

## 6. Current Data And Evidence

### Frozen Manifest Data

Manifest file:

```text
backend/server/frozen_evidence_manifest.json
```

Current count:

- 64 rows total.
- 48 `kroonvolume_internal_proxy` rows.
- 8 `south_holland_student_retrieval` rows.
- 5 `prototype_proof` rows.
- 3 `method_context` rows.

Only 5 frozen-manifest rows currently pass the strict answer/citation gates:

- `gm0518_kroonvolume_proxy_v1.csv`
- `uncertainty_register_v1.csv`
- `ahn5_gm0518_kroonvolume_proxy_v2.csv`
- `ahn5_validation_readiness_matrix_v2.csv`
- `stac_collection.json`

How this data is accessed:

- The manifest stores absolute paths to local evidence files.
- The gate checks whether the path is allowed and readable.
- Handlers reopen only the rows that passed the gate.

How this data is understood by the model:

- For `score_table` and `map_raster`, the local model does not interpret the raw data.
- The code reads the CSV or JSON and builds a deterministic answer.
- The model may help choose a route, but it does not invent values from the table.

How this data is used in answers:

- `score_table` can answer from approved CSV rows.
- `map_raster` can return an approved STAC/catalog pointer.
- Answers cite the manifest row and keep internal/prototype caveats.

### Broad Retrieval Data

The broad retrieval route uses:

```text
/home/hans/.openclaw/workspace/tools/diver_curator_workflow.py
```

Default namespace:

```text
student_combined_baseline
```

This can include:

- IUCN Resolutions chunks.
- BON in a Box student summaries.
- IUCN Red List CSV student summaries.
- Kroonvolume Den Haag curated summaries.
- NEO SignalEyes / Boombasis Den Haag explainer chunks.

NEO-specific namespace:

```text
neo_den_haag_student_baseline
```

How this data is accessed:

- `workflow_rag` runs the Diver/Curator script as a local subprocess.
- The script is expected to query the local retrieval setup and return JSON.
- The backend requires both retrieval results and source assessment.

How this data is understood by the model:

- The backend does not ask a model to free-form browse the evidence.
- The retrieval workflow returns chunks and source assessment labels.
- The backend keeps only safe, usable traces.
- The answer text is extractive and cautious.

How this data is used in answers:

- The answer cites chunk-level traces.
- The UI can show chunk ID, document ID, namespace, relevance label, distance, readiness label, and source path.
- The answer should still be treated as internal/prototype and human-review-needed.

### NEO Workflow Data

NEO workflow wrapper:

```text
backend/inputRouting/neo_workflow.py
```

Recorded NEO run fixtures:

```text
backend/inputRouting/runs/neo_edgecases/
```

Controlled source root named by the NEO wrapper:

```text
/sources/commercial_internal/neo_signaleyes/den_haag_2026-06-15
```

What the NEO data contains:

- `crown`: tree crown polygons.
- `centerpoint`: tree or object centerpoints.
- metadata, provenance, counts, checksums, and small preview GeoJSON files.

Recorded edge-case results show:

- metadata run for crown and centerpoint;
- tiny AOI crown + centerpoint run;
- tiny AOI crown-only run;
- tiny AOI centerpoint-only run;
- tiny AOI runs with stadsdeel, wijk, and buurt context labels;
- one full-city GM0518 run request folder with prompt/config/run files, but no downloaded full-city summary/count output in this repo.

The tiny AOI count files show 1 page retrieved and 6 features per requested entity. This proves small technical capture, not city-wide conclusions.

How this data is used by the assistant:

- The chat assistant should use governed NEO explainer traces, not raw NEO exports.
- Raw NEO coordinates, raw GeoJSON, credentials, feature-level dumps, export bundles, and external LLM sharing are outside the safe answer path.

Safe wording:

- licensed comparator;
- benchmark;
- reference layer;
- local NEO dataset source-of-truth baseline under licence for non-commercial/no-fee student use.

Unsafe wording:

- ground truth;
- validation proof;
- official Groenmonitor equivalence;
- municipal validation;
- NatureDesk Crown Volume is validated.

### Scratch Upload Data

Upload endpoint:

```text
POST /api/upload
```

Where it is stored:

- Only in backend process memory.
- No file is written to disk.
- It expires after 30 minutes.

How it is accessed:

- The frontend receives an `upload_id`.
- It sends that ID with `/api/query`.
- The backend answers from the uploaded text only.

How it is understood and used:

- The selected local Ollama model receives the extracted text and the question.
- The prompt says to answer only from that uploaded text.
- The answer is marked as unverified.

Important boundary:

- Uploaded files are not approved evidence.
- Upload answers should not be mixed with frozen-manifest or retrieval-contract readiness claims.

## 7. Why The Design Is Like This

The design is conservative on purpose.

Local-only routing:

- Why: avoid sending internal or restricted evidence to external services.
- How: use simple route rules first, then local Ollama only if needed.
- When: used during question classification and narrow query understanding.

Frozen evidence manifest:

- Why: make sure only approved files can become answer evidence.
- How: require metadata, readiness fields, approved paths, and citation checks.
- When: used before `score_table`, `map_raster`, and `text_rag`.

Diver/Curator contract:

- Why: broad evidence questions need more than one manifest row.
- How: require `retrieval_package.v1` and `source_assessment.v1`.
- When: used by `workflow_rag`.

Citation validation:

- Why: no answer should leave the backend without a usable trace.
- How: validate required fields and readiness or retrieval trace metadata.
- When: final step before returning a non-refusal answer.

Separate BON workflow wrapper:

- Why: running BON is an action, not just answering a question.
- How: keep `neo_workflow.py` outside `/api/query`.
- When: use it for controlled workflow runs, not ordinary chat.

Refusal-first behavior:

- Why: guessing would be worse than saying "not enough evidence".
- How: every stage can return a refusal.
- When: unsafe wording, missing evidence, weak traces, invalid citations, or unavailable runtime services.

## 8. Full Assistant Route: From Query To Output

This is the current active route as of 2026-06-23.

1. The user opens the React app in `frontend/bon-ui`.
2. The user may choose a local model from the model menu.
3. The user may optionally upload a file.
4. If a file is uploaded, the frontend sends it to `POST /api/upload`.
5. The backend extracts text from the file, stores it in memory, and returns an `upload_id`.
6. The user types a question.
7. The React state variable `question` updates on every keystroke.
8. The user presses Enter or clicks the search button.
9. `handleSubmit()` prevents normal form submission and calls `runQuery(question)`.
10. `runQuery()` trims the question. If it is empty, it stops.
11. The UI sets status to `loading` and clears previous errors.
12. `fetchSynthesis()` sends `POST /api/query`.
13. The request body includes `question`, `model`, and `upload_id` if there is one.
14. In development, Vite proxies `/api` to `NATUREDESK_BACKEND_URL`, defaulting to `http://127.0.0.1:8000`.
15. FastAPI receives the request in `backend/server/main.py`.

If the request has `upload_id`:

16. The backend enters `scratch_query_response()`.
17. The selected model is checked against the allowlist. If invalid, this scratch path falls back to the default model.
18. `answer_from_upload()` looks up the uploaded text in memory.
19. If the upload expired or is missing, the backend refuses with `upload_expired_or_missing`.
20. If it exists, the local model answers from only that uploaded text.
21. The answer includes a warning that this is unverified uploaded-file evidence.
22. The frontend displays the answer and the unverified source card.

If the request does not have `upload_id`:

23. The backend calls `preflight_question_gate(question)`.
24. Preflight refuses unsafe export, action, official/public/validated, or unsafe NEO ground-truth/proof/equivalence wording.
25. If preflight refuses, the backend returns a refusal with no citations.
26. If preflight passes, the backend validates the requested local model.
27. If the model is not allowed, the backend refuses with `invalid_model`.
28. The backend calls `classify_question(question, model=selected_model)`.
29. Classification first checks deterministic route rules.
30. The Hague crown-surface questions route to `score_table`.
31. Map/raster/catalog/spatial pointer questions route to `map_raster`.
32. Broad IUCN/BON/NEO/Kroonvolume/Groenmonitor/The Hague/South Holland baseline questions route to `workflow_rag`.
33. If no rule matches, the classifier asks local Ollama to choose only the route.
34. The classifier validates that the route is one of `text_rag`, `workflow_rag`, `score_table`, `map_raster`, or `refusal`.
35. If classification fails, the backend refuses with `classifier_unavailable`.
36. If the classifier returns `refusal`, the backend returns a refusal answer.
37. If the route is not refusal, `gate_query_evidence(route)` runs.
38. For `score_table`, `text_rag`, and `map_raster`, the gate loads `frozen_evidence_manifest.json`.
39. The gate filters rows by route family and type.
40. Candidate rows are checked for required fields, readiness booleans, approval scope, denied public/training/external uses, allowed roots, denylisted paths, readability, and optional checksum match.
41. If no row passes, the backend refuses with `no_approved_evidence` or `readiness_gate_blocked`.
42. For `workflow_rag`, the manifest gate allows the route through under the retrieval-contract boundary.
43. The backend selects the route handler from `HANDLERS`.

For `score_table`:

44. `handlers/score_table_dynamic.py` reopens only approved rows.
45. For crown-surface questions, it selects the GM0518 municipality row and the requested or closest AHN acquisition-period proxy.
46. For other table questions, it returns a safe table preview.

For `map_raster`:

47. `handlers/map_raster.py` reads an approved local catalog or pointer.
48. It returns metadata only.
49. It does not render, download, or export map files.

For `text_rag`:

50. `handlers/text_rag.py` reads an approved JSONL file and does simple lexical chunk matching.
51. This route is mostly closed because current text rows are not answer-facing ready.

For `workflow_rag`:

52. `handlers/workflow_rag.py` builds a retrieval plan from the user question.
53. It recognizes broad inventory questions about The Hague aliases: The Hague, Den Haag, `'s-Gravenhage`, gemeente Den Haag, and GM0518.
54. Broad place-inventory questions are rewritten to this fixed canonical query:

```text
Den Haag The Hague Kroonvolume Groenmonitor NEO Boombasis urban biodiversity tree canopy evidence overview source holdings caveats
```

55. If deterministic query understanding cannot decide, a bounded local Ollama helper may classify only `place_inventory` or `literal_retrieval`.
56. That helper cannot answer, retrieve evidence, or invent a custom search query.
57. It is skipped for blocked or narrow wording such as current/live, mayor, weather, safety, policy, proof, official, validated, export, restart, or action requests.
58. The literal user question is kept as fallback.
59. The literal fallback is tried only if canonical retrieval returns `insufficient_evidence`.
60. It is not tried after workflow unavailability, subprocess failure, invalid JSON, missing schemas, or other contract failure.
61. NEO terms route to namespace `neo_den_haag_student_baseline` with default top-k 8.
62. Other workflow questions use namespace `student_combined_baseline` with default top-k 5.
63. `workflow_rag` runs `diver_curator_workflow.py` as a local subprocess.
64. The subprocess must return valid JSON.
65. The handler requires `retrieval_package` and `source_assessment`.
66. The retrieval package must have status `success`.
67. The source assessment must have status `success` and `sufficient_evidence=true`.
68. The handler keeps only chunks assessed as strong, moderate, usable, or partial.
69. Each kept chunk must have required trace fields, internal allowed-use labels, `share_with_external_llm=false`, and `train_allowed=false`.
70. The handler creates citation objects from the source traces.
71. The handler calls `backend/server/synthesis.py` to create cautious Markdown answer text.

Final response:

72. The handler returns a `HandlerResponse`.
73. Before any non-refusal answer is sent, `citations_are_valid(result.citations)` runs.
74. If citations are missing or invalid, the backend refuses with `citation_validation_failed`.
75. If citations pass, the backend returns `QueryResponse` with `refused=false`, `answer`, `citations`, `router`, and `evidence`.
76. The frontend receives the JSON.
77. `toSynthesisResponse()` normalizes backend citations into UI source cards.
78. `OutputPanel` displays loading, error, refusal, or answer state.
79. If there is an answer, `AnswerView` splits the Markdown sections.
80. The Answer tab shows the answer and clickable citation markers.
81. The Sources tab shows source cards.
82. The Trace tab shows locator, relevance, namespace, and readiness details.
83. The user receives either a cited answer or a clear refusal.

## 9. Main Limitations And How To Fix Them

### The repo is not self-contained

Why this is a limitation:

- Many evidence files and the Diver/Curator workflow live outside this repo.
- A new machine may not be able to run the full workflow from the repo alone.

How to fix it:

- Add a top-level `README.md` with exact setup steps.
- Add `.env.example` with non-secret environment variables.
- Add small safe fixture data for tests and demos.
- Document which external local paths are required.

### `workflow_rag` depends on local services

Why this is a limitation:

- It needs the Diver/Curator script, local Ollama, pgvector/PostgreSQL, and file permissions.
- If one service is missing, broad retrieval refuses.

How to fix it:

- Add a health endpoint or health page that checks each dependency separately.
- Add read-only PostgreSQL setup instructions for the `uva-bon` runtime user.
- Add mocked workflow tests and safe smoke fixtures.

### Runtime database access may fail for `uva-bon`

Why this is a limitation:

- The local `biodiversity` database may not have a confirmed read-only `uva-bon` role.

How to fix it:

- Create or document a read-only database role.
- Keep the route fail-closed if authentication is missing.
- Do not fall back to raw filesystem search.

### The assistant is cautious, not expert-polished

Why this is a limitation:

- Answers are mostly extractive.
- They are safer, but less fluent than a full expert report.

How to fix it:

- Add a reviewed synthesis layer after source assessment.
- Keep citation validation.
- Add tests proving unsupported claims still refuse.

### The frontend does not show all debug metadata

Why this is a limitation:

- Students can see sources and traces, but not all router and evidence-gate details.

How to fix it:

- Add an internal debug drawer showing route, confidence, evidence family, manifest IDs, missing metadata, and blocked gates.

### Scratch uploads are unverified

Why this is a limitation:

- Upload answers are useful for quick testing, but they are not approved evidence.
- They do not use the same full evidence-manifest path.

How to fix it:

- Keep a strong visible "unverified upload" label.
- Run preflight refusal checks before upload answers too.
- Consider refusing invalid model names instead of falling back to the default model in the upload path.
- Never mix upload answers with approved evidence readiness labels.

### NEO admin selectors are context labels

Why this is a limitation:

- `stadsdeel`, `wijk`, and `buurt` labels in the current NEO wrapper do not yet select real spatial AOIs.

How to fix it:

- Add boundary lookup for these admin units.
- Pass the selected boundary as the real AOI to the NEO pipeline.
- Add tests that prove the selected boundary changes the output area.

### Full-city NEO capture is not proven in this repo

Why this is a limitation:

- The full-city run folder records a request, but this repo does not contain downloaded full-city summary/count/provenance output.

How to fix it:

- Run full-city capture only when allowed and resourced.
- Store safe derived summaries, counts, provenance, and checksums.
- Do not commit raw licensed feature data unless governance explicitly allows it.

### Some older code remains

Why this is a limitation:

- There is historical drift: `score_table.py` versus `score_table_dynamic.py`, older NDVI workflow helpers versus NEO workflow helpers, and `backend/synthesis` versus active `backend/server/synthesis.py`.

How to fix it:

- Add a top-level architecture note naming the active paths.
- Remove or archive old paths after confirming they are no longer needed.
- Keep tests focused on the active server modules.

### Generated files are committed

Why this is a limitation:

- NEO run artifacts are useful for proof, but future outputs could become too large or too sensitive.
- The branch also tracks some Python cache files even though cache files usually should not be tracked.

How to fix it:

- Keep only small, safe proof fixtures in Git.
- Move large or sensitive generated outputs to controlled storage.
- Remove tracked `__pycache__` files in a separate cleanup commit.

## 10. Suggested Next Improvements

1. Add a top-level `README.md` with exact backend and frontend run commands.
2. Add `.env.example` for safe non-secret configuration.
3. Add an architecture diagram: frontend -> backend -> router -> gates -> handlers -> citations -> UI.
4. Add a runtime health page for backend, Ollama, Diver/Curator, PostgreSQL, and BON.
5. Add an internal UI debug drawer.
6. Confirm read-only PostgreSQL access for the `uva-bon` runtime identity.
7. Add a clean fixture folder for small non-sensitive demo data.
8. Keep raw NEO data and credentials out of the repo.
9. Generate safe `neo_metrics.json` and `neo_conclusion.md` files for NEO runs.
10. Replace NEO context-only admin selectors with real AOI boundary selection.
11. Keep `/api/query` separate from BON workflow execution unless a future action gate is designed.
12. Keep tests that prove unsafe NEO wording refuses.
13. Keep tests that prove export, action, official, public-ready, and unsupported claims refuse.
14. Keep tests that prove every approved answer has at least one valid citation.
15. Write a short grader demo script with successful questions and expected refusals.

## 11. Verification Snapshot

What was checked for this update:

- Confirmed branch `Neo_Bon_Workflow`.
- Confirmed current head `079ac1c`.
- Read the active backend API, router, evidence gate, citation validator, handlers, scratch upload path, frontend app, Vite config, NEO workflow wrapper, NEO how-to, manifest summary, and existing handoffs.
- Confirmed the frozen manifest still has 64 rows and 5 strict answer-gate rows.
- `git diff --check` passed.
- Backend unit tests passed with the repo venv: `.venv/bin/python -m unittest -v` in `backend/server`, 61 tests.

Older verification recorded in nearby handoffs:

- Frontend build passed: `npm run build` in `frontend/bon-ui`.
- API smoke tests showed `workflow_rag`, `score_table`, and refusal paths working in the checked environment.

This document is a briefing and handoff. It does not make the prototype public-ready or officially validated.
