import { useFarmData } from "../app/FarmDataContext";
import { FarmMap } from "../components/FarmMap";
import { FarmStatusPanel } from "../components/FarmStatusPanel";
import { OwnerHqOverview } from "../components/OwnerHqOverview";

export function FarmDashboard() {
  const { snapshot } = useFarmData();
  if (!snapshot) return null;

  return (
    <div className="owner-homepage">
      <OwnerHqOverview />
      <section className="farm-world" aria-labelledby="farm-world-title">
        <header className="farm-world__header">
          <div>
            <span>EXISTING FARM EXPERIENCE</span>
            <h2 id="farm-world-title">Bot Farm world & status</h2>
          </div>
          <p>Prototype farm data · separate from canonical product truth</p>
        </header>
        <div className="dashboard-layout">
          <FarmMap bots={snapshot.bots} buildings={snapshot.buildings} navigation={snapshot.navigation} />
          <FarmStatusPanel bots={snapshot.bots} buildings={snapshot.buildings} />
        </div>
      </section>
    </div>
  );
}
