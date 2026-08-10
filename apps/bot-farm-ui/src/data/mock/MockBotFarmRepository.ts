import type { BotFarmRepository } from "../BotFarmRepository";
import type { BotId } from "../../domain/botFarm";
import { mockFarmSnapshot } from "./mockData";

export class MockBotFarmRepository implements BotFarmRepository {
  async getFarmSnapshot() {
    return Promise.resolve(mockFarmSnapshot);
  }

  async getBot(botId: BotId) {
    return Promise.resolve(mockFarmSnapshot.bots.find((bot) => bot.id === botId));
  }
}
