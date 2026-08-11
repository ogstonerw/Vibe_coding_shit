import type { Bot, BotId, FarmSnapshot } from "../domain/botFarm";

export interface BotFarmRepository {
  getFarmSnapshot(): Promise<FarmSnapshot>;
  getBot(botId: BotId): Promise<Bot | undefined>;
}
