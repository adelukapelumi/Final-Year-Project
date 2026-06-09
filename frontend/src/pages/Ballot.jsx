import { useState } from "react";
import Icon from "../components/Icon";
import { fetchBoard, submitVote, verifyBallot } from "../api";

const QUESTION =
  "Should secure diaspora voting be enabled for eligible Nigerians abroad?";
const VOTE_OPTIONS = [
  {
    label: "Yes",
    value: "yes",
    detail: "I support enabling secure diaspora voting for eligible Nigerians abroad."
  },
  {
    label: "No",
    value: "no",
    detail: "I do not support enabling secure diaspora voting at this time."
  }
];

const processingLabels = {
  generating: "Generating zk-STARK proof...",
  verifying: "Verifying ballot validity...",
  publishing: "Publishing proof receipt..."
};

function minimumStageDuration(milliseconds = 650) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

export default function Ballot({ session, onReceiptReady }) {
  const [selectedVote, setSelectedVote] = useState("");
  const [step, setStep] = useState("ballot");
  const [processingStage, setProcessingStage] = useState("generating");
  const [error, setError] = useState("");
  const selectedOption = VOTE_OPTIONS.find((option) => option.value === selectedVote);

  async function handleVote() {
    if (!selectedOption) {
      setError("Select Yes or No before reviewing your ballot.");
      return;
    }

    setStep("processing");
    setProcessingStage("generating");
    setError("");

    try {
      const voteResult = await submitVote(session.token, selectedVote);
      setProcessingStage("verifying");
      const [verification] = await Promise.all([
        verifyBallot(voteResult.ballot_id),
        minimumStageDuration()
      ]);
      setProcessingStage("publishing");
      const [board] = await Promise.all([fetchBoard(), minimumStageDuration()]);
      const boardEntry = (board.ballots || []).find(
        (ballot) => ballot.ballot_id === voteResult.ballot_id
      );

      onReceiptReady({
        ballotId: voteResult.ballot_id,
        proofHash: voteResult.proof_hash,
        timestamp: boardEntry?.timestamp || "Timestamp unavailable",
        verified: Boolean(verification.verified)
      });
    } catch (requestError) {
      setError(requestError.message || "Vote submission failed.");
      setStep("review");
    }
  }

  if (step === "processing") {
    return (
      <section className="page narrow-page">
        <div className="processing-card">
          <div className="proof-animation">
            <span className="proof-animation__ring" />
            <span className="proof-animation__ring proof-animation__ring--two" />
            <span className="proof-animation__core"><Icon name="shield" size={34} /></span>
          </div>
          <span className="section-kicker">Secure submission in progress</span>
          <h1>{processingLabels[processingStage]}</h1>
          <p>Keep this window open while your ballot proof is processed.</p>

          <div className="process-steps">
            {Object.entries(processingLabels).map(([key, label]) => {
              const stages = ["generating", "verifying", "publishing"];
              const currentIndex = stages.indexOf(processingStage);
              const itemIndex = stages.indexOf(key);
              const complete = itemIndex < currentIndex;
              const active = key === processingStage;
              return (
                <div className={`${active ? "is-active" : ""}${complete ? " is-complete" : ""}`} key={key}>
                  <span>{complete ? <Icon name="check" size={15} /> : itemIndex + 1}</span>
                  <strong>{label.replace("...", "")}</strong>
                </div>
              );
            })}
          </div>
          <div className="processing-note"><Icon name="lock" size={15} /> Do not refresh or close this page.</div>
        </div>
      </section>
    );
  }

  if (step === "review") {
    return (
      <section className="page narrow-page">
        <div className="step-heading">
          <div>
            <span className="section-kicker">Step 4 of 5</span>
            <h1>Review & Confirm Vote</h1>
            <p>Check your selection carefully. A submitted ballot cannot be changed.</p>
          </div>
          <span className="secure-chip"><Icon name="lock" size={15} /> Private review</span>
        </div>

        <div className="review-card">
          <div className="review-card__label">Referendum question</div>
          <h2>{QUESTION}</h2>
          <div className="review-selection">
            <span className={`vote-symbol vote-symbol--${selectedVote}`}>
              <Icon name={selectedVote === "yes" ? "check" : "close"} size={28} />
              {selectedVote === "no" ? "NO" : null}
            </span>
            <div>
              <small>Your selection</small>
              <strong>{selectedOption?.label}</strong>
              <p>{selectedOption?.detail}</p>
            </div>
            <button className="text-button" type="button" onClick={() => setStep("ballot")}>
              Change
            </button>
          </div>

          <div className="privacy-note">
            <Icon name="shield" size={22} />
            <div>
              <strong>Your vote remains private</strong>
              <span>The receipt will contain proof metadata only, not this selection.</span>
            </div>
          </div>

          {error ? <div className="status status--error"><strong>Submission error</strong><span>{error}</span></div> : null}

          <div className="review-actions">
            <button className="button button--outline" type="button" onClick={() => setStep("ballot")}>
              Back to Ballot
            </button>
            <button className="button button--primary" type="button" onClick={handleVote}>
              Generate Proof & Submit Vote
              <Icon name="shield" size={18} />
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="page narrow-page">
      <div className="step-heading">
        <div>
          <span className="section-kicker">Step 3 of 5</span>
          <h1>Referendum Ballot</h1>
          <p>Select one response. Your ballot will not be submitted until you review and confirm it.</p>
        </div>
        <span className="secure-chip"><Icon name="shield" size={15} /> Eligibility confirmed</span>
      </div>

      <div className="ballot-card">
        <div className="ballot-card__top">
          <div>
            <span className="status-badge status-badge--neutral">Binary Referendum · Question 01</span>
            <h2>{QUESTION}</h2>
          </div>
          <span className="ballot-seal"><Icon name="ballot" size={26} /></span>
        </div>

        <div className="options">
          {VOTE_OPTIONS.map((option) => {
            const selected = selectedVote === option.value;
            return (
              <button
                aria-pressed={selected}
                key={option.value}
                type="button"
                className={`option option--${option.value}${selected ? " is-selected" : ""}`}
                onClick={() => {
                  setSelectedVote(option.value);
                  setError("");
                }}
              >
                <span className="option__radio">{selected ? <i /> : null}</span>
                <span className="option__copy">
                  <strong>{option.label}</strong>
                  <small>{option.detail}</small>
                </span>
                <span className="option__mark">
                  {option.value === "yes" ? <Icon name="check" size={25} /> : "NO"}
                </span>
              </button>
            );
          })}
        </div>

        {error ? <div className="status status--error"><span>{error}</span></div> : null}

        <div className="ballot-card__footer">
          <span><Icon name="lock" size={16} /> Selection is not submitted yet</span>
          <button
            type="button"
            className="button button--primary"
            disabled={!selectedOption}
            onClick={() => setStep("review")}
          >
            Review Selection
            <Icon name="arrow" size={18} />
          </button>
        </div>
      </div>
    </section>
  );
}
