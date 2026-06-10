export function hasVoteableSelectedEvent(session) {
  const event = session?.selectedEvent;
  return Boolean(
    session?.token &&
      session?.biometricVerified &&
      event?.event_id &&
      event?.status === "Active" &&
      event?.action_enabled
  );
}
