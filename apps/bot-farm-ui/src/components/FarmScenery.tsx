import type { FarmBuildingKind } from "../domain/botFarm";

export function FarmScenery({ kind }: { kind: FarmBuildingKind }) {
  if (kind === "coop") {
    return (
      <div className="scenery scenery--coop" aria-hidden="true">
        <div className="crypto-coop"><span className="coop-roof" /><span className="coop-door" /><span className="coop-sign">BTC</span></div>
        <div className="coop-fence" /><div className="coop-feed" />
      </div>
    );
  }
  if (kind === "barn") {
    return (
      <div className="scenery scenery--barn" aria-hidden="true">
        <div className="moex-barn"><span className="barn-roof" /><span className="barn-door" /><span className="barn-sign">MOEX</span></div>
        <div className="barn-crates" /><div className="barrel" />
      </div>
    );
  }
  if (kind === "tower") {
    return (
      <div className="scenery scenery--tower" aria-hidden="true">
        <div className="watchtower"><span className="tower-flag" /><span className="tower-shield">+</span></div>
        <div className="stone-fence" />
      </div>
    );
  }
  return (
    <div className="scenery scenery--workshop" aria-hidden="true">
      <div className="review-hut"><span className="bulletin"><i /><i /><i /></span></div>
      <div className="paper-desk"><span /><span /></div>
      <div className="book-stack" />
    </div>
  );
}
