import { Link } from "react-router-dom";
import type { Bot, FarmBuilding } from "../domain/botFarm";
import { PixelSprite } from "./PixelSprite";

export function FarmStatusPanel({ bots, buildings }: { bots: readonly Bot[]; buildings: readonly FarmBuilding[] }) {
  return (
    <aside className="farm-status wood-panel" aria-labelledby="farm-status-title">
      <div className="panel-title">
        <span className="panel-title__leaf" aria-hidden="true" />
        <h2 id="farm-status-title">Состояние фермы</h2>
      </div>
      <div className="farm-status__list">
        {bots.map((bot) => (
          <Link className="bot-health-card" to={`/bots/${bot.id}`} key={bot.id} aria-label={`${bot.name}, ${bot.evidenceLabel}, ${bot.status}`}>
            <PixelSprite kind={bot.sprite} size="small" label={`Портрет ${bot.name}`} />
            <span className="bot-health-card__body">
              <strong>{bot.name}</strong>
              <span className="bot-building-label">{buildings.find((building) => building.id === bot.buildingId)?.name}</span>
              <span className={`evidence-label evidence-label--${bot.evidenceTone}`}>{bot.evidenceLabel}</span>
              <span className={`evidence-status evidence-status--${bot.evidenceTone}`}><i aria-hidden="true" />{bot.status}</span>
            </span>
          </Link>
        ))}
      </div>
      <Link className="monitor-link" to="/releases">Открыть доску допуска <span aria-hidden="true">→</span></Link>
    </aside>
  );
}
