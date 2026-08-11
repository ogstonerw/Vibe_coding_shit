import { describe, expect, it } from "vitest";
import { BOT_IDS, FARM_BUILDING_IDS, type BotId } from "../../domain/botFarm";
import { mockFarmSnapshot } from "./mockData";

describe("mock farm contract", () => {
  it("puts every NPC-bot into one expandable farm building", () => {
    expect(mockFarmSnapshot.bots.map((bot) => bot.id)).toEqual(BOT_IDS);
    expect(new Set(mockFarmSnapshot.bots.map((bot) => bot.sprite)).size).toBe(6);
    expect(mockFarmSnapshot.buildings.map((building) => building.id)).toEqual(FARM_BUILDING_IDS);
    expect(mockFarmSnapshot.buildings.flatMap((building) => building.botIds).sort()).toEqual([...BOT_IDS].sort());
    expect(mockFarmSnapshot.buildings.find((building) => building.id === "crypto-coop")?.botIds).toHaveLength(3);
    expect(
      mockFarmSnapshot.bots.every((bot) =>
        mockFarmSnapshot.buildings.some(
          (building) =>
            building.id === bot.buildingId &&
            (building.botIds as readonly BotId[]).includes(bot.id),
        ),
      ),
    ).toBe(true);
    expect(
      mockFarmSnapshot.buildings.every((building) => building.botIds.length <= building.capacity),
    ).toBe(true);
    expect(mockFarmSnapshot.bots.every((bot) => !("readiness" in bot))).toBe(true);
  });

  it("states the current TB-001 gates without implying trading access", () => {
    const primaryBot = mockFarmSnapshot.bots.find((bot) => bot.id === "tb-001");

    expect(primaryBot?.lastRun).toContain("130/130 PASS");
    expect(primaryBot?.gates.find((gate) => gate.id === "owner-merge")?.verdict).toBe("PENDING");
    expect(primaryBot?.gates.find((gate) => gate.id === "owner-pilot")?.verdict).toBe("BLOCKED");
    expect(primaryBot?.gates.find((gate) => gate.id === "owner-live")?.verdict).toBe("LOCKED");
    expect(mockFarmSnapshot.risk.capitalState).toBe("LOCKED");
    expect(mockFarmSnapshot.risk.current).toBe("NOT_EVALUATED");
    expect(mockFarmSnapshot.release).toMatchObject({
      ownerMerge: "PENDING",
      ownerPilot: "BLOCKED",
      ownerLive: "LOCKED",
    });
    expect(mockFarmSnapshot.quality).toMatchObject({
      passedTests: 130,
      totalTests: 130,
      unresolvedBlockers: 0,
      unresolvedHigh: 0,
    });
  });
});
