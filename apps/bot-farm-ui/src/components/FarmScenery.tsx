import type { EnvironmentKind } from "../domain/botFarm";

export function FarmScenery({ environment }: { environment: EnvironmentKind }) {
  if (environment === "field") {
    return (
      <div className="scenery scenery--field" aria-hidden="true">
        <div className="mailbox"><span /></div>
        <div className="wheat wheat--one" /><div className="wheat wheat--two" /><div className="wheat wheat--three" />
        <div className="produce-crate" />
      </div>
    );
  }
  if (environment === "market") {
    return (
      <div className="scenery scenery--market" aria-hidden="true">
        <div className="market-stall"><span className="market-sign">MOEX</span><span className="market-awning" /></div>
        <div className="barrel" /><div className="market-crates" />
      </div>
    );
  }
  if (environment === "training") {
    return (
      <div className="scenery scenery--training" aria-hidden="true">
        <div className="target target--one" /><div className="target target--two" />
        <div className="dummy"><span /></div><div className="training-fence" />
      </div>
    );
  }
  if (environment === "tower") {
    return (
      <div className="scenery scenery--tower" aria-hidden="true">
        <div className="watchtower"><span className="tower-flag" /><span className="tower-shield">+</span></div>
        <div className="stone-fence" />
      </div>
    );
  }
  if (environment === "mill") {
    return (
      <div className="scenery scenery--mill" aria-hidden="true">
        <div className="mill-house"><span className="mill-clock" /></div>
        <div className="water-wheel"><span /><span /><span /><span /></div>
        <div className="water-run" />
      </div>
    );
  }
  return (
    <div className="scenery scenery--desk" aria-hidden="true">
      <div className="review-hut"><span className="bulletin"><i /><i /><i /></span></div>
      <div className="paper-desk"><span /><span /></div>
      <div className="book-stack" />
    </div>
  );
}
