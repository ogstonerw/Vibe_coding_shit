import { useEffect, useRef, useState } from "react";
import { useFarmData } from "../app/FarmDataContext";
import { VerdictBadge } from "../components/VerdictBadge";

type DemoRunState = { suiteId: string; status: "RUNNING" | "PASS" } | null;

export function TestLabPage() {
  const { snapshot } = useFarmData();
  const [demoRun, setDemoRun] = useState<DemoRunState>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => () => window.clearTimeout(timer.current), []);
  if (!snapshot) return null;

  function runDemo(suiteId: string) {
    window.clearTimeout(timer.current);
    setDemoRun({ suiteId, status: "RUNNING" });
    timer.current = window.setTimeout(() => setDemoRun({ suiteId, status: "PASS" }), 900);
  }

  return (
    <div className="content-page">
      <header className="page-banner page-banner--lab"><span className="banner-art" aria-hidden="true">⚗</span><div><span className="eyebrow">Локальная лаборатория</span><h1>Test Lab</h1><p>Витрина проверок и безопасных mock-прогонов. Реальные тестовые процессы отсюда не запускаются.</p></div><strong>{snapshot.quality.environment}</strong></header>
      <div className="truth-strip"><span className="truth-strip__light" aria-hidden="true" /><strong>Зафиксированный результат ядра: {snapshot.quality.passedTests} / {snapshot.quality.totalTests} {snapshot.release.offline}</strong><span>{snapshot.quality.sourceLabel}</span></div>

      <section className="suite-grid" aria-labelledby="suite-title">
        <h2 className="sr-only" id="suite-title">Наборы тестов</h2>
        {snapshot.testSuites.map((suite) => {
          const activeState = demoRun?.suiteId === suite.id ? demoRun.status : null;
          return (
            <article className="suite-card" key={suite.id}>
              <div className="suite-card__top"><span className="suite-flask" aria-hidden="true"><i /></span><VerdictBadge verdict={activeState === "PASS" ? "PASS" : suite.status === "READY" ? "DEMO" : suite.status} /></div>
              <h2>{suite.name}</h2><p>{suite.detail}</p>
              <dl><div><dt>Последний результат</dt><dd>{suite.lastRun}</dd></div><div><dt>Контур</dt><dd>{suite.demoRunnable ? "LOCAL MOCK" : "NOT IMPLEMENTED"}</dd></div></dl>
              <button className="pixel-button" type="button" disabled={!suite.demoRunnable || activeState === "RUNNING"} onClick={() => runDemo(suite.id)}>
                {activeState === "RUNNING" ? "Анимация прогона…" : activeState === "PASS" ? "Demo PASS · повторить" : suite.demoRunnable ? "Запустить demo" : "Заблокировано"}
              </button>
              {activeState === "RUNNING" && <span className="lab-progress" aria-label="Mock-прогон выполняется"><i /></span>}
            </article>
          );
        })}
      </section>
      <p className="demo-footnote" aria-live="polite">{demoRun?.status === "PASS" ? "Mock-анимация завершена: PASS. Команды, subprocess и сеть не вызывались." : "Demo-кнопки меняют только локальное состояние React."}</p>
    </div>
  );
}
