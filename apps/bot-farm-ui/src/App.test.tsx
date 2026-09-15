import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AppRoutes } from "./App";
import { FarmDataProvider } from "./app/FarmDataContext";
import productGraphSnapshot from "./data/generated/productGraphSnapshot.json";

function renderRoute(route = "/") {
  return render(
    <FarmDataProvider>
      <MemoryRouter initialEntries={[route]}>
        <AppRoutes />
      </MemoryRouter>
    </FarmDataProvider>,
  );
}

describe("Bot Farm UI", () => {
  it("renders the Owner HQ product identity and current development state", async () => {
    renderRoute();

    const productHeading = await screen.findByRole("heading", {
      name: productGraphSnapshot.product.name,
    });
    const ownerHq = productHeading.closest("section");
    const foundation = productGraphSnapshot.development.waves.find((wave) => wave.id === "W0");
    const currentWave = productGraphSnapshot.development.waves.find(
      (wave) => wave.id === productGraphSnapshot.development.current_wave_id,
    );

    expect(ownerHq).not.toBeNull();
    expect(within(ownerHq!).getByText(`${foundation?.id} · ${foundation?.title}`)).toBeInTheDocument();
    expect(within(ownerHq!).getByText(`${currentWave?.id} · ${currentWave?.title}`)).toBeInTheDocument();
    expect(within(ownerHq!).getByText("No Owner decisions required.")).toBeInTheDocument();
    expect(within(ownerHq!).getByText("READ_ONLY")).toBeInTheDocument();
  });

  it("renders every roadmap Wave from the generated projection", async () => {
    renderRoute();

    const roadmapHeading = await screen.findByRole("heading", { name: "Roadmap" });
    const roadmap = roadmapHeading.closest("section");
    expect(roadmap).not.toBeNull();
    expect(within(roadmap!).getAllByRole("listitem")).toHaveLength(
      productGraphSnapshot.development.waves.length,
    );
    for (const wave of productGraphSnapshot.development.waves) {
      expect(within(roadmap!).getByText(wave.title)).toBeInTheDocument();
    }
  });

  it("renders fail-closed authority from the Product Graph projection", async () => {
    renderRoute();

    const authorityHeading = await screen.findByRole("heading", { name: "Authority locks" });
    const authorityBoard = authorityHeading.closest("section");
    expect(authorityBoard).not.toBeNull();
    expect(within(authorityBoard!).getByText("Capital authority · FALSE · LOCKED")).toBeInTheDocument();
    for (const environment of productGraphSnapshot.authority.environments) {
      const card = within(authorityBoard!).getByText(environment.label).closest("article");
      expect(card).not.toBeNull();
      expect(within(card!).getByText("LOCKED")).toBeInTheDocument();
    }
  });

  it("groups six NPC-bots into four expandable farm buildings", async () => {
    renderRoute();

    const mapHeading = await screen.findByRole("heading", {
      name: "Карта зданий и NPC-ботов",
    });
    const map = mapHeading.closest("section");

    expect(map).not.toBeNull();
    expect(within(map!).getAllByRole("link")).toHaveLength(6);
    expect(within(map!).getAllByRole("button", { name: /NPC-ботов/ })).toHaveLength(4);
    expect(within(map!).getByRole("button", { name: /^Крипто-курятник,/ })).toBeInTheDocument();
    expect(within(map!).getByRole("button", { name: /^Амбар MOEX,/ })).toBeInTheDocument();
    expect(screen.getByText("130/130")).toBeInTheDocument();
    expect(screen.getByText("LIVE LOCKED")).toBeInTheDocument();
    expect(screen.getByText("0 BLOCKERS")).toBeInTheDocument();
    expect(screen.getByText("commit ddbc553")).toBeInTheDocument();
    expect(screen.getByText("GitHub Actions 31406129216")).toBeInTheDocument();
    expect(screen.getByText("2026-08-10T15:55:12Z")).toBeInTheDocument();
  });

  it("opens TB-001 from the map and keeps real capital locked", async () => {
    const user = userEvent.setup();
    renderRoute();

    const mapHeading = await screen.findByRole("heading", {
      name: "Карта зданий и NPC-ботов",
    });
    const map = mapHeading.closest("section");
    await user.click(within(map!).getByRole("link", { name: /^TB-001 Telegram BTC,/i }));

    expect(await screen.findByRole("heading", { name: "TB-001 Telegram BTC" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Historical Telegram Replay" })).toBeInTheDocument();
    expect(screen.getByText("REAL CAPITAL · LOCKED")).toBeInTheDocument();
    expect(screen.getByText("130 / 130 PASS")).toBeInTheDocument();
  });

  it("moves the Owner between buildings with arrow keys without side effects", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderRoute();

    const mapHeading = await screen.findByRole("heading", { name: "Карта зданий и NPC-ботов" });
    const map = mapHeading.closest("section");
    expect(map).toHaveAttribute("data-active-building", "crypto-coop");

    const cryptoBuilding = within(map!).getByRole("button", { name: /^Крипто-курятник,/ });
    cryptoBuilding.focus();
    await user.keyboard("{ArrowRight}");

    expect(map).toHaveAttribute("data-active-building", "moex-barn");
    expect(within(map!).getByText("Owner переместился к зданию Амбар MOEX")).toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("supports deep links to the read-only risk center", async () => {
    renderRoute("/risk");

    expect(await screen.findByRole("heading", { name: "Risk Center" })).toBeInTheDocument();
    expect(screen.getByText("REAL CAPITAL")).toBeInTheDocument();
    expect(screen.getAllByText("NOT_EVALUATED").length).toBeGreaterThan(0);
    expect(screen.getAllByText("LOCKED").length).toBeGreaterThan(0);
    expect(screen.getByText("Нет fills и ордеров")).toBeInTheDocument();
  });

  it("navigates between tool pages through the wooden menu", async () => {
    const user = userEvent.setup();
    renderRoute();

    await screen.findByRole("heading", { name: "Карта зданий и NPC-ботов" });
    const main = document.getElementById("main-content");
    expect(main).not.toBeNull();
    main!.scrollTop = 500;
    await user.click(screen.getByRole("link", { name: "Test Lab" }));
    expect(await screen.findByRole("heading", { name: "Test Lab" })).toBeInTheDocument();
    expect(main).toHaveFocus();
    expect(main!.scrollTop).toBe(0);

    await user.click(screen.getByRole("link", { name: "Releases" }));
    expect(await screen.findByRole("heading", { name: "Releases" })).toBeInTheDocument();
  });

  it("routes each bottom-dock item to its named local view", async () => {
    const user = userEvent.setup();
    renderRoute();

    await screen.findByRole("heading", { name: "Карта зданий и NPC-ботов" });
    expect(screen.getByRole("link", { name: "Журнал событий" })).toHaveAttribute("href", "/events");
    expect(screen.getByRole("link", { name: /Уведомления/ })).toHaveAttribute("href", "/notifications");
    expect(screen.getByRole("link", { name: "Архив билдов" })).toHaveAttribute("href", "/builds");

    await user.click(screen.getByRole("link", { name: "Документация" }));
    expect(await screen.findByRole("heading", { name: "Документация" })).toBeInTheDocument();
  });

  it("runs only a local Test Lab animation", async () => {
    const user = userEvent.setup();
    renderRoute("/test-lab");

    const suiteHeading = await screen.findByRole("heading", { name: "Historical Telegram Replay" });
    const suiteCard = suiteHeading.closest("article");
    expect(suiteCard).not.toBeNull();
    const button = within(suiteCard!).getByRole("button", { name: "Запустить demo" });
    await user.click(button);

    expect(screen.getByRole("button", { name: "Анимация прогона…" })).toBeDisabled();
    expect(
      await screen.findByText("Mock-анимация завершена: UI DEMO ONLY. Evidence, subprocess и сеть не затронуты."),
    ).toBeInTheDocument();
  });

  it("keeps Merge, Pilot and Live as separate Owner gates", async () => {
    renderRoute("/releases");

    expect(await screen.findByText("Owner Merge")).toBeInTheDocument();
    expect(screen.getByText("Owner Pilot")).toBeInTheDocument();
    expect(screen.getByText("Owner Live")).toBeInTheDocument();
    expect(screen.getByText("MERGE ≠ PILOT ≠ LIVE")).toBeInTheDocument();
  });
});
