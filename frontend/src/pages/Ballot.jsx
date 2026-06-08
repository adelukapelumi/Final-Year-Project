import { useState } from "react";
import { fetchBoard, submitVote, verifyBallot } from "../api";

const QUESTION =
  "Should secure diaspora voting be enabled for eligible Nigerians abroad?";

export default function Ballot({ session, onReceiptReady }) {
  const [selectedVote, setSelectedVote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  async function handleVote() {
    if (!selectedVote) {
      setError("Select Yes or No before submitting your ballot.");
      return;
    }

    setBusy(true);
    setError("");
    setSuccess("");

    try {
      const voteResult = await submitVote(session.token, selectedVote);
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
          {["yes", "no"].map((option) => {
            const selected = selectedVote === option;
            return (
              <button
                key={option}
                type="button"
                className={`option${selected ? " is-selected" : ""}`}
                onClick={() => setSelectedVote(option)}
              >
                <strong>{option === "yes" ? "Yes" : "No"}</strong>
                <div className="muted">
                  {option === "yes"
                    ? "Support enabling the secure diaspora voting flow."
                    : "Do not enable the secure diaspora voting flow."}
                </div>
              </button>
            );
          })}
        </div>

        <div className="actions">
          <button type="button" className="button" disabled={busy} onClick={handleVote}>
            {busy ? "Submitting..." : "Submit Vote"}
          </button>
        </div>

        {error ? <div className="status status--error">{error}</div> : null}
        {success ? <div className="status status--success">{success}</div> : null}
      </div>
    </section>
  );
}
