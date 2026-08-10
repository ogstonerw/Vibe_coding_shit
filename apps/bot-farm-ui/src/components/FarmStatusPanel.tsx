import { Link } from "react-router-dom";
import type { Bot } from "../domain/botFarm";
import { PixelSprite } from "./PixelSprite";

export function FarmStatusPanel({ bots }: { bots: readonly Bot[] }) {
  return (
    <aside className="farm-status wood-panel" aria-labelledby="farm-status-title">
      <div className="panel-title">
        <span className="panel-title__leaf" aria-hidden="true" />
        <h2 id="farm-status-title">Состояние фермы</h2>
      </div>
      <div className="farm-status__list">
        {bots.map((bot) => (
          <Link className="bot-health-card" to={`/bots/${bot.id}`} key={bot.id} aria-label={`${bot.name}, готовность ${bot.readiness}%, ${bot.status}`}>
            <PixelSprite kind={bot.sprite} size="small" label={`Портрет ${bot.name}`} />
            <span className="bot-health-card__body">
              <strong>{bot.name}</strong>
              <span className="health-row"><span>Готовность</span><b>{bot.readiness}%</b></span>
              <span className="readiness-track" role="progressbar" aria-label={`Готовность ${bot.name}`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={bot.readiness}>
                <span style={{ width: `${bot.readiness}%` }} />
              </span>
              <span className={`health-status health-status--${bot.health}`}><i aria-hidden="true" />{bot.status}</span>
            </span>
          </Link>
        ))}
      </div>
      <Link className="monitor-link" to="/releases">Открыть доску допуска <span aria-hidden="true">→</span></Link>
    </aside>
  );
}
