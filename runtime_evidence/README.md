# Runtime Evidence

This folder contains local evidence files that the backend can reference through its frozen evidence manifest.

These files are for the internal prototype. They are not a public release package.

## What Is Here

Current files are under:

```text
runtime_evidence/kroonvolume/
```

They include Kroonvolume-related CSV and STAC/catalog-style files for internal research prototype use.

Examples:

```text
gm0518_kroonvolume_proxy_v1.csv
uncertainty_register_v1.csv
ahn5_gm0518_kroonvolume_proxy_v2.csv
ahn5_validation_readiness_matrix_v2.csv
stac_collection.json
```

## How The Backend Uses These Files

The backend does not treat every file on disk as answer evidence.

Instead, `backend/server/frozen_evidence_manifest.json` lists which files are allowed, what route can use them, and what readiness gates apply.

The backend then checks:

- approval fields;
- allowed use;
- denied use;
- readiness metadata;
- allowed root paths;
- readability;
- optional checksums;
- citation validity.

## Important Boundaries

Do not call these files official, public-ready, client-ready, municipal-endorsed, or validated unless a separate readiness decision says so.

Do not add new files here and assume the assistant can use them. Update the governed manifest and tests together.

Do not use this folder as an export bundle.
