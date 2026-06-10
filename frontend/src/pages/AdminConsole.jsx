import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import {
  createAdminVoter,
  deactivateAdminVoter,
  deleteAdminVoter,
  fetchAdminVoters,
  getAdminConfirmationText,
  resetAdminDemoData,
  resetAdminEvent,
  resetAdminVoter,
  validateAdminToken
} from "../api";

const ADMIN_SESSION_KEY = "prototype-registry-admin-token";
const DEMO_CONFIRMATION_TEXT = getAdminConfirmationText();

const EMPTY_FORM = {
  nin: "",
  displayName: "",
  diasporaLocation: "",
  voterCategory: "Eligible Diaspora Voter"
};

function readStoredAdminToken() {
  return window.sessionStorage.getItem(ADMIN_SESSION_KEY) || "";
}

function statusLabel(value, activeLabel, inactiveLabel = "Not yet") {
  return value ? activeLabel : inactiveLabel;
}

export default function AdminConsole() {
  const [tokenInput, setTokenInput] = useState("");
  const [adminToken, setAdminToken] = useState(() => readStoredAdminToken());
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [authError, setAuthError] = useState("");
  const [adminMeta, setAdminMeta] = useState(null);
  const [overview, setOverview] = useState(null);
  const [voters, setVoters] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState({ tone: "", message: "" });
  const [actionKey, setActionKey] = useState("");
  const [form, setForm] = useState(EMPTY_FORM);
  const [confirmationText, setConfirmationText] = useState("");

  useEffect(() => {
    if (!adminToken) {
      return;
    }

    let active = true;
    setIsAuthenticating(true);
    validateAdminToken(adminToken)
      .then((payload) => {
        if (!active) {
          return;
        }
        setAdminMeta(payload.admin);
        setAuthError("");
      })
      .catch((error) => {
        if (!active) {
          return;
        }
        setAdminToken("");
        setAdminMeta(null);
        setOverview(null);
        setVoters([]);
        window.sessionStorage.removeItem(ADMIN_SESSION_KEY);
        setAuthError(error.message || "Admin validation failed.");
      })
      .finally(() => {
        if (active) {
          setIsAuthenticating(false);
        }
      });

    return () => {
      active = false;
    };
  }, [adminToken]);

  useEffect(() => {
    if (!adminToken || !adminMeta) {
      return;
    }

    let active = true;
    setIsLoading(true);
    fetchAdminVoters(adminToken)
      .then((payload) => {
        if (!active) {
          return;
        }
        setOverview(payload.overview || null);
        setVoters(payload.voters || []);
        setStatus((currentStatus) =>
          currentStatus.message ? currentStatus : { tone: "", message: "" }
        );
      })
      .catch((error) => {
        if (active) {
          setStatus({
            tone: "error",
            message: error.message || "Unable to load registry data."
          });
        }
      })
      .finally(() => {
        if (active) {
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [adminMeta, adminToken]);

  async function refreshConsole(message = "", tone = "success") {
    if (!adminToken) {
      return;
    }

    setIsLoading(true);
    try {
      const payload = await fetchAdminVoters(adminToken);
      setOverview(payload.overview || null);
      setVoters(payload.voters || []);
      if (message) {
        setStatus({ tone, message });
      }
    } catch (error) {
      setStatus({
        tone: "error",
        message: error.message || "Unable to refresh registry data."
      });
    } finally {
      setIsLoading(false);
    }
  }

  async function handleAuthenticate(event) {
    event.preventDefault();
    setIsAuthenticating(true);
    setAuthError("");

    try {
      const payload = await validateAdminToken(tokenInput.trim());
      window.sessionStorage.setItem(ADMIN_SESSION_KEY, tokenInput.trim());
      setAdminToken(tokenInput.trim());
      setAdminMeta(payload.admin);
      setStatus({ tone: "success", message: "Admin token accepted for this browser session." });
    } catch (error) {
      setAuthError(error.message || "Admin validation failed.");
    } finally {
      setIsAuthenticating(false);
    }
  }

  function handleEndAdminSession() {
    window.sessionStorage.removeItem(ADMIN_SESSION_KEY);
    setAdminToken("");
    setTokenInput("");
    setAdminMeta(null);
    setOverview(null);
    setVoters([]);
    setConfirmationText("");
    setStatus({ tone: "", message: "" });
  }

  async function handleCreateVoter(event) {
    event.preventDefault();
    setActionKey("create");
    try {
      await createAdminVoter(adminToken, {
        nin: form.nin,
        display_name: form.displayName,
        diaspora_location: form.diasporaLocation,
        voter_category: form.voterCategory,
        mock_biometric_enabled: true
      });
      setForm(EMPTY_FORM);
      await refreshConsole("Mock eligible voter created.");
    } catch (error) {
      setStatus({ tone: "error", message: error.message || "Mock voter creation failed." });
    } finally {
      setActionKey("");
    }
  }

  async function runRowAction(key, action, successMessage) {
    setActionKey(key);
    try {
      await action();
      await refreshConsole(successMessage);
    } catch (error) {
      setStatus({ tone: "error", message: error.message || "Registry action failed." });
    } finally {
      setActionKey("");
    }
  }

  if (!adminToken || !adminMeta) {
    return (
      <section className="page admin-page">
        <div className="admin-login-shell">
          <div className="admin-login-hero">
            <span className="section-kicker section-kicker--light">Prototype-only access</span>
            <h1>Prototype Registry Admin</h1>
            <p>
              Manage mock eligible voters and reset demo state without editing JSON files or
              touching persistent storage directly.
            </p>
            <div className="admin-login-points">
              <div>
                <Icon name="shield" size={18} />
                <span>Token stays in `sessionStorage` for this admin browser session only.</span>
              </div>
              <div>
                <Icon name="lock" size={18} />
                <span>No raw votes, decrypted votes, NIN hashes, or full NIN values are shown here.</span>
              </div>
              <div>
                <Icon name="board" size={18} />
                <span>This console is for prototype registry management, not a full election dashboard.</span>
              </div>
            </div>
          </div>

          <form className="admin-login-card" onSubmit={handleAuthenticate}>
            <span className="section-kicker">Admin access</span>
            <h2>Enter the prototype admin token</h2>
            <p>Set `EVOTING_ADMIN_TOKEN` in deployment, then use that token here.</p>

            <label className="field">
              <span>Admin token</span>
              <div className="input-wrap">
                <Icon name="lock" size={18} />
                <input
                  autoComplete="off"
                  placeholder="Paste EVOTING_ADMIN_TOKEN"
                  type="password"
                  value={tokenInput}
                  onChange={(event) => setTokenInput(event.target.value)}
                />
              </div>
            </label>

            {authError ? (
              <div className="status status--error">
                <div>
                  <strong>Admin authentication failed</strong>
                  <span>{authError}</span>
                </div>
              </div>
            ) : null}

            <button
              className="button button--primary button--wide"
              disabled={isAuthenticating || !tokenInput.trim()}
              type="submit"
            >
              {isAuthenticating ? "Validating token..." : "Open Registry Console"}
              {isAuthenticating ? <span className="spinner spinner--small" /> : <Icon name="arrow" size={18} />}
            </button>
          </form>
        </div>
      </section>
    );
  }

  return (
    <section className="page admin-page">
      <div className="admin-console-head">
        <div>
          <span className="section-kicker">Prototype registry management</span>
          <h1>{adminMeta.label}</h1>
          <p>Use this console to manage mock eligible voters and reset demo-only accreditation data.</p>
        </div>
        <div className="admin-console-head__actions">
          <span className="secure-chip">
            <Icon name="shield" size={14} />
            Prototype-only console
          </span>
          <button className="button button--outline button--small" onClick={() => refreshConsole()} type="button">
            <Icon name="refresh" size={15} />
            Refresh
          </button>
          <button className="button button--outline button--small" onClick={handleEndAdminSession} type="button">
            <Icon name="logout" size={15} />
            End Admin Session
          </button>
        </div>
      </div>

      {status.message ? (
        <div className={`status ${status.tone === "error" ? "status--error" : "status--success"}`}>
          <div>
            <strong>{status.tone === "error" ? "Admin action failed" : "Admin action complete"}</strong>
            <span>{status.message}</span>
          </div>
        </div>
      ) : null}

      <div className="admin-stat-grid">
        <article>
          <small>Total mock voters</small>
          <strong>{overview?.total_mock_voters ?? "-"}</strong>
        </article>
        <article>
          <small>Active mock voters</small>
          <strong>{overview?.active_mock_voters ?? "-"}</strong>
        </article>
        <article>
          <small>Ballots cast</small>
          <strong>{overview?.ballots_cast ?? "-"}</strong>
        </article>
        <article>
          <small>Active event</small>
          <strong>{overview?.active_event?.title || "-"}</strong>
        </article>
      </div>

      <div className="admin-grid">
        <article className="admin-card">
          <div className="admin-card__head">
            <div>
              <span className="section-kicker">Create mock voter</span>
              <h2>Mock Eligible Voter Registry Console</h2>
            </div>
          </div>
          <form className="admin-form" onSubmit={handleCreateVoter}>
            <label className="field">
              <span>Mock NIN</span>
              <div className="input-wrap">
                <Icon name="user" size={18} />
                <input
                  inputMode="numeric"
                  maxLength={11}
                  placeholder="11-digit mock NIN"
                  value={form.nin}
                  onChange={(event) =>
                    setForm((currentForm) => ({
                      ...currentForm,
                      nin: event.target.value.replace(/\D/g, "")
                    }))
                  }
                />
              </div>
            </label>
            <label className="field">
              <span>Display name</span>
              <div className="input-wrap">
                <Icon name="user" size={18} />
                <input
                  placeholder="Example: Ifeoma Nwosu"
                  value={form.displayName}
                  onChange={(event) =>
                    setForm((currentForm) => ({ ...currentForm, displayName: event.target.value }))
                  }
                />
              </div>
            </label>
            <label className="field">
              <span>Diaspora location</span>
              <div className="input-wrap">
                <Icon name="map" size={18} />
                <input
                  placeholder="Example: Dublin, Ireland"
                  value={form.diasporaLocation}
                  onChange={(event) =>
                    setForm((currentForm) => ({
                      ...currentForm,
                      diasporaLocation: event.target.value
                    }))
                  }
                />
              </div>
            </label>
            <label className="field">
              <span>Voter category</span>
              <div className="input-wrap">
                <Icon name="shield" size={18} />
                <input
                  value={form.voterCategory}
                  onChange={(event) =>
                    setForm((currentForm) => ({
                      ...currentForm,
                      voterCategory: event.target.value
                    }))
                  }
                />
              </div>
            </label>
            <p className="admin-note">
              Only a masked NIN and last four digits are retained for display after creation.
            </p>
            <button
              className="button button--primary"
              disabled={actionKey === "create" || form.nin.length !== 11 || !form.displayName.trim() || !form.diasporaLocation.trim()}
              type="submit"
            >
              {actionKey === "create" ? "Creating..." : "Create Mock Voter"}
              {actionKey === "create" ? <span className="spinner spinner--small" /> : <Icon name="arrow" size={18} />}
            </button>
          </form>
        </article>

        <article className="admin-card admin-card--danger">
          <div className="admin-card__head">
            <div>
              <span className="section-kicker">Reset tools</span>
              <h2>Prototype demo controls</h2>
            </div>
          </div>

          <div className="admin-danger-block">
            <strong>Reset active event ballots</strong>
            <p>
              Clears ballots and proof artifacts for {overview?.active_event?.title || "the active event"} while
              keeping the mock registry intact.
            </p>
            <button
              className="button button--outline"
              disabled={actionKey === "reset-event"}
              onClick={() =>
                runRowAction(
                  "reset-event",
                  () => resetAdminEvent(adminToken, overview?.active_event?.event_id),
                  "Active event ballots and proofs were reset."
                )
              }
              type="button"
            >
              <Icon name="refresh" size={16} />
              {actionKey === "reset-event" ? "Resetting..." : "Reset Event Ballots"}
            </button>
          </div>

          <div className="admin-danger-block admin-danger-block--deep">
            <strong>Reset all demo data</strong>
            <p>
              Clears ballots, proof artifacts, proof inputs, session state, biometric verification, and `has voted`
              flags, but keeps the mock voter registry.
            </p>
            <label className="field">
              <span>Type {DEMO_CONFIRMATION_TEXT}</span>
              <div className="input-wrap">
                <Icon name="lock" size={18} />
                <input
                  placeholder={DEMO_CONFIRMATION_TEXT}
                  value={confirmationText}
                  onChange={(event) => setConfirmationText(event.target.value)}
                />
              </div>
            </label>
            <button
              className="button button--primary admin-danger-button"
              disabled={actionKey === "reset-demo" || confirmationText !== DEMO_CONFIRMATION_TEXT}
              onClick={() =>
                runRowAction(
                  "reset-demo",
                  () => resetAdminDemoData(adminToken),
                  "Demo ballots, proofs, sessions, and biometric state were cleared."
                )
              }
              type="button"
            >
              <Icon name="close" size={16} />
              {actionKey === "reset-demo" ? "Resetting demo data..." : "Reset Demo Data"}
            </button>
          </div>
        </article>
      </div>

      <article className="admin-card">
        <div className="admin-card__head">
          <div>
            <span className="section-kicker">Registry list</span>
            <h2>Mock eligible voters</h2>
          </div>
          <span>{isLoading ? "Refreshing registry..." : `${voters.length} voter record${voters.length === 1 ? "" : "s"}`}</span>
        </div>

        <div className="admin-table-wrap">
          <div className="admin-table">
            <div className="admin-table__head">
              <span>Display name</span>
              <span>Masked NIN</span>
              <span>Diaspora location</span>
              <span>Voter category</span>
              <span>Status</span>
              <span>Has voted</span>
              <span>Biometric verified</span>
              <span>Actions</span>
            </div>
            {voters.map((voter) => (
              <div className="admin-table__row" key={voter.id}>
                <div data-label="Display name">
                  <strong>{voter.display_name}</strong>
                </div>
                <div data-label="Masked NIN">
                  <code>{voter.masked_nin}</code>
                </div>
                <div data-label="Diaspora location">{voter.diaspora_location}</div>
                <div data-label="Voter category">{voter.voter_category}</div>
                <div data-label="Status">
                  <span className={`status-badge ${voter.is_active ? "status-badge--success" : "status-badge--error"}`}>
                    {voter.is_active ? "Active" : "Inactive"}
                  </span>
                </div>
                <div data-label="Has voted">{statusLabel(voter.has_voted, "Yes", "No")}</div>
                <div data-label="Biometric verified">{statusLabel(voter.biometric_verified, "Verified", "No")}</div>
                <div className="admin-table__actions" data-label="Actions">
                  <button
                    className="button button--outline button--small"
                    disabled={Boolean(actionKey)}
                    onClick={() =>
                      runRowAction(
                        `reset-${voter.id}`,
                        () => resetAdminVoter(adminToken, voter.id),
                        `${voter.display_name} was reset.`
                      )
                    }
                    type="button"
                  >
                    <Icon name="refresh" size={14} />
                    Reset
                  </button>
                  <button
                    className="button button--outline button--small"
                    disabled={Boolean(actionKey) || !voter.is_active}
                    onClick={() => {
                      if (!window.confirm(`Deactivate ${voter.display_name}?`)) {
                        return;
                      }
                      runRowAction(
                        `deactivate-${voter.id}`,
                        () => deactivateAdminVoter(adminToken, voter.id),
                        `${voter.display_name} was deactivated.`
                      );
                    }}
                    type="button"
                  >
                    <Icon name="shield" size={14} />
                    Deactivate
                  </button>
                  <button
                    className="button button--outline button--small"
                    disabled={Boolean(actionKey)}
                    onClick={() => {
                      if (!window.confirm(`Delete ${voter.display_name} and clear stored demo state?`)) {
                        return;
                      }
                      runRowAction(
                        `delete-${voter.id}`,
                        () => deleteAdminVoter(adminToken, voter.id),
                        `${voter.display_name} was deleted from the mock registry.`
                      );
                    }}
                    type="button"
                  >
                    <Icon name="close" size={14} />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
          {!isLoading && voters.length === 0 ? (
            <div className="empty-state empty-state--compact">
              <span className="icon-tile">
                <Icon name="user" />
              </span>
              <h2>No mock voters configured</h2>
              <p>Create a registry record above to enable prototype accreditation without redeploying.</p>
            </div>
          ) : null}
        </div>
      </article>
    </section>
  );
}
