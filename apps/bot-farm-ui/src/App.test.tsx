import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppRoutes } from "./App";
import { FarmDataProvider } from "./app/FarmDataContext";

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
  it("shows six distinct bot zones and the truthful release plaques", async () => {
    renderRoute();

    const mapHeading = await screen.findByRole("heading", {
      name: "Карта фермы торговых ботов",
    });
    const map = mapHeading.closest("section");

    expect(map).not.toBeNull();
    expect(within(map!).getAllByRole("link")).toHaveLength(6);
    expect(screen.getByText("130/130")).toBeInTheDocument();
    expect(screen.getByText("LIVE LOCKED")).toBeInTheDocument();
    expect(screen.getByText("0 BLOCKERS")).toBeInTheDocument();
  });

  it("opens TB-001 from the map and keeps real capital locked", async () => {
    const user = userEvent.setup();
    renderRoute();

    const mapHeading = await screen.findByRole("heading", {
      name: "Карта фермы торговых ботов",
    });
    const map = mapHeading.closest("section");
    await user.click(within(map!).getByRole("link", { name: /Открыть TB-001 Telegram BTC/i }));

    expect(await screen.findByRole("heading", { name: "TB-001 Telegram BTC" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Historical Telegram Replay" })).toBeInTheDocument();
    expect(screen.getByText("REAL CAPITAL · LOCKED")).toBeInTheDocument();
    expect(screen.getByText("130 / 130 PASS")).toBeInTheDocument();
  });

  it("supports deep links to the read-only risk center", async () => {
    renderRoute("/risk");

    expect(await screen.findByRole("heading", { name: "Risk Center" })).toBeInTheDocument();
    expect(screen.getByText("REAL CAPITAL")).toBeInTheDocument();
    expect(screen.getAllByText("LOCKED").length).toBeGreaterThan(0);
    expect(screen.getByText("Нет fills и ордеров")).toBeInTheDocument();
  });

  it("navigates between tool pages through the wooden menu", async () => {
    const user = userEvent.setup();
    renderRoute();

    await screen.findByRole("heading", { name: "Карта фермы торговых ботов" });
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

    await screen.findByRole("heading", { name: "Карта фермы торговых ботов" });
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
      await screen.findByText("Mock-анимация завершена: PASS. Команды, subprocess и сеть не вызывались."),
    ).toBeInTheDocument();
  });
});
