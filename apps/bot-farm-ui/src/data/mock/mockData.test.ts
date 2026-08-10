import { describe, expect, it } from "vitest";
import { BOT_IDS } from "../../domain/botFarm";
import { mockFarmSnapshot } from "./mockData";

describe("mock farm contract", () => {
  it("contains one typed entity for every farm zone", () => {
    expect(mockFarmSnapshot.bots.map((bot) => bot.id)).toEqual(BOT_IDS);
    expect(new Set(mockFarmSnapshot.bots.map((bot) => bot.sprite)).size).toBe(6);
    expect(new Set(mockFarmSnapshot.bots.map((bot) => bot.environment)).size).toBe(6);
  });

  it("states the current TB-001 gates without implying trading access", () => {
    const primaryBot = mockFarmSnapshot.bots.find((bot) => bot.id === "tb-001");

    expect(primaryBot?.lastRun).toContain("130/130 PASS");
    expect(primaryBot?.gates.find((gate) => gate.id === "owner")?.verdict).toBe("PENDING");
    expect(primaryBot?.gates.find((gate) => gate.id === "paper")?.verdict).toBe("BLOCKED");
    expect(primaryBot?.gates.find((gate) => gate.id === "live")?.verdict).toBe("BLOCKED");
    expect(mockFarmSnapshot.risk.capitalState).toBe("LOCKED");
    expect(mockFarmSnapshot.quality).toMatchObject({
      passedTests: 130,
      totalTests: 130,
      unresolvedBlockers: 0,
      unresolvedHigh: 0,
    });
  });
});
