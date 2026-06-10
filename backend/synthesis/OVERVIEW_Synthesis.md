# NatureDesk — Synthesis Module Overview

This document explains what the files in `backend/synthesis/` are supposed to do,
how they fit together, and the rules the module is built to enforce. It is a
summary of the current state of the folder, written for someone who needs to
understand the module without reading every file.

> **Owner:** Santino (LLM/Prompt Lead)
> **Last updated content reference:** `synthesis_prompt.md` dated 2026-06-09

---

## 1. What this module is for

The **synthesis module** is the final reasoning step of NatureDesk. Its single
job is:

> Take an ecologist's question **plus a small set of pre-approved evidence
> chunks**, and produce a strictly cited answer — or refuse if the evidence
> doesn't support one.

It is deliberately **not** a general biodiversity expert, **not** a search
engine, and **not** a legal/policy/planning advisor. It may only use the
evidence handed to it in the current request. Anything outside that evidence is
treated as unknown.

The defining principle of the whole module is **evidence-only answering with
mandatory citations**. Every factual claim must trace back to a provided chunk,
or the answer is considered a failure.

---

## 2. The big picture / data flow

The module sits at the end of a retrieval pipeline (the "router" and retrieval
steps live outside this folder):

```
  ecologist's question
          │
          ▼
  [ router / retrieval ]   ← not in this folder
          │  passes ≤ 5 "challenge-approved" chunks, ordered by score
          ▼
  [ synthesis step ]       ← THIS folder
          │  builds system prompt + user message, calls the LLM at temp 0
          ▼
  LLM response (Answer template  OR  Refusal template)
          │
          ▼
  [ response validation ]  ← checks required sections + citations exist
          │
          ▼
  validated answer  OR  forced refusal
```

The actual production entry point — `synthesis.py` — is **referenced but does
not exist yet** in this folder. What exists today is: the prompt spec, a
runnable end-to-end test harness, sample outputs, validation scripts, and dummy
data. See [Section 5](#5-status--whats-missing).

---

## 3. File-by-file summary

| File | Type | Purpose |
|------|------|---------|
| `synthesis_prompt.md` | Spec | The canonical system prompt, all hard constraints, the answer/refusal templates, and developer integration notes. The source of truth. |
| `test_synthesis.py` | Script | Runnable harness that calls a live LLM with dummy chunks and checks the output format for three scenarios. |
| `dummy_chunks.py` | Data | Fake evidence chunks used by the test harness (an answerable set and an empty refusal set). |
| `test_response.md` | Sample | A captured example of a **valid answer** (the SHI 2019–2024 case). |
| `refusal_response.md` | Sample | A captured example of a **valid refusal** (butterfly data from 1970). |
| `validate_response.py` | Script | Checks a saved answer file for the required sections and citations. |
| `validate_refusal.py` | Script | Checks a saved refusal file for correct refusal structure (and that it is *not* secretly an answer). |
| `requirements.txt` | Config | Python dependencies: `openai` and `python-dotenv`. |
| `__init__.py` | Package | Empty; marks `synthesis/` as a Python package. |

---

### 3.1 `synthesis_prompt.md` — the contract (source of truth)

This is the most important file. It specifies the **system prompt** and the
rules the model must follow. The key pieces:

**Role:** NatureDesk explains and summarizes *approved BON in a Box evidence*
only.

**Seven hard constraints:**

1. **Evidence-only answering** — no training knowledge, no background
   assumptions, no web, no external tools. Missing info = unknown.
2. **Citation requirement** — every factual claim must be cited as
   `(Source: [title], chunk [chunk_id])`. An uncited claim is a failure.
3. **No inference beyond evidence** — no extrapolation, prediction,
   speculation, or generalization. (Example: a drop in SHI from 0.82 → 0.77 may
   be *reported*, but "habitat is collapsing" is forbidden.)
4. **Refusal policy** — refuse when there is no evidence, evidence doesn't
   answer the question, or the question needs legal/policy/predictive/causal
   conclusions or out-of-corpus data. No partial answers.
5. **Source fidelity** — copy `chunk_id`, `title`, and `citation_string`
   exactly; quote a short verbatim passage.
6. **Scientific caution** — never assert causes, impacts, or mechanisms unless
   explicitly stated. Correlation ≠ trend ≠ cause.
7. **Missing information** — answer only what's supported and describe the rest
   under "Uncertainty and gaps."

**Mandatory answer template** (five sections):

1. `## Answer` — one concise, fully-cited paragraph
2. `## Evidence used` — a table (Chunk ID · Title · Citation · Relevant passage)
3. `## Uncertainty and gaps` — what the evidence does *not* establish
4. `## Assumptions` — any interpretation beyond literal wording (`None` if none)
5. `## Human review needed` — a concrete next step / which expert or source

**Refusal template:** `## Refusal` + the question + a `Reason:` + "What a human
should consult instead:".

**Developer notes** at the bottom define how the calling code should behave:

- **User-message format:** the verbatim question followed by each chunk wrapped
  in `--- CHUNK --- … --- END CHUNK ---` with `chunk_id`, `title`,
  `citation_string`, `source_family`, `readiness_label`, and `text`.
- **Retrieval rules:** only pass chunks where
  `readiness_label == challenge-approved`; never pass excluded/blocked chunks,
  raw documents, PDFs, or web results. **Max 5 chunks**, ordered by score.
- **Temperature:** `0.0`–`0.1` (this is a citation task, not a creative one).
- **Response validation:** after the model replies, the code must confirm the
  "Evidence used", "Uncertainty and gaps", and "Human review needed" sections
  exist and at least one `(Source:` citation is present — **otherwise return a
  refusal**.
- **Router refusal conditions:** the upstream router should refuse *before*
  synthesis when there are no/excluded chunks, or the question asks for legal,
  policy, predictive, or unsupported-causal answers.

It closes with four **validation prompts** (a should-answer, two should-refuse,
and a should-narrow case) used to sanity-check behavior.

---

### 3.2 `test_synthesis.py` — the live end-to-end harness

A runnable script that exercises the real synthesis behavior against an LLM:

- Creates an `OpenAI` client from `OPENAI_API_KEY`.
- Defines `format_chunks(chunks)` — renders the chunk list into the
  `--- CHUNK ---` text block the prompt expects (or `[No evidence retrieved]`
  when empty).
- Defines `synthesize(question, chunks)` — sends a `developer` (system) message
  plus a `user` message (`Question: … / Approved evidence: …`) to the model and
  returns the text output.
- Defines `run(question, chunks, label)` — prints the answer and runs lightweight
  format checks (looks for `## Evidence used` / `## Refusal`, `## Uncertainty`,
  `## Human review`).
- Executes **three scenarios** at the bottom:
  1. **ANSWERABLE** — the SHI 2019–2024 question with `DUMMY_CHUNKS`.
  2. **REFUSAL – no evidence** — the 1970 butterfly question with empty chunks.
  3. **REFUSAL – legal question** — a housing-legality question (should refuse
     even though evidence is present).

> ⚠️ **Two things to know about this file:**
>
> 1. It uses a **condensed, slightly different system prompt** written inline,
>    *not* the full canonical prompt from `synthesis_prompt.md`. Notably its
>    citation format includes the citation string —
>    `(Source: [title], chunk [chunk_id], [citation_string])` — whereas the spec
>    uses `(Source: [title], chunk [chunk_id])`. The canonical spec is the
>    source of truth; the test prompt is a simplified stand-in.
> 2. It targets model `"gpt-5.5"` with `reasoning={"effort": "low"}`. Confirm
>    that model id / API shape is correct for your environment before relying on
>    it.

---

### 3.3 `dummy_chunks.py` — test fixtures

Provides two fixtures consumed by `test_synthesis.py`:

- **`DUMMY_CHUNKS`** — two `challenge-approved` chunks:
  - `bon-shi-001`: documentation explaining what the Species Habitat Index (SHI)
    is (a 0–1 measure of suitable habitat remaining vs. a baseline).
  - `bon-shi-002`: a TSV-style score table showing SHI declining from `0.82`
    (2019) to `0.77` (2024) for The Hague Groenmonitor.
- **`DUMMY_REFUSAL_CHUNKS`** — an empty list, to drive the no-evidence refusal
  path.

Each chunk carries the full metadata the prompt expects: `chunk_id`, `title`,
`citation_string`, `source_family`, `readiness_label`, `text`.

---

### 3.4 `test_response.md` & `refusal_response.md` — golden samples

Captured "known-good" outputs used as reference and as input to the validators:

- **`test_response.md`** — a model answer to the SHI question. It correctly cites
  both chunks, fills the Evidence-used table, states what the evidence does *not*
  establish (causes, species included, broader conditions), reports
  `Assumptions: None`, and proposes a concrete human-review step. This is the
  shape every valid answer should match.
- **`refusal_response.md`** — a clean refusal for the 1970 butterfly question:
  the `## Refusal` header, the quoted question, a `Reason:` (no evidence in
  corpus), and a "What a human should consult instead:" suggestion (historical
  monitoring datasets, archives, museum collections).

---

### 3.5 `validate_response.py` & `validate_refusal.py` — format checkers

Small standalone scripts that read a saved markdown file and print pass/fail
checks. They encode the same structural rules the production code is supposed to
enforce.

**`validate_response.py`** reads `test_response.md` and checks for:

- `## Evidence used` section
- `## Uncertainty and gaps` section
- `## Human review needed` section
- at least one `(Source:` citation
- (also reports if a `## Refusal` was used instead)

**`validate_refusal.py`** reads `refusal_response.md` and checks that it:

- has a `## Refusal` header
- has a `Reason:`
- has "What a human should consult instead:"
- does **not** contain a `## Answer` section (a refusal must not smuggle in an
  answer)

…then prints a single `VALID REFUSAL` / `INVALID REFUSAL` verdict. (Its inline
comments are in Dutch; the logic is straightforward.)

> Note: both validators have the target filename **hard-coded** and read from the
> current working directory, so run them from inside `backend/synthesis/`.

---

### 3.6 `requirements.txt` & `__init__.py`

- **`requirements.txt`** — `openai>=1.0.0` and `python-dotenv>=1.0.0`. The
  `dotenv` dependency implies the API key is expected to come from a `.env` file
  in real use (though `test_synthesis.py` currently reads the env var directly).
- **`__init__.py`** — empty file that makes `synthesis/` an importable Python
  package.

---

## 4. The rules this module enforces (at a glance)

These are the guarantees the module exists to provide:

1. **Grounded** — answers use only the supplied, `challenge-approved` evidence.
2. **Cited** — every factual claim carries a `(Source: …)` citation; uncited
   claims are failures.
3. **Structured** — answers always follow the five-section template; refusals
   always follow the refusal template, and the two never mix.
4. **Cautious** — no causes, predictions, legal/policy conclusions, or
   generalizations beyond the literal evidence.
5. **Fail-closed** — if the response is malformed or missing required
   sections/citations, the system returns a refusal rather than a shaky answer.
6. **Bounded** — at most 5 chunks, ordered by retrieval score, temperature ~0.

---

## 5. Status / what's missing

What currently exists is a **specification + test/validation scaffold**, not yet
the production module:

- ❌ **`synthesis.py` does not exist yet.** Both `synthesis_prompt.md` ("Used by:
  synthesis.py") and its developer notes ("synthesis.py should verify…")
  reference it, but no such file is present anywhere in the repo. The production
  entry point still needs to be written.
- ⚠️ **Prompt drift.** `test_synthesis.py` embeds a condensed system prompt that
  differs from the canonical `synthesis_prompt.md` (different citation format).
  When `synthesis.py` is built, it should use the canonical spec.
- ⚠️ **Model id.** `test_synthesis.py` calls `model="gpt-5.5"` via the Responses
  API — verify this matches an available model/API in your environment.
- ⚠️ **Validators are file-pinned.** `validate_response.py` and
  `validate_refusal.py` read fixed filenames from the cwd; they're handy spot
  checks but would need parameterizing to validate arbitrary live responses.

### Suggested next step

Implement `synthesis.py` as the real entry point: build the user message per the
spec's chunk format, enforce the `challenge-approved` / max-5 / temperature
rules, call the model with the **canonical** system prompt, then run the
response-validation checks (reusing the logic in `validate_response.py`) and
fall back to a refusal when validation fails.

---

## 6. How to run what exists today

```bash
cd backend/synthesis
pip install -r requirements.txt

# Live end-to-end test (needs a valid API key):
export OPENAI_API_KEY=...        # or put it in a .env file
python test_synthesis.py

# Offline format checks on the saved sample outputs:
python validate_response.py      # checks test_response.md
python validate_refusal.py       # checks refusal_response.md
```
