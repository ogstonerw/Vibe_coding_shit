export const BOT_IDS = [
  "tb-001",
  "tb-002",
  "sandbox",
  "risk-bot",
  "replay-bot",
  "review-bot",
] as const;

export type BotId = (typeof BOT_IDS)[number];
export type BotStage =
  | "DEVELOPMENT"
  | "OFFLINE_SIMULATION"
  | "RESEARCH"
  | "PLANNED"
  | "GUARDING"
  | "REVIEW";
export type GateVerdict = "PASS" | "PENDING" | "BLOCKED" | "LOCKED" | "DEMO";
export type HealthState = "healthy" | "attention" | "training" | "guarded";
export type ReviewVerdict = "PASS" | "PASS_WITH_FOLLOW_UP" | "WAITING";
export type RiskState = "NORMAL" | "WATCH" | "DE_RISK" | "PROTECT" | "EMERGENCY";
export type SpriteKind = "courier" | "merchant" | "trainee" | "guardian" | "mechanic" | "reviewer";
export type EnvironmentKind = "field" | "market" | "training" | "tower" | "mill" | "desk";
export type PlaqueTone = "success" | "pending" | "locked" | "clear";

export interface BotGate {
  id: string;
  label: string;
  verdict: GateVerdict;
  detail?: string;
}

export interface BotReview {
  role: string;
  verdict: ReviewVerdict;
  detail: string;
}

export interface StageStep {
  label: string;
  state: "complete" | "current" | "locked";
}

export interface PipelineStation {
  id: string;
  label: string;
  kind: "export" | "parser" | "risk" | "intent" | "journal";
}

export interface Bot {
  id: BotId;
  name: string;
  shortName: string;
  role: string;
  market: string;
  strategy: string;
  stage: BotStage;
  stageLabel: string;
  status: string;
  statusDetail: string;
  readiness: number;
  health: HealthState;
  sprite: SpriteKind;
  environment: EnvironmentKind;
  gates: readonly BotGate[];
  reviews: readonly BotReview[];
  progression: readonly StageStep[];
  pipeline?: readonly PipelineStation[];
  lastRun: string;
  isDemo: boolean;
}

export interface StatusPlaque {
  id: "tests" | "owner" | "capital" | "findings";
  label: string;
  primary: string;
  secondary: string;
  tone: PlaqueTone;
}

export interface FarmNewsItem {
  id: string;
  message: string;
  age: string;
  tone: "good" | "info" | "waiting";
}

export interface TestSuite {
  id: string;
  name: string;
  status: "PASS" | "READY" | "PLANNED";
  lastRun: string;
  detail: string;
  demoRunnable: boolean;
}

export interface ReviewAgent {
  id: string;
  name: string;
  sprite: SpriteKind;
  verdict: ReviewVerdict;
  detail: string;
}

export interface ReleaseRecord {
  botId: BotId;
  slice: string;
  stage: string;
  offline: GateVerdict;
  ownerGate: GateVerdict;
  paper: GateVerdict;
  live: GateVerdict;
}

export interface QualitySnapshot {
  passedTests: number;
  totalTests: number;
  unresolvedBlockers: number;
  unresolvedHigh: number;
  mediumFollowUps: number;
  environment: "OFFLINE";
  sourceLabel: string;
}

export interface RiskSnapshot {
  current: RiskState;
  ladder: readonly RiskState[];
  capitalState: "LOCKED";
  note: string;
}

export interface FarmSnapshot {
  farmName: string;
  subtitle: string;
  plaques: readonly StatusPlaque[];
  bots: readonly Bot[];
  news: readonly FarmNewsItem[];
  farmDay: number;
  weather: string;
  testSuites: readonly TestSuite[];
  reviewAgents: readonly ReviewAgent[];
  quality: QualitySnapshot;
  release: ReleaseRecord;
  risk: RiskSnapshot;
}
