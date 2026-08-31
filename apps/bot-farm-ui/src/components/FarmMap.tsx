import { useRef, useState, type KeyboardEvent } from "react";
import { Link } from "react-router-dom";
import type {
  Bot,
  FarmBuilding,
  FarmBuildingId,
  FarmDirection,
  FarmNavigation,
} from "../domain/botFarm";
import { FarmScenery } from "./FarmScenery";
import { PixelSprite } from "./PixelSprite";

const directionKeys: Partial<Record<string, FarmDirection>> = {
  ArrowLeft: "left",
  ArrowRight: "right",
  ArrowUp: "up",
  ArrowDown: "down",
};

const directionGlyphs: Record<FarmDirection, string> = {
  left: "←",
  right: "→",
  up: "↑",
  down: "↓",
};

const directionLabels: Record<FarmDirection, string> = {
  left: "влево",
  right: "вправо",
  up: "вверх",
  down: "вниз",
};

const agentKindLabels = {
  trading: "Trading bot",
  research: "Research bot",
  service: "Service bot",
  review: "Review bot",
} as const;

function BuildingNpc({ bot }: { bot: Bot }) {
  return (
    <Link
      className={`building-npc building-npc--${bot.evidenceTone}`}
      to={`/bots/${bot.id}`}
      aria-label={`${bot.name}, ${agentKindLabels[bot.agentKind]}, ${bot.evidenceLabel}, ${bot.status}`}
    >
      <PixelSprite kind={bot.sprite} size="small" decorative />
      <span><strong>{bot.shortName}</strong><small>{agentKindLabels[bot.agentKind]}</small></span>
      <i aria-hidden="true" />
      {bot.isDemo && <em>DEMO</em>}
    </Link>
  );
}

interface FarmBuildingCardProps {
  building: FarmBuilding;
  bots: readonly Bot[];
  active: boolean;
  registerButton: (node: HTMLButtonElement | null) => void;
  onSelect: () => void;
}

function FarmBuildingCard({ building, bots, active, registerButton, onSelect }: FarmBuildingCardProps) {
  const buildingBots = building.botIds
    .map((botId) => bots.find((bot) => bot.id === botId))
    .filter((bot): bot is Bot => Boolean(bot));
  const freeSlots = Math.max(0, building.capacity - buildingBots.length);

  return (
    <article
      className={`farm-building farm-building--${building.kind}${active ? " farm-building--active" : ""}`}
      aria-labelledby={`${building.id}-title`}
    >
      <button
        ref={registerButton}
        className="zone-sign building-sign"
        type="button"
        tabIndex={active ? 0 : -1}
        aria-pressed={active}
        aria-label={`${building.name}, ${buildingBots.length} из ${building.capacity} NPC-ботов, ${building.status}`}
        onClick={onSelect}
      >
        <strong id={`${building.id}-title`}>{building.name}</strong>
        <small>{building.shortName} · {buildingBots.length}/{building.capacity}</small>
      </button>
      <FarmScenery kind={building.kind} />
      <div className="building-npcs" aria-label={`NPC-боты: ${building.name}`}>
        {buildingBots.map((bot) => <BuildingNpc bot={bot} key={bot.id} />)}
        {Array.from({ length: freeSlots }, (_, index) => (
          <span className="building-slot" key={`${building.id}-slot-${index + 1}`}>
            <i aria-hidden="true">+</i><small>Свободный слот</small>
          </span>
        ))}
      </div>
      <div className="building-status">
        <strong>{building.status}</strong><small>{building.statusDetail}</small>
      </div>
    </article>
  );
}

interface FarmMapProps {
  bots: readonly Bot[];
  buildings: readonly FarmBuilding[];
  navigation: FarmNavigation;
}

export function FarmMap({ bots, buildings, navigation }: FarmMapProps) {
  const [activeBuildingId, setActiveBuildingId] = useState<FarmBuildingId>(navigation.initialBuildingId);
  const [announcement, setAnnouncement] = useState("");
  const buildingRefs = useRef<Partial<Record<FarmBuildingId, HTMLButtonElement>>>({});

  const activeBuilding = buildings.find((building) => building.id === activeBuildingId) ?? buildings[0];
  const availableConnections = navigation.connections.filter((connection) => connection.from === activeBuildingId);

  function selectBuilding(buildingId: FarmBuildingId, announce = true) {
    const building = buildings.find((candidate) => candidate.id === buildingId);
    if (!building) return;
    setActiveBuildingId(buildingId);
    if (announce) setAnnouncement(`Owner переместился к зданию ${building.name}`);
  }

  function move(direction: FarmDirection) {
    const connection = availableConnections.find((candidate) => candidate.direction === direction);
    if (!connection) return;
    selectBuilding(connection.to);
    buildingRefs.current[connection.to]?.focus({ preventScroll: true });
  }

  function handleMapKeyDown(event: KeyboardEvent<HTMLElement>) {
    const direction = directionKeys[event.key];
    if (direction) {
      event.preventDefault();
      move(direction);
      return;
    }
    if (event.key === "Escape") {
      event.preventDefault();
      buildingRefs.current[activeBuildingId]?.focus({ preventScroll: true });
    }
  }

  return (
    <section
      className="farm-map"
      aria-labelledby="farm-map-title"
      data-active-building={activeBuildingId}
      onKeyDown={handleMapKeyDown}
    >
      <h2 className="sr-only" id="farm-map-title">Карта зданий и NPC-ботов</h2>
      <div className="farm-map__path farm-map__path--vertical" aria-hidden="true" />
      <div className="farm-map__path farm-map__path--horizontal" aria-hidden="true" />
      <div className="farm-pond" aria-hidden="true"><span className="pond-ripple pond-ripple--one" /><span className="pond-ripple pond-ripple--two" /><span className="pond-duck" /></div>
      <div className="farm-tree farm-tree--one" aria-hidden="true" />
      <div className="farm-tree farm-tree--two" aria-hidden="true" />
      <div className="farm-tree farm-tree--three" aria-hidden="true" />
      <div className="farm-flowers" aria-hidden="true"><i /><i /><i /><i /></div>

      <div className="farm-zones">
        {buildings.map((building) => (
          <FarmBuildingCard
            key={building.id}
            building={building}
            bots={bots}
            active={building.id === activeBuildingId}
            registerButton={(node) => {
              if (node) buildingRefs.current[building.id] = node;
              else delete buildingRefs.current[building.id];
            }}
            onSelect={() => selectBuilding(building.id)}
          />
        ))}
      </div>

      <div className={`farm-owner farm-owner--${activeBuildingId}`} aria-hidden="true">
        <PixelSprite kind="owner" size="small" decorative />
        <span>OWNER</span>
      </div>

      <nav className="farm-movement-pad" aria-label={`Переходы от здания ${activeBuilding?.name ?? "не выбрано"}`}>
        <strong>Ходить по ферме</strong>
        <div>
          {availableConnections.map((connection) => {
            const destination = buildings.find((building) => building.id === connection.to);
            return (
              <button
                type="button"
                className={`move-button move-button--${connection.direction}`}
                key={`${connection.direction}-${connection.to}`}
                onClick={() => move(connection.direction)}
                aria-label={`Перейти ${directionLabels[connection.direction]} к зданию ${destination?.name ?? connection.to}`}
              >
                <span aria-hidden="true">{directionGlyphs[connection.direction]}</span>
              </button>
            );
          })}
        </div>
        <small>Стрелки клавиатуры · только навигация</small>
      </nav>

      <p className="sr-only" aria-live="polite">{announcement}</p>
      <div className="farm-welcome" aria-hidden="true">РАСШИРЯЕМАЯ ФЕРМА</div>
      <div className="pixel-chicken" aria-hidden="true"><span /></div>
    </section>
  );
}
