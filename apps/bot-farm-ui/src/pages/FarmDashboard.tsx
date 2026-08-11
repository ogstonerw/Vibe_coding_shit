import { useFarmData } from "../app/FarmDataContext";
import { FarmMap } from "../components/FarmMap";
import { FarmStatusPanel } from "../components/FarmStatusPanel";

export function FarmDashboard() {
  const { snapshot } = useFarmData();
  if (!snapshot) return null;

  return (
    <div className="dashboard-layout">
      <FarmMap bots={snapshot.bots} buildings={snapshot.buildings} navigation={snapshot.navigation} />
      <FarmStatusPanel bots={snapshot.bots} buildings={snapshot.buildings} />
    </div>
  );
}
