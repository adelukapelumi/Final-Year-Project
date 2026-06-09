import { useState } from "react";
import { fetchBoard, submitVote, verifyBallot } from "../api";

const QUESTION =
  "Should secure diaspora voting be enabled for eligible Nigerians abroad?";
const VOTE_OPTIONS = [
  { label: "Yes", value: "yes" },
  { label: "No", value: "no" }
];
const VALID_VOTES = new Set(VOTE_OPTIONS.map((option) => option.value));

export default function Ballot({ session, onReceiptReady }) {
  const [selectedVote, setSelectedVote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const normalizedVote =
    typeof selectedVote === "string" ? selectedVote.toLowerCase() : "";
  const hasValidSelection = VALID_VOTES.has(normalizedVote);

  async function handleVote() {
    if (!hasValidSelection) {
      setError("Select Yes or No before submitting your ballot.");
      return;
    }

    setBusy(true);
    setError("");
    setSuccess("");

    try {
      const voteResult = await submitVote(session.token, normalizedVote);
      await verifyBallot(voteResult.ballot_id);
      const board = await fetchBoard();
      const boardEntry = board.ballots.find((ballot) => ballot.ballot_id === voteResult.ballot_id);

      onReceiptReady({
        ballotId: voteResult.ballot_id,
        proofHash: voteResult.proof_hash,
        timestamp: boardEntry?.timestamp || "Timestamp unavailable"
      });
      setSuccess("Vote submitted successfully.");
    } catch (requestError) {
      setError(requestError.message || "Vote submission failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page">
      <div className="hero">
        <h2>Referendum Ballot</h2>
        <p className="muted">{QUESTION}</p>
      </div>

      <div className="card stack">
        <div className="options">
          {VOTE_OPTIONS.map((option) => {
            const selected = normalizedVote === option.value;
            return (
              <button
                key={option.value}
                type="button"
                className={`option${selected ? " is-selected" : ""}`}
                onClick={() => setSelectedVote(option.value)}
              >
                <strong>{option.label}</strong>
                <div className="muted">
                  {option.value === "yes"
                    ? "Support enabling the secure diaspora voting flow."
                    : "Do not enable the secure diaspora voting flow."}
                </div>
              </button>
            );
          })}
        </div>

        <div className="actions">
          <button
            type="button"
            className="button"
            disabled={busy || !hasValidSelection}
            onClick={handleVote}
          >
            {busy ? "Submitting..." : "Submit Vote"}
          </button>
        </div>

        {error ? <div className="status status--error">{error}</div> : null}
        {success ? <div className="status status--success">{success}</div> : null}
      </div>
    </section>
  );
}
