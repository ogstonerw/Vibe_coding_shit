import { Link } from "react-router-dom";
import type { Bot } from "../domain/botFarm";
import { FarmScenery } from "./FarmScenery";
import { PixelSprite } from "./PixelSprite";

function FarmZone({ bot }: { bot: Bot }) {
  return (
    <Link
      to={`/bots/${bot.id}`}
      className={`farm-zone farm-zone--${bot.environment}`}
      aria-label={`Открыть ${bot.name}: ${bot.status}`}
    >
      <span className="zone-sign">
        <strong>{bot.shortName}</strong>
        <small>{bot.id === "tb-001" ? "Telegram BTC" : bot.stageLabel}</small>
      </span>
      <FarmScenery environment={bot.environment} />
      <span className="zone-worker">
        <PixelSprite kind={bot.sprite} size="large" decorative />
      </span>
      <span className={`zone-status zone-status--${bot.health}`}>
        <span className="status-light" aria-hidden="true" />
        {bot.status}
      </span>
      {bot.isDemo && <span className="demo-ribbon">DEMO</span>}
    </Link>
  );
}

export function FarmMap({ bots }: { bots: readonly Bot[] }) {
  return (
    <section className="farm-map" aria-labelledby="farm-map-title">
      <h2 className="sr-only" id="farm-map-title">Карта фермы торговых ботов</h2>
      <div className="farm-map__path farm-map__path--vertical" aria-hidden="true" />
      <div className="farm-map__path farm-map__path--horizontal" aria-hidden="true" />
      <div className="farm-pond" aria-hidden="true"><span className="pond-ripple pond-ripple--one" /><span className="pond-ripple pond-ripple--two" /><span className="pond-duck" /></div>
      <div className="farm-tree farm-tree--one" aria-hidden="true" />
      <div className="farm-tree farm-tree--two" aria-hidden="true" />
      <div className="farm-tree farm-tree--three" aria-hidden="true" />
      <div className="farm-flowers" aria-hidden="true"><i /><i /><i /><i /></div>
      <div className="farm-zones">
        {bots.map((bot) => <FarmZone key={bot.id} bot={bot} />)}
      </div>
      <div className="farm-welcome" aria-hidden="true">ДОБРО ПОЖАЛОВАТЬ</div>
      <div className="pixel-chicken" aria-hidden="true"><span /></div>
    </section>
  );
}
