// Which group each skill shows under on the home page. The build fails when this
// list and the folders in skills/ disagree.
export type Group = { title: string; intro: string; start: string; skills: string[] };

export const GROUPS: Group[] = [
  {
    title: "Getting started",
    intro: "Run once in each repository, and learn the workflow.",
    start: "setup-workflow",
    skills: ["setup-workflow", "teach"],
  },
  {
    title: "The main flow",
    intro: "From an idea to a merged change, in order.",
    start: "grill-with-docs",
    skills: [
      "grill-with-docs",
      "to-spec",
      "to-tickets",
      "implement-spec",
      "implement",
      "review-change",
      "retro",
      "grade-run",
    ],
  },
  {
    title: "Shaping",
    intro: "Settle an open question before it reaches the flow.",
    start: "grill-me",
    skills: ["grill-me", "prototype", "research"],
  },
  {
    title: "Engineering",
    intro: "Keep the codebase and the issue list healthy.",
    start: "improve-codebase-architecture",
    skills: ["improve-codebase-architecture", "comment-report", "diagnosing-bugs", "triage", "handoff"],
  },
  {
    title: "Reference",
    intro: "The shared layer other skills load or cite.",
    start: "grilling",
    skills: [
      "grilling",
      "domain-modeling",
      "codebase-design",
      "knowledge-map",
      "tdd",
      "writing-for-agents",
      "diagram",
      "ast",
    ],
  },
  {
    title: "Your record",
    intro: "See what you have done and how it holds up, from evidence.",
    start: "track-record",
    skills: ["track-record"],
  },
];
