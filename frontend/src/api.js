const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const VALID_VOTES = new Set(["yes", "no"]);
const ADMIN_CONFIRMATION_TEXT = "RESET DEMO DATA";

function buildUrl(path) {
  return `${API_BASE_URL}${path}`;
}

function normalizeVote(vote) {
  if (typeof vote !== "string") {
    return "";
  }

  const normalizedVote = vote.toLowerCase();
  return VALID_VOTES.has(normalizedVote) ? normalizedVote : "";
}

async function request(path, options = {}) {
  try {
    const response = await fetch(buildUrl(path), {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      }
    });

    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : null;

    if (!response.ok) {
      throw {
        status: response.status,
        message: payload?.error || "Request failed."
      };
    }

    return payload;
  } catch (error) {
    if (error?.message === "Failed to fetch") {
      throw {
        status: 0,
        message:
          "Backend unavailable. Start the Flask API from the backend folder with `python app.py`, then reload the frontend."
      };
    }

    throw error?.message ? error : { status: 0, message: "Unexpected frontend error." };
  }
}

export function authenticate(nin, mode) {
  return request(`/${mode}`, {
    method: "POST",
    body: JSON.stringify({ nin })
  });
}

export function verifyCameraCapture(token, detectionMode) {
  return request("/biometric-verify", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({
      camera_capture: true,
      detection_mode: detectionMode
    })
  });
}

export function fetchEvents() {
  return request("/events", { method: "GET" });
}

export function submitVote(token, eventId, vote) {
  const normalizedVote = normalizeVote(vote);

  if (!normalizedVote) {
    throw {
      status: 0,
      message: "Select a valid Yes or No vote before submitting."
    };
  }

  return request("/vote", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ event_id: eventId, vote: normalizedVote })
  });
}

export function verifyBallot(ballotId, eventId) {
  return request("/verify", {
    method: "POST",
    body: JSON.stringify({ ballot_id: ballotId, event_id: eventId })
  });
}

export function fetchBoard(eventId) {
  const query = eventId ? `?event_id=${encodeURIComponent(eventId)}` : "";
  return request(`/board${query}`, { method: "GET" });
}

export function fetchTally(eventId) {
  const query = eventId ? `?event_id=${encodeURIComponent(eventId)}` : "";
  return request(`/tally${query}`, { method: "GET" });
}

function adminRequest(path, token, options = {}) {
  return request(path, {
    ...options,
    headers: {
      "X-Admin-Token": token,
      ...(options.headers || {})
    }
  });
}

export function getAdminConfirmationText() {
  return ADMIN_CONFIRMATION_TEXT;
}

export function validateAdminToken(token) {
  return adminRequest("/admin/me", token, { method: "GET" });
}

export function fetchAdminVoters(token) {
  return adminRequest("/admin/voters", token, { method: "GET" });
}

export function createAdminVoter(token, payload) {
  return adminRequest("/admin/voters", token, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export function resetAdminVoter(token, voterId, eventId = "") {
  return adminRequest(`/admin/voters/${voterId}/reset`, token, {
    method: "POST",
    body: JSON.stringify(eventId ? { event_id: eventId } : {})
  });
}

export function deactivateAdminVoter(token, voterId) {
  return adminRequest(`/admin/voters/${voterId}/deactivate`, token, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function deleteAdminVoter(token, voterId) {
  return adminRequest(`/admin/voters/${voterId}`, token, {
    method: "DELETE"
  });
}

export function resetAdminEvent(token, eventId) {
  return adminRequest(`/admin/events/${encodeURIComponent(eventId)}/reset`, token, {
    method: "POST",
    body: JSON.stringify({})
  });
}

export function resetAdminDemoData(token, clearRegistry = false) {
  return adminRequest("/admin/reset-demo-data", token, {
    method: "POST",
    body: JSON.stringify({
      confirmation_text: ADMIN_CONFIRMATION_TEXT,
      clear_registry: clearRegistry
    })
  });
}
