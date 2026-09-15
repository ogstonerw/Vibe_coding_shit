import productGraphSnapshot from "../data/generated/productGraphSnapshot.json";

const stateLabels = {
  DONE: "DONE",
  CURRENT: "CURRENT DEVELOPMENT",
  NEXT: "NEXT",
  PLANNED: "PLANNED",
  LOCKED: "LOCKED",
} as const;

type DisplayState = keyof typeof stateLabels;
type OwnerDecision = {
  id: string;
  reason: string;
  status: string;
  subject: string;
};

export function OwnerHqOverview() {
  const {
    authority,
    development,
    owner_decisions_required,
    product,
    schema_version,
    source,
    summary,
  } = productGraphSnapshot;
  const ownerDecisions: readonly OwnerDecision[] = owner_decisions_required;
  const foundation = development.waves.find((wave) => wave.id === "W0");
  const currentWave = development.waves.find(
    (wave) => wave.id === development.current_wave_id,
  );

  if (!foundation || !currentWave) {
    throw new Error("Owner HQ projection is missing the foundation or current Wave");
  }

  const summaryItems = [
    ["Domains", summary.domain_count],
    ["Waves", summary.wave_count],
    ["Epics", summary.epic_count],
    ["Locked objects", summary.locked_object_count],
  ] as const;

  return (
    <section className="owner-hq" aria-labelledby="owner-hq-title">
      <header className="owner-hq__header">
        <div>
          <span className="owner-hq__eyebrow">OWNER HQ · PRODUCT</span>
          <h1 id="owner-hq-title">{product.name}</h1>
          <p>30-second product-development control surface</p>
        </div>
        <div className="projection-seal" aria-label="Read-only Product Graph projection">
          <strong>{source.projection}</strong>
          <span>PRODUCT GRAPH PROJECTION</span>
          <small>{source.operational ? "OPERATIONAL" : "NON-OPERATIONAL"}</small>
        </div>
      </header>

      <div className="owner-hq__stage-grid" aria-label="Development state">
        <article className="stage-card stage-card--done">
          <span>Completed foundation</span>
          <strong>{foundation.id} · {foundation.title}</strong>
          <em>DONE</em>
        </article>
        <article className="stage-card stage-card--next">
          <span>Current development Wave</span>
          <strong>{currentWave.id} · {currentWave.title}</strong>
          <em>CURRENT · canonical status {currentWave.status}</em>
        </article>
        <article className="stage-card stage-card--direction">
          <span>Current Product OS direction</span>
          <p>{product.north_star}</p>
        </article>
      </div>

      <div className="owner-hq__content-grid">
        <section className="hq-board hq-roadmap" aria-labelledby="roadmap-title">
          <div className="hq-board__title">
            <div>
              <span>DEVELOPMENT</span>
              <h2 id="roadmap-title">Roadmap</h2>
            </div>
            <div className="roadmap-legend" aria-label="Roadmap state legend">
              {Object.entries(stateLabels).map(([state, label]) => (
                <span className={`state-key state-key--${state.toLowerCase()}`} key={state}>
                  {label}
                </span>
              ))}
            </div>
          </div>
          <ol className="wave-roadmap">
            {development.waves.map((wave) => {
              const displayState = wave.display_state as DisplayState;
              return (
                <li
                  className={`wave-card wave-card--${displayState.toLowerCase()}`}
                  data-display-state={displayState}
                  key={wave.id}
                >
                  <span className="wave-card__id">{wave.id}</span>
                  <strong>{wave.title}</strong>
                  <small>{stateLabels[displayState]}</small>
                </li>
              );
            })}
          </ol>
        </section>

        <aside className="owner-hq__side-stack">
          <section className="hq-board hq-summary" aria-labelledby="summary-title">
            <div className="hq-board__title">
              <div><span>GRAPH</span><h2 id="summary-title">Summary</h2></div>
            </div>
            <dl>
              {summaryItems.map(([label, value]) => (
                <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
              ))}
            </dl>
          </section>

          <section className="hq-board hq-attention" aria-labelledby="attention-title">
            <div className="hq-board__title">
              <div><span>OWNER</span><h2 id="attention-title">Attention</h2></div>
              <b>{ownerDecisions.length}</b>
            </div>
            {ownerDecisions.length > 0 ? (
              <ul>
                {ownerDecisions.map((decision) => (
                  <li key={decision.id}>
                    <strong>{decision.subject}</strong>
                    <span>{decision.reason}</span>
                    <small>{decision.status}</small>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No Owner decisions required.</p>
            )}
          </section>
        </aside>
      </div>

      <section className="hq-board hq-authority" aria-labelledby="authority-title">
        <div className="hq-board__title">
          <div><span>SAFETY</span><h2 id="authority-title">Authority locks</h2></div>
          <strong className="capital-authority">
            Capital authority · {authority.capital_authority ? "GRANTED" : "FALSE · LOCKED"}
          </strong>
        </div>
        <div className="authority-grid">
          {authority.environments.map((environment) => (
            <article className="authority-card" key={environment.subject}>
              <span aria-hidden="true">▣</span>
              <div><strong>{environment.label}</strong><small>{environment.reason}</small></div>
              <b>{environment.status}</b>
            </article>
          ))}
        </div>
      </section>

      <footer className="owner-hq__source">
        <strong>{source.name} · v{schema_version}</strong>
        <span>{source.generated_from}</span>
        <span>{source.classification}</span>
        <span>
          {source.writable_runtime_truth
            ? "Writable runtime truth"
            : "Projection only · no writable Product Graph"}
        </span>
      </footer>
    </section>
  );
}
