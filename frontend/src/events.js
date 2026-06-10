export const ACTIVE_EVENT_ID = "diaspora-referendum-2026";

export const FALLBACK_EVENTS = [
  {
    event_id: ACTIVE_EVENT_ID,
    title: "Diaspora Voting Referendum",
    question: "Should secure diaspora voting be enabled for eligible Nigerians abroad?",
    ballot_type: "Binary referendum",
    status: "Active",
    description: "A prototype referendum on enabling secure voting access for eligible Nigerians abroad.",
    start_date: "June 10, 2026",
    end_date: "June 30, 2026",
    action_enabled: true
  },
  {
    event_id: "overseas-voter-education-poll",
    title: "Overseas Voter Education Poll",
    question: "How should future diaspora voter education materials be delivered?",
    ballot_type: "Demonstration event",
    status: "Upcoming",
    description: "A non-voteable preview event for future voter education and portal guidance.",
    start_date: "July 2026",
    end_date: "To be announced",
    action_enabled: false
  },
  {
    event_id: "secure-ballot-audit-drill",
    title: "Secure Ballot Audit Drill",
    question: "Prototype audit workflow demonstration",
    ballot_type: "Demonstration event",
    status: "Closed",
    description: "A completed demonstration of privacy-preserving ballot receipt auditing.",
    start_date: "May 2026",
    end_date: "Closed May 31, 2026",
    action_enabled: false
  }
];

export function getFallbackEvent(eventId = ACTIVE_EVENT_ID) {
  return FALLBACK_EVENTS.find((event) => event.event_id === eventId) || FALLBACK_EVENTS[0];
}
