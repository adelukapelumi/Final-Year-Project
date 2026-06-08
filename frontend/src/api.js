const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

function buildUrl(path) {
  return `${API_BASE_URL}${path}`;
}

async function request(path, options = {}) {
  try {
    const response = await fetch(buildUrl(path), {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
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

export function submitVote(token, vote) {
  return request("/vote", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify({ vote })
  });
}

export function verifyBallot(ballotId) {
  return request("/verify", {
    method: "POST",
    body: JSON.stringify({ ballot_id: ballotId })
  });
}

export function fetchBoard() {
  return request("/board", { method: "GET" });
}

export function fetchTally() {
  return request("/tally", { method: "GET" });
}
