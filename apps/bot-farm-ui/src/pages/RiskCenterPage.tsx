import { useFarmData } from "../app/FarmDataContext";

const riskNotes = {
  NORMAL: "Штатный offline-контур",
  WATCH: "Наблюдение без исполнения",
  DE_RISK: "Снижение допуска",
  PROTECT: "Защитная остановка",
  EMERGENCY: "Полная блокировка",
} as const;

export function RiskCenterPage() {
  const { snapshot } = useFarmData();
  if (!snapshot) return null;

  return (
    <div className="content-page">
      <header className="page-banner page-banner--risk"><span className="banner-art" aria-hidden="true">◆</span><div><span className="eyebrow">Read-only sentinel</span><h1>Risk Center</h1><p>Наглядная лестница защитных состояний без рыночных данных и элементов исполнения.</p></div><strong>{snapshot.risk.current}</strong></header>
      <div className="risk-layout">
        <section className="page-section risk-ladder-card" aria-labelledby="risk-ladder-title">
          <div className="section-heading"><span className="section-icon" aria-hidden="true">↥</span><div><span>Policy ladder</span><h2 id="risk-ladder-title">Контуры защиты</h2></div></div>
          <ol className="risk-ladder">
            {snapshot.risk.ladder.map((state, index) => (
              <li className={state === snapshot.risk.current ? "risk-state risk-state--current" : "risk-state"} key={state}>
                <span>{index + 1}</span><div><strong>{state.replace("_", "-")}</strong><small>{riskNotes[state]}</small></div>{state === snapshot.risk.current && <em>CURRENT</em>}
              </li>
            ))}
          </ol>
        </section>
        <aside className="watchtower-card" aria-label="Состояние реального капитала">
          <div className="watchtower-art" aria-hidden="true"><span /><i /></div>
          <span className="eyebrow">Capital perimeter</span><h2>REAL CAPITAL</h2><strong>{snapshot.risk.capitalState}</strong>
          <p>{snapshot.risk.note}</p>
          <ul><li>Нет API-ключей</li><li>Нет позиций и PnL</li><li>Нет fills и ордеров</li><li>Paper / Live blocked</li></ul>
        </aside>
      </div>
      <div className="risk-readonly-note" role="note"><strong>Только чтение.</strong> Страница визуализирует mock-политику и не предоставляет controls для изменения риска.</div>
    </div>
  );
}
