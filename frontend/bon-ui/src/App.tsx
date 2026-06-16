import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, FormEvent } from "react";
import "./App.css";

/* ------------------------------------------------------------------ */
/* Data contract                                                       */
/* These are the shapes the UI renders. They describe what the backend */
/* will eventually return. Nothing here ships any sample content.      */
/* ------------------------------------------------------------------ */

type ArtifactType = "document" | "table" | "geospatial";

type Citation = {
  id: string;
  title: string;
  source: string;
  url?: string;
  artifactType?: ArtifactType;
  locator?: string; // e.g. "p. 12", "rows 4-9", "tile EPSG:28992"
  excerpt?: string; // short supporting snippet
  traceLabel?: string;
  readinessLabel?: string;
};

type BackendCitation = Partial<Citation> & {
  manifest_id?: unknown;
  chunk_id?: unknown;
  document_id?: unknown;
  citation?: unknown;
  citation_string?: unknown;
  path?: unknown;
  source_path?: unknown;
  relative_path?: unknown;
  family?: unknown;
  source_family?: unknown;
  type?: unknown;
  trace_type?: unknown;
  cosine_distance?: unknown;
  relevance_label?: unknown;
  namespace?: unknown;
  retrieval_mode?: unknown;
  readiness?: unknown;
};

type SynthesisResponse =
  | {
      refused: false;
      answer: string; // may contain inline [1] [2] markers
      citations: Citation[];
    }
  | {
      refused: true;
      answer: string;
      citations: Citation[];
      refusalReason: string;
    };

type Status = "idle" | "loading" | "answer" | "refusal" | "error";

const ROUTER_ENDPOINT = "/api/query";

async function fetchSynthesis(question: string): Promise<SynthesisResponse> {
  const res = await fetch(ROUTER_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });

  const payload: unknown = await res.json().catch(() => null);

  if (!res.ok) {
    throw new Error(readBackendError(payload) ?? `query failed: ${res.status}`);
  }

  return toSynthesisResponse(payload);
}

function toSynthesisResponse(payload: unknown): SynthesisResponse {
  if (!payload || typeof payload !== "object") {
    throw new Error("query returned no JSON response");
  }

  const data = payload as {
    refused?: unknown;
    answer?: unknown;
    citations?: unknown;
    refusalReason?: unknown;
  };
  const citations = Array.isArray(data.citations)
    ? data.citations.map((citation, index) => toCitation(citation, index))
    : [];

  if (data.refused === true) {
    return {
      refused: true,
      answer: typeof data.answer === "string" ? data.answer : "I can't answer from the approved evidence.",
      citations,
      refusalReason:
        typeof data.refusalReason === "string" ? data.refusalReason : "router_refused",
    };
  }

  if (data.refused === false && typeof data.answer === "string") {
    return {
      refused: false,
      answer: data.answer,
      citations,
    };
  }

  throw new Error("query returned an unexpected response shape");
}

function toCitation(value: unknown, index: number): Citation {
  const raw = value && typeof value === "object" ? (value as BackendCitation) : {};
  const id = stringValue(raw.id) ?? String(index + 1);
  const manifestId = stringValue(raw.manifest_id);
  const chunkId = stringValue(raw.chunk_id);
  const documentId = stringValue(raw.document_id);
  const relativePath = stringValue(raw.relative_path);
  const sourcePath = stringValue(raw.source_path) ?? stringValue(raw.path);
  const artifactType = toArtifactType(stringValue(raw.artifactType) ?? stringValue(raw.type));

  return {
    id,
    title: stringValue(raw.title) ?? relativePath ?? chunkId ?? manifestId ?? `Source ${index + 1}`,
    source:
      stringValue(raw.source) ??
      stringValue(raw.citation_string) ??
      stringValue(raw.citation) ??
      stringValue(raw.source_family) ??
      stringValue(raw.family) ??
      "Frozen evidence manifest",
    url: stringValue(raw.url),
    artifactType,
    locator: stringValue(raw.locator) ?? traceLocator(raw, chunkId, documentId, relativePath, manifestId, sourcePath),
    excerpt: stringValue(raw.excerpt),
    traceLabel: traceLabel(raw),
    readinessLabel: readinessLabel(raw),
  };
}

function stringValue(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function toArtifactType(value: string | undefined): ArtifactType | undefined {
  if (!value) return undefined;
  if (value === "score_table" || value === "table" || value === "artifact_catalog") return "table";
  if (value === "map_raster_pointer" || value === "geospatial") return "geospatial";
  if (value === "document" || value.includes("text") || value.includes("note")) return "document";
  return undefined;
}

function readBackendError(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const data = payload as { detail?: unknown; error?: unknown; message?: unknown };
  const value = data.detail ?? data.error ?? data.message;
  return typeof value === "string" ? value : null;
}

function traceLocator(
  raw: BackendCitation,
  chunkId?: string,
  documentId?: string,
  relativePath?: string,
  manifestId?: string,
  sourcePath?: string,
): string | undefined {
  const distance =
    typeof raw.cosine_distance === "number"
      ? raw.cosine_distance.toFixed(3)
      : stringValue(raw.cosine_distance);
  if (chunkId) {
    return [chunkId, documentId ? `doc ${documentId}` : undefined, distance ? `distance ${distance}` : undefined]
      .filter(Boolean)
      .join(" | ");
  }
  return relativePath ?? manifestId ?? sourcePath;
}

function traceLabel(raw: BackendCitation): string | undefined {
  const traceType = stringValue(raw.trace_type);
  const relevance = stringValue(raw.relevance_label);
  const namespace = stringValue(raw.namespace);
  if (!traceType && !relevance && !namespace) return undefined;
  return [traceType, relevance ? `relevance ${relevance}` : undefined, namespace].filter(Boolean).join(" | ");
}

function readinessLabel(raw: BackendCitation): string | undefined {
  const readiness = raw.readiness;
  if (!readiness || typeof readiness !== "object") return undefined;
  const data = readiness as {
    user_facing_ready?: unknown;
    citation_ready?: unknown;
    analyst_citation_ready?: unknown;
    share_with_external_llm?: unknown;
    train_allowed?: unknown;
  };
  const audience =
    data.user_facing_ready === true
      ? "user-facing ready"
      : data.analyst_citation_ready === true
        ? "analyst trace"
        : "internal trace";
  const citation = data.citation_ready === true ? "citation-ready" : "not citation-ready";
  const external =
    data.share_with_external_llm === false && data.train_allowed === false
      ? "no external/training use"
      : undefined;
  return [audience, citation, external].filter(Boolean).join(" | ");
}

/* ------------------------------------------------------------------ */
/* Frontend-only controls (NOT wired to the backend yet)               */
/* These two pieces of state stay in the browser. Switching the model  */
/* or attaching a file does not change what the desk actually queries. */
/* ------------------------------------------------------------------ */

type ModelOption = {
  id: string; // ollama-style tag shown verbatim
  name: string;
  params: string;
  note: string;
};

const MODEL_OPTIONS: ModelOption[] = [
  { id: "qwen3.5:7b", name: "Qwen 3.5", params: "7B", note: "Default · balanced speed & quality" },
  { id: "qwen3.5:14b", name: "Qwen 3.5", params: "14B", note: "Sharper reasoning, slower" },
  { id: "llama3.1:8b", name: "Llama 3.1", params: "8B", note: "General purpose" },
  { id: "mistral:7b", name: "Mistral", params: "7B", note: "Fast & compact" },
  { id: "gemma2:9b", name: "Gemma 2", params: "9B", note: "Strong summarisation" },
  { id: "phi3:mini", name: "Phi-3 Mini", params: "3.8B", note: "Lightweight, low memory" },
];

const DEFAULT_MODEL = "qwen3.5:7b";

const UPLOAD_ACCEPT = ".csv,.json,.geojson,.xlsx,.xls,.txt,.pdf,.tif,.tiff,.zip";

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }
  return `${value.toFixed(value >= 10 ? 0 : 1)} ${units[unit]}`;
}

/* ------------------------------------------------------------------ */

function App() {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [response, setResponse] = useState<SynthesisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // frontend-only: not sent to the backend yet
  const [model, setModel] = useState(DEFAULT_MODEL);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);

  async function runQuery(q: string) {
    const trimmed = q.trim();
    if (!trimmed) return;

    setStatus("loading");
    setError(null);

    try {
      const result = await fetchSynthesis(trimmed);
      setResponse(result);
      setStatus(result.refused ? "refusal" : "answer");
    } catch {
      setStatus("error");
      setError(
        "The desk isn't connected to its evidence backend yet. Once the API is wired, answers will appear here.",
      );
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runQuery(question);
  }

  return (
    <main className="app-shell">
      {/* crisp, static field-survey backdrop — topographic contour lines */}
      <div className="topo" aria-hidden="true" />
      <div className="grain" aria-hidden="true" />

      <nav className="topbar">
        <span className="wordmark">
          <span className="brand-mark" aria-hidden="true">
            <LeafIcon />
          </span>
          <span className="name">NatureDesk</span>
        </span>
        <div className="toolbar">
          <ModelMenu model={model} onChange={setModel} />
          <UploadControl file={uploadedFile} onChange={setUploadedFile} />
        </div>
      </nav>

      <div className="workspace">
        <header className="hero">
          <span className="eyebrow">
            <span className="dot" aria-hidden="true" />
            Grounded synthesis &middot; every claim traced
          </span>
          <h1 className="hero-title">
            Evidence you can <span className="accent">actually trace.</span>
          </h1>
          <p className="hero-sub">
            Ask a biodiversity question and the desk answers only from its
            approved corpus, with the exact sources in hand, or it declines.
          </p>
        </header>

        <form className="query-block" onSubmit={handleSubmit}>
          <label className="query-label" htmlFor="question">
            Ask the desk
          </label>
          <div className={`query-field${question.trim() ? " has-text" : ""}`}>
            <span className="field-icon" aria-hidden="true">
              <SearchIcon />
            </span>
            <input
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a biodiversity question…"
              autoComplete="off"
            />
            <button type="submit" disabled={status === "loading" || !question.trim()}>
              <span className="btn-label">
                {status === "loading" ? "Searching" : "Search evidence"}
              </span>
              <ArrowIcon />
            </button>
          </div>
          <p className="query-hint">
            Press Enter to search. Answers come back with the exact sources
            behind them.
          </p>
        </form>

        {uploadedFile && (
          <div className="data-notice" role="status">
            <span className="data-notice-icon" aria-hidden="true">
              <UploadIcon />
            </span>
            <div className="data-notice-body">
              <p className="data-notice-title">
                Your data attached &middot; <strong>{uploadedFile.name}</strong>
              </p>
              <p className="data-notice-sub">
                {formatBytes(uploadedFile.size)} &middot; not connected to the backend
                yet, so the desk still answers from its approved corpus.
              </p>
            </div>
            <button
              type="button"
              className="data-notice-clear"
              onClick={() => setUploadedFile(null)}
              aria-label="Remove uploaded data"
            >
              <CloseIcon />
            </button>
          </div>
        )}

        <OutputPanel status={status} response={response} error={error} />
      </div>
    </main>
  );
}

/* ------------------------------------------------------------------ */
/* Local-model menu (frontend-only)                                    */
/* ------------------------------------------------------------------ */

function ModelMenu({
  model,
  onChange,
}: {
  model: string;
  onChange: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = MODEL_OPTIONS.find((m) => m.id === model) ?? MODEL_OPTIONS[0];

  useEffect(() => {
    if (!open) return;
    function onPointer(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className="model-menu" ref={ref}>
      <button
        type="button"
        className={`model-trigger${open ? " is-open" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
      >
        <ChipIcon />
        <span className="model-trigger-text">
          <span className="model-trigger-label">Model</span>
          <span className="model-trigger-id">{current.id}</span>
        </span>
        <ChevronIcon />
      </button>

      {open && (
        <div className="model-pop" role="menu">
          <p className="model-pop-head">Local model &middot; runs on Spark</p>
          <ul className="model-list">
            {MODEL_OPTIONS.map((m) => (
              <li key={m.id}>
                <button
                  type="button"
                  role="menuitemradio"
                  aria-checked={m.id === model}
                  className={`model-option${m.id === model ? " is-active" : ""}`}
                  onClick={() => {
                    onChange(m.id);
                    setOpen(false);
                  }}
                >
                  <span className="model-option-main">
                    <span className="model-option-name">
                      {m.name}
                      <span className="model-option-params">{m.params}</span>
                      {m.id === DEFAULT_MODEL && (
                        <span className="model-option-default">standard</span>
                      )}
                    </span>
                    <span className="model-option-id">{m.id}</span>
                    <span className="model-option-note">{m.note}</span>
                  </span>
                  {m.id === model && (
                    <span className="model-option-check" aria-hidden="true">
                      <CheckIcon />
                    </span>
                  )}
                </button>
              </li>
            ))}
          </ul>
          <p className="model-pop-foot">Selection is local only — not wired to the backend yet.</p>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Upload-your-own-data control (frontend-only)                        */
/* ------------------------------------------------------------------ */

function UploadControl({
  file,
  onChange,
}: {
  file: File | null;
  onChange: (file: File | null) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFile(e: ChangeEvent<HTMLInputElement>) {
    const picked = e.target.files?.[0] ?? null;
    onChange(picked);
    // reset so picking the same file again still fires onChange
    e.target.value = "";
  }

  return (
    <>
      <input
        ref={inputRef}
        type="file"
        accept={UPLOAD_ACCEPT}
        onChange={handleFile}
        hidden
      />
      <button
        type="button"
        className={`upload-btn${file ? " has-file" : ""}`}
        onClick={() => inputRef.current?.click()}
      >
        <UploadIcon />
        <span>{file ? "Replace data" : "Upload data"}</span>
      </button>
    </>
  );
}

function ArrowIcon() {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" aria-hidden="true">
      <path
        d="M5 12h13M13 6l6 6-6 6"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/* ------------------------------------------------------------------ */

function OutputPanel({
  status,
  response,
  error,
}: {
  status: Status;
  response: SynthesisResponse | null;
  error: string | null;
}) {
  // a screen reader hears the result update without needing to scroll
  const live = { "aria-live": "polite" as const, "aria-atomic": true as const };

  if (status === "idle") {
    return (
      <section className="output-panel is-idle" {...live}>
        <div className="panel-head">
          <span className="tag">Output</span>
        </div>
        <div className="panel-body">
          <LeafIcon className="idle-icon" />
          <p>
            Ask a question above. The desk returns a written answer with the
            exact sources it relied on, or it tells you plainly when the
            evidence isn't there.
          </p>
        </div>
      </section>
    );
  }

  if (status === "loading") {
    return (
      <section className="output-panel" {...live}>
        <div className="panel-head">
          <span className="tag">Working</span>
        </div>
        <div className="panel-body">
          <div className="loading-steps">
            <div className="loading-step done">
              <span className="mark" /> Reading the approved corpus
            </div>
            <div className="loading-step active">
              <span className="mark" /> Checking each claim against a source
            </div>
            <div className="loading-step">
              <span className="mark" /> Assembling the cited answer
            </div>
          </div>
        </div>
      </section>
    );
  }

  if (status === "error") {
    return (
      <section className="output-panel" {...live}>
        <div className="panel-head">
          <span className="tag">Not connected</span>
        </div>
        <div className="panel-body">
          <p className="error-text">{error}</p>
        </div>
      </section>
    );
  }

  if (!response) return null;

  if (response.refused) {
    const isBackendPending = response.refusalReason === "backend_pipeline_not_connected";

    return (
      <section className="output-panel is-refusal" {...live}>
        <div className="panel-head">
          <span className="refusal-badge">
            <ShieldIcon />
            {isBackendPending ? "Router connected, pipeline pending" : "Declined, no supporting evidence"}
          </span>
        </div>
        <div className="panel-body">
          <p className="refusal-text">{response.answer}</p>
          <p className="refusal-reason">
            Reason: <code>{response.refusalReason}</code>
          </p>
          <p className="refusal-next">
            {isBackendPending
              ? "The router has classified the question. Retrieval and synthesis still need to be connected before cited answers can appear here."
              : "Try rephrasing, narrowing the area or species, or this may sit outside the approved corpus. The desk won't answer without a source to back it."}
          </p>
        </div>
      </section>
    );
  }

  return <AnswerView response={response} />;
}

/* ------------------------------------------------------------------ */

type AnswerTab = "answer" | "sources" | "trace";

function AnswerView({
  response,
}: {
  response: Extract<SynthesisResponse, { refused: false }>;
}) {
  const [tab, setTab] = useState<AnswerTab>("answer");
  const [copied, setCopied] = useState(false);
  const cardRefs = useRef<Record<string, HTMLLIElement | null>>({});
  const pendingFocus = useRef<string | null>(null);

  const count = response.citations.length;
  const hasTrace = response.citations.some(
    (c) => c.locator || c.traceLabel || c.readinessLabel,
  );

  // A citation chip lives only on the Answer tab, so clicking one always
  // switches to Sources. Once that tab renders, scroll to and flash the
  // matching card. (Target id is held in a ref to avoid a re-render here.)
  useEffect(() => {
    if (tab !== "sources") return;
    const id = pendingFocus.current;
    pendingFocus.current = null;
    if (!id) return;
    const el = cardRefs.current[id];
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.remove("is-flash");
    void el.offsetWidth; // restart the flash animation
    el.classList.add("is-flash");
  }, [tab]);

  function focusSource(id: string) {
    pendingFocus.current = id;
    setTab("sources");
  }

  function copyAnswer() {
    void navigator.clipboard?.writeText(response.answer).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    });
  }

  const tabs: { id: AnswerTab; label: string; badge?: number }[] = [
    { id: "answer", label: "Answer" },
    { id: "sources", label: "Sources", badge: count },
    { id: "trace", label: "Trace" },
  ];

  return (
    <section className="output-panel" aria-live="polite" aria-atomic>
      <div className="panel-head panel-head--tabs">
        <div className="tabbar" role="tablist" aria-label="Answer views">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              id={`tab-${t.id}`}
              aria-selected={tab === t.id}
              aria-controls={`panel-${t.id}`}
              className={`tab${tab === t.id ? " is-active" : ""}`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
              {typeof t.badge === "number" && <span className="tab-badge">{t.badge}</span>}
            </button>
          ))}
        </div>
        <span className="grounded">
          <CheckIcon />
          {count} {count === 1 ? "source" : "sources"}
        </span>
      </div>

      {tab === "answer" && (
        <div className="panel-body" role="tabpanel" id="panel-answer" aria-labelledby="tab-answer">
          <div className="answer-head">
            <span className="answer-kicker">Short answer</span>
            <button type="button" className="copy-btn" onClick={copyAnswer}>
              {copied ? <CheckIcon /> : <CopyIcon />}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
          <p className="answer-text">
            <AnswerText text={response.answer} onCite={focusSource} />
          </p>
          {count > 0 && (
            <p className="answer-foot">
              Numbers like <span className="cite-ref cite-ref--demo">1</span> link to the
              evidence — open the <button type="button" className="inline-link" onClick={() => setTab("sources")}>Sources</button> tab.
            </p>
          )}
        </div>
      )}

      {tab === "sources" && (
        <div className="panel-body" role="tabpanel" id="panel-sources" aria-labelledby="tab-sources">
          {count === 0 ? (
            <p className="empty-note">No sources were attached to this answer.</p>
          ) : (
            <ol className="source-list">
              {response.citations.map((c) => (
                <li
                  key={c.id}
                  id={`source-${c.id}`}
                  className="source-card"
                  ref={(el) => {
                    cardRefs.current[c.id] = el;
                  }}
                >
                  <span className="source-num">{c.id}</span>
                  <div className="source-main">
                    <p className="source-title">{c.title}</p>
                    <div className="source-meta">
                      <span className="pub">{c.source}</span>
                      {c.artifactType && <ArtifactBadge type={c.artifactType} />}
                    </div>
                    {c.excerpt && <p className="source-excerpt">{c.excerpt}</p>}
                    {c.url && (
                      <a
                        className="source-link"
                        href={c.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        <LinkIcon /> Open source
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}

      {tab === "trace" && (
        <div className="panel-body" role="tabpanel" id="panel-trace" aria-labelledby="tab-trace">
          <p className="trace-intro">
            Retrieval detail behind each source — locators, relevance and readiness
            as returned by the desk.
          </p>
          {!hasTrace ? (
            <p className="empty-note">No retrieval trace was returned for this answer.</p>
          ) : (
            <ul className="trace-list">
              {response.citations.map((c) => (
                <li key={c.id} className="trace-row">
                  <span className="source-num">{c.id}</span>
                  <div className="trace-fields">
                    <p className="trace-title">{c.title}</p>
                    {c.locator && (
                      <div className="trace-field">
                        <span className="trace-key">Locator</span>
                        <span className="trace-val">{c.locator}</span>
                      </div>
                    )}
                    {c.traceLabel && (
                      <div className="trace-field">
                        <span className="trace-key">Trace</span>
                        <span className="trace-val">{c.traceLabel}</span>
                      </div>
                    )}
                    {c.readinessLabel && (
                      <div className="trace-field">
                        <span className="trace-key">Readiness</span>
                        <span className="trace-val">{c.readinessLabel}</span>
                      </div>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}

/* Renders answer text, turning [1] [2] markers into clickable refs */
function AnswerText({
  text,
  onCite,
}: {
  text: string;
  onCite: (id: string) => void;
}) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <>
      {parts.map((part, i) => {
        const match = part.match(/^\[(\d+)\]$/);
        if (!match) return <span key={i}>{part}</span>;
        const id = match[1];
        return (
          <button
            key={i}
            type="button"
            className="cite-ref"
            onClick={() => onCite(id)}
            aria-label={`Jump to source ${id}`}
          >
            {id}
          </button>
        );
      })}
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Artifact badge: encodes the three NatureDesk retrieval types        */
/* ------------------------------------------------------------------ */

function ArtifactBadge({ type }: { type: ArtifactType }) {
  if (type === "document") {
    return (
      <span className="badge document">
        <DocIcon /> Document
      </span>
    );
  }
  if (type === "table") {
    return (
      <span className="badge table">
        <TableIcon /> Score table
      </span>
    );
  }
  return (
    <span className="badge geospatial">
      <MapIcon /> Geospatial
      <span className="review-flag">· for review</span>
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Icons (inline SVG, no dependencies)                                 */
/* ------------------------------------------------------------------ */

function LeafIcon({ className = "leaf" }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path
        d="M5 19c0-7 5-13 14-14 0 9-6 14-14 14Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M5 19c3-4 6-6 10-7.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
      <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="1.8" />
      <path d="m20 20-3.5-3.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="m5 13 4 4 10-11" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 3 5 6v6c0 4 3 6.5 7 9 4-2.5 7-5 7-9V6l-7-3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M9.5 12.5 11 14l3.5-3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function LinkIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M14 7h3a5 5 0 0 1 0 10h-3M10 17H7A5 5 0 0 1 7 7h3M8 12h8" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M6 3h8l4 4v14H6V3Z" stroke="currentColor" strokeWidth="1.6" strokeLinejoin="round" />
      <path d="M14 3v4h4M9 13h6M9 16h6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

function TableIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="4" y="5" width="16" height="14" rx="1.5" stroke="currentColor" strokeWidth="1.6" />
      <path d="M4 10h16M10 10v9M4 14.5h16" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}

function MapIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M9 4 4 6v14l5-2 6 2 5-2V4l-5 2-6-2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M9 4v14M15 6v14" stroke="currentColor" strokeWidth="1.5" />
    </svg>
  );
}

function ChipIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
      <rect x="7" y="7" width="10" height="10" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <path
        d="M10 7V4M14 7V4M10 20v-3M14 20v-3M7 10H4M7 14H4M20 10h-3M20 14h-3"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

function ChevronIcon() {
  return (
    <svg className="chevron" viewBox="0 0 24 24" width="14" height="14" fill="none" aria-hidden="true">
      <path d="m6 9 6 6 6-6" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" aria-hidden="true">
      <path d="M12 16V4m0 0L7 9m5-5 5 5" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 16v2a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" aria-hidden="true">
      <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function CopyIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <rect x="9" y="9" width="11" height="11" rx="2" stroke="currentColor" strokeWidth="1.6" />
      <path d="M5 15V5a2 2 0 0 1 2-2h8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export default App;
