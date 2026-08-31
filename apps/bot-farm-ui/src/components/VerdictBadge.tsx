import type { GateVerdict, ReviewVerdict } from "../domain/botFarm";

type DisplayVerdict = GateVerdict | ReviewVerdict | "READY" | "PLANNED";

const verdictLabels: Record<DisplayVerdict, string> = {
  PASS: "PASS",
  PASS_WITH_FOLLOW_UP: "PASS + FOLLOW-UP",
  PENDING: "PENDING",
  BLOCKED: "BLOCKED",
  LOCKED: "LOCKED",
  DEMO: "DEMO",
  WAITING: "WAITING",
  READY: "READY",
  PLANNED: "PLANNED",
};

export function VerdictBadge({ verdict }: { verdict: DisplayVerdict }) {
  return (
    <span className={`verdict-badge verdict-badge--${verdict.toLowerCase().replaceAll("_", "-")}`}>
      {verdictLabels[verdict]}
    </span>
  );
}
