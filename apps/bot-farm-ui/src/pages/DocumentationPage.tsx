import { Link } from "react-router-dom";

export function DocumentationPage() {
  return (
    <div className="content-page">
      <header className="page-banner"><span className="banner-art" aria-hidden="true">▥</span><div><span className="eyebrow">Field guide</span><h1>Документация</h1><p>Короткий путеводитель по текущему frontend slice и его неизменяемым safety boundaries.</p></div><strong>UI v0.1</strong></header>
      <div className="docs-grid">
        <section className="page-section"><div className="section-heading"><span className="section-icon" aria-hidden="true">↟</span><div><span>Navigation</span><h2>Маршруты фермы</h2></div></div><ul className="docs-list"><li><Link to="/">Карта фермы</Link><span>шесть bot entities и readiness</span></li><li><Link to="/bots/tb-001">Паспорт TB-001</Link><span>stages, gates и replay pipeline</span></li><li><Link to="/test-lab">Test Lab</Link><span>только local mock run</span></li><li><Link to="/risk">Risk Center</Link><span>read-only protection ladder</span></li></ul></section>
        <section className="page-section"><div className="section-heading"><span className="section-icon" aria-hidden="true">◆</span><div><span>Safety</span><h2>Что интерфейс не делает</h2></div></div><ul className="docs-locks"><li>Не читает Telegram API</li><li>Не вызывает Bitget API</li><li>Не открывает SQLite</li><li>Не запускает Python subprocess</li><li>Не авторизует Paper или Live</li></ul></section>
      </div>
      <section className="page-section docs-seam"><div className="section-heading"><span className="section-icon" aria-hidden="true">⚙</span><div><span>Data seam</span><h2>Как устроены данные</h2></div></div><code>pages/components → FarmDataProvider → BotFarmRepository → MockBotFarmRepository</code><p>Текущий adapter можно заменить read-only API adapter в composition root, не меняя страницы. Полное руководство находится в <b>apps/bot-farm-ui/README.md</b>.</p></section>
    </div>
  );
}
