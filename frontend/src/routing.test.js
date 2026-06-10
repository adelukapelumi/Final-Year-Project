import test from "node:test";
import assert from "node:assert/strict";
import { hasVoteableSelectedEvent } from "./routing.js";

test("direct ballot access is blocked without a selected event", () => {
  assert.equal(
    hasVoteableSelectedEvent({
      token: "session",
      biometricVerified: true
    }),
    false
  );
});

test("ballot access requires the selected event to be active and voteable", () => {
  assert.equal(
    hasVoteableSelectedEvent({
      token: "session",
      biometricVerified: true,
      selectedEvent: {
        event_id: "diaspora-referendum-2026",
        status: "Active",
        action_enabled: true
      }
    }),
    true
  );
  assert.equal(
    hasVoteableSelectedEvent({
      token: "session",
      biometricVerified: true,
      selectedEvent: {
        event_id: "overseas-voter-education-poll",
        status: "Upcoming",
        action_enabled: false
      }
    }),
    false
  );
});
