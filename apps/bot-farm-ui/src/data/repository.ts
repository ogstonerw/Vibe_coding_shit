import type { BotFarmRepository } from "./BotFarmRepository";
import { MockBotFarmRepository } from "./mock/MockBotFarmRepository";

// Composition root: replace only this binding when a read-only API adapter exists.
export const botFarmRepository: BotFarmRepository = new MockBotFarmRepository();
