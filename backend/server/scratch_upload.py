"""Ephemeral, unverified upload-and-ask path for NatureDesk.

Deliberately isolated from the approved-evidence pipeline. This module never
reads or writes frozen_evidence_manifest.json and never returns a citation
that looks like approved evidence. Extracted text lives only in this
process's memory for a short TTL — nothing is written to disk.

Supported source types (matches the knowledge_base file mix):
  .yaml / .yml   .json   .jsonl   .md   .txt   .csv   .html   .pdf   .docx
"""

from __future__ import annotations

import io
import json
import time
import uuid
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib import error, request

import yaml

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MAX_CHARS = 8_000
MAX_FILE_BYTES = 15 * 1024 * 1024
TTL_SECONDS = 30 * 60

UNVERIFIED_NOTE = (
    "This answer was generated only from a file you uploaded this session. "
    "It is not part of NatureDesk's approved evidence corpus and has not "
    "been checked or cited the way frozen evidence is."
)

_STORE: dict[str, dict] = {}  # upload_id -> {text, filename, expires}


class UploadError(ValueError):
    pass


def store_upload(filename: str, raw: bytes) -> str:
    if len(raw) > MAX_FILE_BYTES:
        raise UploadError("File is larger than the 15 MB scratch-upload limit.")

    text = _extract_text(filename, raw)
    if not text.strip():
        raise UploadError("Could not extract any readable text from that file.")

    upload_id = uuid.uuid4().hex
    _STORE[upload_id] = {
        "text": text[:MAX_CHARS],
        "filename": filename,
        "expires": time.time() + TTL_SECONDS,
    }
    _evict_expired()
    return upload_id


def answer_from_upload(question: str, upload_id: str, model: str) -> Optional[dict]:
    entry = _STORE.get(upload_id)
    if entry is None or time.time() > entry["expires"]:
        _STORE.pop(upload_id, None)
        return None

    prompt = (
        "Answer using ONLY the document text below, which a user uploaded "
        "this session. It is not verified evidence. If the answer isn't in "
        "the text, say so plainly instead of guessing.\n\n"
        f"--- DOCUMENT: {entry['filename']} ---\n{entry['text']}\n--- END DOCUMENT ---\n\n"
        f"Question: {question}"
    )
    answer_text = _call_ollama(prompt, model)
    return {
        "answer": f"{answer_text}\n\n---\n_{UNVERIFIED_NOTE}_",
        "citations": [
            {
                "id": "1",
                "title": entry["filename"],
                "source": "User-uploaded file (this session only, unverified)",
                "readiness": {
                    "user_facing_ready": False,
                    "citation_ready": False,
                    "share_with_external_llm": False,
                    "train_allowed": False,
                },
            }
        ],
    }


def _extract_text(filename: str, raw: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(raw.decode("utf-8", errors="replace"))
        return yaml.dump(data, sort_keys=False)

    if suffix == ".json":
        data = json.loads(raw.decode("utf-8", errors="replace"))
        return json.dumps(data, indent=2)

    if suffix == ".jsonl":
        lines = raw.decode("utf-8", errors="replace").splitlines()
        return "\n".join(lines[:300])

    if suffix in {".md", ".txt", ".csv"}:
        return raw.decode("utf-8", errors="replace")

    if suffix == ".html":
        return _strip_html(raw.decode("utf-8", errors="replace"))

    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    if suffix == ".docx":
        from docx import Document
        doc = Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)

    raise UploadError(f"Unsupported file type for scratch upload: {suffix or '(no extension)'}")


def _strip_html(markup: str) -> str:
    class _Stripper(HTMLParser):
        def __init__(self):
            super().__init__()
            self.parts: list[str] = []

        def handle_data(self, data):
            self.parts.append(data)

    stripper = _Stripper()
    stripper.feed(markup)
    return " ".join(stripper.parts)


def _call_ollama(prompt: str, model: str) -> str:
    body = {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.2}}
    req = request.Request(
        OLLAMA_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=90) as response:
            raw = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise UploadError(f"Local model is unreachable: {exc}") from exc
    text = raw.get("response")
    if not isinstance(text, str):
        raise UploadError("Local model returned no text.")
    return text.strip()


def _evict_expired() -> None:
    now = time.time()
    for key in [k for k, v in _STORE.items() if v["expires"] < now]:
        _STORE.pop(key, None)