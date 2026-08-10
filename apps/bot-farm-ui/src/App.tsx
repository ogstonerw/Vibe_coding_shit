import { BrowserRouter, Route, Routes } from "react-router-dom";
import { FarmDataProvider } from "./app/FarmDataContext";
import { AppShell } from "./components/AppShell";
import { BotDetailPage } from "./pages/BotDetailPage";
import { DocumentationPage } from "./pages/DocumentationPage";
import { FarmDashboard } from "./pages/FarmDashboard";
import { NotFoundPage } from "./pages/NotFoundPage";
import { ReleasesPage } from "./pages/ReleasesPage";
import { ReviewsPage } from "./pages/ReviewsPage";
import { RiskCenterPage } from "./pages/RiskCenterPage";
import { TestLabPage } from "./pages/TestLabPage";
import { UtilityPage } from "./pages/UtilityPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<FarmDashboard />} />
        <Route path="bots/:botId" element={<BotDetailPage />} />
        <Route path="test-lab" element={<TestLabPage />} />
        <Route path="risk" element={<RiskCenterPage />} />
        <Route path="releases" element={<ReleasesPage />} />
        <Route path="reviews" element={<ReviewsPage />} />
        <Route path="events" element={<UtilityPage kind="events" />} />
        <Route path="notifications" element={<UtilityPage kind="notifications" />} />
        <Route path="builds" element={<UtilityPage kind="builds" />} />
        <Route path="docs" element={<DocumentationPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <FarmDataProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </FarmDataProvider>
  );
}
