import { Link } from "react-router-dom";
import { useFarmData } from "../app/FarmDataContext";
import { VerdictBadge } from "../components/VerdictBadge";

type UtilityKind = "events" | "notifications" | "builds";

const utilityMeta = {
  events: {
    eyebrow: "Local event shelf",
    title: "Журнал событий",
    description: "Последние сообщения типизированного mock snapshot. Постоянное хранилище событий пока не подключено.",
    glyph: "▤",
  },
  notifications: {
    eyebrow: "Mock inbox",
    title: "Уведомления",
    description: "Локальная витрина новостей фермы без push, polling и внешних сервисов.",
    glyph: "●",
  },
  builds: {
    eyebrow: "Release shelf",
    title: "Архив билдов",
    description: "Текущий offline release snapshot. История сборок станет доступна после появления read-only API.",
    glyph: "◇",
  },
} as const;

export function UtilityPage({ kind }: { kind: UtilityKind }) {
  const { snapshot } = useFarmData();
  if (!snapshot) return null;
  const meta = utilityMeta[kind];

  return (
    <div className="content-page">
      <header className="page-banner"><span className="banner-art" aria-hidden="true">{meta.glyph}</span><div><span className="eyebrow">{meta.eyebrow}</span><h1>{meta.title}</h1><p>{meta.description}</p></div><strong>LOCAL MOCK</strong></header>
      {kind === "builds" ? (
        <section className="page-section utility-release" aria-labelledby="utility-build-title">
          <div className="section-heading"><span className="section-icon" aria-hidden="true">▣</span><div><span>{snapshot.release.slice}</span><h2 id="utility-build-title">{snapshot.release.botId} · {snapshot.release.stage}</h2></div><VerdictBadge verdict={snapshot.release.offline} /></div>
          <dl className="utility-facts"><div><dt>Owner Merge</dt><dd>{snapshot.release.ownerMerge}</dd></div><div><dt>Owner Pilot</dt><dd>{snapshot.release.ownerPilot}</dd></div><div><dt>Owner Live</dt><dd>{snapshot.release.ownerLive}</dd></div></dl>
          <Link className="pixel-button" to="/releases">Открыть доску релиза</Link>
        </section>
      ) : (
        <section className="page-section" aria-labelledby="utility-news-title">
          <div className="section-heading"><span className="section-icon" aria-hidden="true">☷</span><div><span>Farm snapshot</span><h2 id="utility-news-title">{kind === "events" ? "Последние события" : "Непрочитанные mock-сообщения"}</h2></div></div>
          <ul className="utility-list">
            {snapshot.news.map((item) => <li key={item.id}><span className={`utility-dot utility-dot--${item.tone}`} aria-hidden="true" /><div><strong>{item.message}</strong><small>{item.age}</small></div></li>)}
          </ul>
          <p className="muted-copy">Элементы read-only: подтверждение прочтения и серверная синхронизация не реализованы.</p>
        </section>
      )}
    </div>
  );
}
