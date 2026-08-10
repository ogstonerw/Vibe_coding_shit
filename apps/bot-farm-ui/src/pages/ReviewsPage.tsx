import { useFarmData } from "../app/FarmDataContext";
import { PixelSprite } from "../components/PixelSprite";
import { VerdictBadge } from "../components/VerdictBadge";

export function ReviewsPage() {
  const { snapshot } = useFarmData();
  if (!snapshot) return null;

  return (
    <div className="content-page">
      <header className="page-banner page-banner--reviews"><span className="banner-art" aria-hidden="true">★</span><div><span className="eyebrow">Совет специалистов</span><h1>Agent Reviews</h1><p>Компактная витрина итогов {snapshot.release.slice}; оценки не редактируются из UI.</p></div><strong>{snapshot.quality.unresolvedHigh} HIGH</strong></header>
      <section className="review-council" aria-labelledby="council-title">
        <div className="section-heading"><span className="section-icon" aria-hidden="true">☷</span><div><span>Review evidence</span><h2 id="council-title">Ревьюеры у общего стола</h2></div></div>
        <div className="review-agent-grid">
          {snapshot.reviewAgents.map((agent) => (
            <article className="review-agent-card" key={agent.id}>
              <div className="review-agent-card__portrait"><PixelSprite kind={agent.sprite} size="large" label={`Ревьюер ${agent.name}`} /></div>
              <div><span className="review-role">Independent gate</span><h2>{agent.name}</h2><p>{agent.detail}</p><VerdictBadge verdict={agent.verdict} /></div>
            </article>
          ))}
        </div>
      </section>
      <section className="findings-board" aria-label="Сводка замечаний"><div><small>UNRESOLVED BLOCKER</small><strong>{snapshot.quality.unresolvedBlockers}</strong></div><div><small>UNRESOLVED HIGH</small><strong>{snapshot.quality.unresolvedHigh}</strong></div><div><small>FOLLOW-UP</small><strong>{snapshot.quality.mediumFollowUps} MEDIUM</strong><span>Dependency lockfile</span></div><p>Owner Merge — <b>{snapshot.release.ownerMerge}</b>. Owner Pilot — <b>{snapshot.release.ownerPilot}</b>. Owner Live — <b>{snapshot.release.ownerLive}</b>.</p></section>
    </div>
  );
}
