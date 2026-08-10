import { Link } from "react-router-dom";
import { useFarmData } from "../app/FarmDataContext";
import { VerdictBadge } from "../components/VerdictBadge";

export function ReleasesPage() {
  const { snapshot } = useFarmData();
  if (!snapshot) return null;
  const release = snapshot.release;

  return (
    <div className="content-page">
      <header className="page-banner page-banner--release"><span className="banner-art" aria-hidden="true">▣</span><div><span className="eyebrow">Амбар сборок</span><h1>Releases</h1><p>Доска допуска TB-001. Никакая стадия не продвигается из этого интерфейса.</p></div><strong>{release.slice}</strong></header>
      <section className="release-board" aria-labelledby="release-title">
        <div className="release-board__pin" aria-hidden="true" />
        <div className="release-title-row"><div><span className="eyebrow">{release.botId}</span><h2 id="release-title">Historical Telegram Replay</h2></div><VerdictBadge verdict={release.offline} /></div>
        <p className="release-summary">{release.slice}: {release.stage}. Следующий переход требует отдельного решения владельца.</p>
        <div className="release-gates">
          <div className="release-gate release-gate--pass"><span aria-hidden="true">✓</span><div><small>Offline gates</small><strong>{release.stage}</strong></div><VerdictBadge verdict={release.offline} /></div>
          <div className="release-gate release-gate--pending"><span aria-hidden="true">⌛</span><div><small>Owner Merge</small><strong>Только merge/release кода</strong></div><VerdictBadge verdict={release.ownerMerge} /></div>
          <div className="release-gate release-gate--blocked"><span aria-hidden="true">×</span><div><small>Owner Pilot</small><strong>Paper evidence отсутствует</strong></div><VerdictBadge verdict={release.ownerPilot} /></div>
          <div className="release-gate release-gate--locked"><span aria-hidden="true">▣</span><div><small>Owner Live</small><strong>Реальный капитал закрыт</strong></div><VerdictBadge verdict={release.ownerLive} /></div>
        </div>
        <div className="release-actions"><Link className="pixel-button" to={`/bots/${release.botId}`}>Открыть паспорт TB-001</Link><span>MERGE ≠ PILOT ≠ LIVE</span></div>
      </section>
    </div>
  );
}
