import { useState } from "react";
import "./App.css";

type Citation = {
  title: string;
  source: string;
  url: string;
};

type SynthesisResponse = {
  answer: string;
  citations: Citation[];
  refusal: boolean;
  refusalReason?: string;
};

const fakeCitedAnswer: SynthesisResponse = {
  refusal: false,
  answer:
    "Based on the available sources, the area shows signs of ecological pressure, especially around habitat fragmentation and land-use change.",
  citations: [
    {
      title: "Copernicus Land Monitoring Service",
      source: "European Environment Agency",
      url: "https://land.copernicus.eu/",
    },
    {
      title: "GBIF Species Occurrence Data",
      source: "GBIF",
      url: "https://www.gbif.org/",
    },
  ],
};

const fakeRefusal: SynthesisResponse = {
  refusal: true,
  answer: "",
  citations: [],
  refusalReason:
    "I cannot answer this reliably because the available evidence is too weak or missing required source data.",
};

export default function App() {
  const [question, setQuestion] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "answer" | "refusal">("idle");

  function handleSubmit() {
    setStatus("loading");

    setTimeout(() => {
      if (question.toLowerCase().includes("refuse")) {
        setStatus("refusal");
      } else {
        setStatus("answer");
      }
    }, 700);
  }

  const response =
    status === "refusal" ? fakeRefusal : status === "answer" ? fakeCitedAnswer : null;

  return (
    <main className="page">
      <section className="shell">
        <h1>BON Synthesis Preview</h1>

        <div className="inputRow">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask a biodiversity question..."
          />
          <button onClick={handleSubmit}>Submit</button>
        </div>

        <section className="outputPanel">
          {status === "idle" && <p className="muted">Submit a question to preview the output.</p>}

          {status === "loading" && <p className="muted">Loading synthesis...</p>}

          {response && response.refusal && (
            <div>
              <h2>Cannot Answer Reliably</h2>
              <p>{response.refusalReason}</p>
            </div>
          )}

          {response && !response.refusal && (
            <div>
              <h2>Answer</h2>
              <p>{response.answer}</p>

              <h3>Sources</h3>
              <ul>
                {response.citations.map((citation) => (
                  <li key={citation.url}>
                    <a href={citation.url} target="_blank">
                      {citation.title}
                    </a>
                    <span> — {citation.source}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}