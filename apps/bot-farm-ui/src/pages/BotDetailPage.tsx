import { Link, useParams } from "react-router-dom";
import { useFarmData } from "../app/FarmDataContext";
import { PixelSprite } from "../components/PixelSprite";
import { VerdictBadge } from "../components/VerdictBadge";

const pipelineGlyphs = {
  export: "↧",
  parser: "{ }",
  risk: "◆",
  intent: "LIMIT",
  journal: "▤",
} as const;

export function BotDetailPage() {
  const { botId } = useParams();
  const { snapshot } = useFarmData();
  const bot = snapshot?.bots.find((candidate) => candidate.id === botId);

  if (!snapshot || !bot) {
    return (
      <section className="page-card empty-page">
        <span className="empty-page__icon" aria-hidden="true">?</span>
        <h1>Бот не найден</h1>
        <p>На этой грядке пока никто не работает.</p>
        <Link className="pixel-button" to="/">Вернуться в парк</Link>
      </section>
    );
  }

  const isPrimaryBot = bot.id === "tb-001";

  return (
    <div className="detail-page">
      <div className="breadcrumb"><Link to="/">Парк ботов</Link><span>/</span><strong>{bot.name}</strong></div>

      <section className="bot-passport parchment-card">
        <div className="passport-portrait"><PixelSprite kind={bot.sprite} size="large" label={`Портрет ${bot.name}`} /></div>
        <div className="passport-copy">
          <div className="eyebrow">Паспорт агента · {bot.isDemo ? "DEMO ENTITY" : "VERIFIED SLICE"}</div>
          <h1>{bot.name}</h1>
          <p>{bot.role}</p>
          <dl>
            <div><dt>Рынок</dt><dd>{bot.market}</dd></div>
            <div><dt>Контур</dt><dd>{bot.strategy}</dd></div>
            <div><dt>Последний прогон</dt><dd>{bot.lastRun}</dd></div>
          </dl>
        </div>
        <div className="passport-score">
          <small>Готовность</small><strong>{bot.readiness}%</strong>
          <span className="readiness-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={bot.readiness}><i style={{ width: `${bot.readiness}%` }} /></span>
          <em>{bot.stageLabel}</em>
        </div>
      </section>

      {bot.isDemo && (
        <div className="demo-disclaimer" role="note"><strong>DEMO:</strong> этот персонаж показывает будущую форму интерфейса. Его торговая логика не реализована.</div>
      )}

      <section className="page-section stage-section" aria-labelledby="stage-title">
        <div className="section-heading"><span className="section-icon" aria-hidden="true">↟</span><div><span>Маршрут допуска</span><h2 id="stage-title">Стадии бота</h2></div></div>
        <ol className="stage-path">
          {bot.progression.map((step, index) => (
            <li className={`stage-step stage-step--${step.state}`} key={step.label}>
              <span className="stage-node" aria-hidden="true">{step.state === "complete" ? "✓" : step.state === "locked" ? "×" : index + 1}</span>
              <span><strong>{step.label}</strong><small>{step.state === "complete" ? "Пройдено" : step.state === "current" ? "Текущая стадия" : "Заблокировано"}</small></span>
            </li>
          ))}
        </ol>
      </section>

      {isPrimaryBot && bot.pipeline && (
        <section className="page-section pipeline-section" aria-labelledby="pipeline-title">
          <div className="section-heading"><span className="section-icon" aria-hidden="true">⚙</span><div><span>Offline production line</span><h2 id="pipeline-title">Historical Telegram Replay</h2></div><strong className="score-stamp">{snapshot.quality.passedTests} / {snapshot.quality.totalTests} {snapshot.release.offline}</strong></div>
          <div className="pipeline-track">
            {bot.pipeline.map((station, index) => (
              <div className="pipeline-station" key={station.id}>
                <span className={`station-machine station-machine--${station.kind}`} aria-hidden="true">{pipelineGlyphs[station.kind]}</span>
                <strong>{station.label}</strong>
                <small>{station.kind === "intent" ? "SIMULATED ONLY" : "deterministic"}</small>
                {index < bot.pipeline!.length - 1 && <i className="pipeline-arrow" aria-hidden="true">→</i>}
              </div>
            ))}
          </div>
          <p className="safety-note"><span aria-hidden="true">▣</span> Локальные fixture-данные проходят через parser, risk sizing и симулированный LIMIT intent. Сетевых вызовов, fills и денег нет.</p>
        </section>
      )}

      <div className="detail-grid">
        <section className="page-section" aria-labelledby="gates-title">
          <div className="section-heading"><span className="section-icon" aria-hidden="true">✓</span><div><span>Evidence board</span><h2 id="gates-title">Release gates</h2></div></div>
          <ul className="gate-list">
            {bot.gates.map((gate) => (
              <li key={gate.id}><span><strong>{gate.label}</strong>{gate.detail && <small>{gate.detail}</small>}</span><VerdictBadge verdict={gate.verdict} /></li>
            ))}
          </ul>
        </section>

        <section className="page-section" aria-labelledby="reviews-title">
          <div className="section-heading"><span className="section-icon" aria-hidden="true">★</span><div><span>Agent council</span><h2 id="reviews-title">Ревью</h2></div></div>
          {bot.reviews.length > 0 ? (
            <ul className="review-mini-list">
              {bot.reviews.map((review) => (
                <li key={review.role}><span><strong>{review.role}</strong><small>{review.detail}</small></span><VerdictBadge verdict={review.verdict} /></li>
              ))}
            </ul>
          ) : <p className="muted-copy">Для demo-персонажа ревью ещё не проводилось.</p>}
          <Link className="pixel-button pixel-button--secondary" to="/reviews">Открыть совет ревьюеров</Link>
        </section>
      </div>

      <section className="capital-lock" aria-label="Блокировка реального капитала">
        <span className="capital-lock__icon" aria-hidden="true">▣</span>
        <div><strong>REAL CAPITAL · LOCKED</strong><p>Paper, Limited Live и Live не разрешены. Этот интерфейс не создаёт ордера и не меняет действующие governance gates.</p></div>
        <VerdictBadge verdict="LOCKED" />
      </section>
    </div>
  );
}
