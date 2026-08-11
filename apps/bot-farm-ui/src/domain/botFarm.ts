export const BOT_IDS = [
  "tb-001",
  "tb-002",
  "sandbox",
  "risk-bot",
  "replay-bot",
  "review-bot",
] as const;

export type BotId = (typeof BOT_IDS)[number];
export const FARM_BUILDING_IDS = [
  "crypto-coop",
  "moex-barn",
  "safety-tower",
  "review-workshop",
] as const;

export type FarmBuildingId = (typeof FARM_BUILDING_IDS)[number];
export type FarmDirection = "left" | "right" | "up" | "down";
export type FarmBuildingKind = "coop" | "barn" | "tower" | "workshop";
export type AgentKind = "trading" | "research" | "service" | "review";
export type BotStage =
  | "DEVELOPMENT"
  | "OFFLINE_SIMULATION"
  | "RESEARCH"
  | "PLANNED"
  | "GUARDING"
  | "REVIEW";
export type GateVerdict = "PASS" | "PENDING" | "BLOCKED" | "LOCKED" | "DEMO";
export type EvidenceTone = "verified" | "attention" | "demo" | "guarded";
export type ReviewVerdict = "PASS" | "PASS_WITH_FOLLOW_UP" | "WAITING";
export type RiskState = "NOT_EVALUATED" | "NORMAL" | "WATCH" | "DE_RISK" | "PROTECT" | "EMERGENCY";
export type SpriteKind = "courier" | "merchant" | "trainee" | "guardian" | "mechanic" | "reviewer" | "owner";
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
  evidenceLabel: string;
  evidenceTone: EvidenceTone;
  agentKind: AgentKind;
  buildingId: FarmBuildingId;
  sprite: SpriteKind;
  gates: readonly BotGate[];
  reviews: readonly BotReview[];
  progression: readonly StageStep[];
  pipeline?: readonly PipelineStation[];
  lastRun: string;
  isDemo: boolean;
}

export interface FarmBuilding {
  id: FarmBuildingId;
  name: string;
  shortName: string;
  kind: FarmBuildingKind;
  botIds: readonly BotId[];
  capacity: number;
  status: string;
  statusDetail: string;
}

export interface FarmConnection {
  from: FarmBuildingId;
  to: FarmBuildingId;
  direction: FarmDirection;
}

export interface FarmNavigation {
  initialBuildingId: FarmBuildingId;
  connections: readonly FarmConnection[];
}

export interface OperatorContext {
  displayName: string;
  roleLabel: "Owner";
  mode: "SOLO_OWNER";
  authorizationBoundary: "SERVER_REQUIRED";
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
  ownerMerge: GateVerdict;
  ownerPilot: GateVerdict;
  ownerLive: GateVerdict;
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
  sourceCommit: string;
  sourceRun: string;
  capturedAt: string;
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
  operator: OperatorContext;
  plaques: readonly StatusPlaque[];
  buildings: readonly FarmBuilding[];
  navigation: FarmNavigation;
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
