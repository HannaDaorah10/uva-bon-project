import { useRef, useState } from "react";
import type { FormEvent } from "react";
import "./App.css";

/* ------------------------------------------------------------------ */
/* Data contract                                                       */
/* Same shape your mock already used. The only additions are OPTIONAL  */
/* citation fields, so a backend that only sends id/title/source/url   */
/* still renders fine. Nothing here breaks the existing wiring.        */
/* ------------------------------------------------------------------ */

type ArtifactType = "document" | "table" | "geospatial";

type Citation = {
  id: string;
  title: string;
  source: string;
  url?: string;
  // optional, for the three NatureDesk retrieval artifact types
  artifactType?: ArtifactType;
  locator?: string; // e.g. "p. 12", "rows 4-9", "tile EPSG:28992"
  excerpt?: string; // short supporting snippet
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

/* ------------------------------------------------------------------ */
/* Backend wiring                                                      */
/* Right now this returns mock data so the page runs standalone.       */
/* To go live, replace the body with a real call, e.g.:                */
/*                                                                     */
/*   const res = await fetch("/api/query", {                           */
/*     method: "POST",                                                 */
/*     headers: { "Content-Type": "application/json" },                */
/*     body: JSON.stringify({ question }),                             */
/*   });                                                               */
/*   if (!res.ok) throw new Error("query failed");                     */
/*   return (await res.json()) as SynthesisResponse;                   */
/*                                                                     */
/* The component below does not care which one it is.                  */
/* ------------------------------------------------------------------ */

async function fetchSynthesis(question: string): Promise<SynthesisResponse> {
  await new Promise((r) => setTimeout(r, 850)); // simulate network

  // mock trigger: type "refuse" to preview the honest-refusal state
  if (question.toLowerCase().includes("refuse")) {
    return {
      refused: true,
      answer:
        "I can't answer this from the approved evidence. The corpus doesn't contain a source that supports a claim here, so I'm not going to guess.",
      citations: [],
      refusalReason: "no_supporting_source_in_corpus",
    };
  }

  return {
    refused: false,
    answer:
      "Wetland restoration tends to improve habitat connectivity when it's planned around existing Natura 2000 areas [1] and follows local hydrology and species movement corridors [2]. Modelled connectivity gains were strongest where restored patches sat within 2 km of protected sites [3].",
    citations: [
      {
        id: "1",
        title: "Natura 2000 site management guidance",
        source: "European Commission",
        url: "https://environment.ec.europa.eu/topics/nature-and-biodiversity/natura-2000_en",
        artifactType: "document",
        locator: "Section 3.2",
        excerpt:
          "Restoration measures should be coordinated with the conservation objectives of adjacent Natura 2000 sites.",
      },
      {
        id: "2",
        title: "Wetland restoration and biodiversity outcomes",
        source: "NatureDesk corpus",
        artifactType: "document",
        locator: "p. 14",
      },
      {
        id: "3",
        title: "Connectivity index by restored patch",
        source: "BON in a Box pipeline output",
        artifactType: "table",
        locator: "connectivity_scores.tsv, rows 4-9",
      },
    ],
  };
}

/* ------------------------------------------------------------------ */

const EXAMPLES = [
  "How does wetland restoration affect habitat connectivity?",
  "Which species are listed for the Meijendel dunes?",
];

function App() {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [response, setResponse] = useState<SynthesisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      setError("The desk couldn't be reached. Check the connection and try again.");
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runQuery(question);
  }

  function handleExample(example: string) {
    setQuestion(example);
    void runQuery(example);
  }

  return (
    <main className="app-shell">
      <div className="workspace">
        <header className="masthead">
          <p className="wordmark">
            <LeafIcon />
            <span className="name">NatureDesk</span>
            <span className="scope">biodiversity evidence</span>
          </p>
          <p className="boundary-note">
            <span className="dot" aria-hidden="true" />
            Answers are drawn only from the approved NatureDesk evidence corpus.
            Every claim is traced to a source, or the question is declined.
          </p>
        </header>

        <form className="query-block" onSubmit={handleSubmit}>
          <label className="query-label" htmlFor="question">
            Ask the desk
          </label>
          <div className="query-row">
            <input
              id="question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="e.g. How does wetland restoration affect habitat connectivity?"
              autoComplete="off"
            />
            <button type="submit" disabled={status === "loading" || !question.trim()}>
              <SearchIcon />
              {status === "loading" ? "Searching" : "Search evidence"}
            </button>
          </div>

          <div className="examples">
            <span className="label">Try:</span>
            {EXAMPLES.map((ex) => (
              <button
                key={ex}
                type="button"
                className="chip"
                onClick={() => handleExample(ex)}
              >
                {ex}
              </button>
            ))}
          </div>
        </form>

        <OutputPanel status={status} response={response} error={error} />
      </div>
    </main>
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
          <span className="tag">Error</span>
        </div>
        <div className="panel-body">
          <p className="error-text">{error}</p>
        </div>
      </section>
    );
  }

  if (!response) return null;

  if (response.refused) {
    return (
      <section className="output-panel is-refusal" {...live}>
        <div className="panel-head">
          <span className="refusal-badge">
            <ShieldIcon />
            Declined, no supporting evidence
          </span>
        </div>
        <div className="panel-body">
          <p className="refusal-text">{response.answer}</p>
          <p className="refusal-reason">
            Reason: <code>{response.refusalReason}</code>
          </p>
          <p className="refusal-next">
            Try rephrasing, narrowing the area or species, or this may sit
            outside the approved corpus. The desk won't answer without a source
            to back it.
          </p>
        </div>
      </section>
    );
  }

  return <AnswerView response={response} />;
}

/* ------------------------------------------------------------------ */

function AnswerView({
  response,
}: {
  response: Extract<SynthesisResponse, { refused: false }>;
}) {
  const cardRefs = useRef<Record<string, HTMLLIElement | null>>({});

  function focusSource(id: string) {
    const el = cardRefs.current[id];
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" });
    el.classList.remove("is-flash");
    void el.offsetWidth; // restart the flash animation
    el.classList.add("is-flash");
  }

  return (
    <section className="output-panel" aria-live="polite" aria-atomic>
      <div className="panel-head">
        <span className="grounded">
          <CheckIcon />
          Grounded in {response.citations.length}{" "}
          {response.citations.length === 1 ? "source" : "sources"}
        </span>
      </div>
      <div className="panel-body">
        <p className="answer-text">
          <AnswerText text={response.answer} onCite={focusSource} />
        </p>

        <div className="sources">
          <div className="sources-head">
            <h3>Sources</h3>
            <span className="count">traceable evidence</span>
          </div>
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
                    {c.locator && <span className="source-locator">{c.locator}</span>}
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
        </div>
      </div>
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

export default App;