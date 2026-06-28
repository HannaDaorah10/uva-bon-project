# BON Workflow Wrappers

This folder contains standalone scripts for running BON in a Box workflow experiments.

These scripts are not the normal web assistant route. They can start BON runs and write output folders, so they should stay separate from `/api/query` unless a reviewed action/export gate is designed.

## What Is In This Folder

```text
backend/inputRouting/
|-- run_workflow.py        # Older NDVI prompt-to-BON workflow helper
|-- build_bon_json.py      # Builds BON input JSON from an intent
|-- neo_workflow.py        # NEO SignalEyes / Boombasis workflow wrapper
|-- normalize_timeseries.py
|-- ollama_qwen_prompt_to_intent.py
|-- templates/
|   `-- bon_ndvi_template.json
|-- runs/
|   `-- neo_edgecases/     # Recorded NEO test runs
|-- HowTo.md               # Older NDVI notes
`-- neo_howto.md           # Older NEO notes
```

## Plain-Language Purpose

The scripts turn a human prompt into workflow input, send it to BON in a Box, and collect outputs.

Simple shape:

```text
prompt
  -> local Qwen intent
  -> BON input JSON
  -> BON run
  -> output files in a run folder
```

## NDVI Helper

The older NDVI helper is `run_workflow.py`.

Example:

```bash
cd ~/naturedesk/uva-bon-project/backend/inputRouting
python3 run_workflow.py "Run NDVI for Den Haag in growing season 2024 with median"
```

The current template may still be based on Zuid-Holland / South Holland. Check the template and bounding box before treating results as another area.

## NEO SignalEyes / Boombasis Helper

The NEO helper is `neo_workflow.py`.

Example smoke test:

```bash
cd ~/naturedesk/uva-bon-project/backend/inputRouting
python3 neo_workflow.py "Run a NEO smoke test for Den Haag with crown and centerpoint"
```

Common modes:

- `metadata`: checks metadata and schema information;
- `tiny_aoi`: small test area, best first smoke test;
- `full_city`: full GM0518 Den Haag capture, larger and slower.

Common entities:

- `crown`: tree crown polygons;
- `centerpoint`: tree or object centerpoints.

## Output Folders

Each run writes a timestamped folder under `runs/`.

Typical files:

```text
prompt.txt
llm_config.json
bon_run_input.json
bon_run_response.txt
output_folders.json
*_summary.json
*_counts.json
*_provenance.json
*_checksums.sha256
*_map_preview.geojson
```

Start with `*_summary.json` and `output_folders.json` when debugging a run.

## Safety And Rights Boundaries

Do not put credentials in prompts, README files, logs, screenshots, or commits.

Treat NEO SignalEyes / Boombasis data as licensed comparator material for the agreed student challenge context. Do not call it:

- ground truth;
- official validation;
- municipal approval;
- Groenmonitor equivalence;
- proof that NatureDesk Crown Volume is validated.

Use safer wording such as:

- licensed comparator;
- reference layer under licence;
- operational benchmark;
- NEO benchmark/reference layer.

Do not upload raw restricted data or full-city raw GeoJSON to external tools unless the relevant rights and readiness gates allow it.

## Checks Before Running

Check local model availability:

```bash
ollama list
```

Check BON is reachable:

```bash
curl -I http://127.0.0.1:3001
```

Check the NDVI template JSON:

```bash
python3 -m json.tool templates/bon_ndvi_template.json
```

## Important Difference From The Assistant

The assistant API answers questions.

These scripts run workflows.

Keep that difference clear when changing the code.
