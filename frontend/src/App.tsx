import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionLayout from "./components/SessionLayout";
import DashboardPage from "./pages/DashboardPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import HistoryPage from "./pages/HistoryPage";
import OverviewPage from "./pages/OverviewPage";
import ExplainPage from "./pages/ExplainPage";
import ComparePage from "./pages/ComparePage";
import ValidatePage from "./pages/ValidatePage";
import SettingsPage from "./pages/SettingsPage";
import BudgetPage from "./pages/BudgetPage";
import ProAppShell from "./pro/components/ProAppShell";
import ProSessionListPage from "./pro/pages/ProSessionListPage";
import ProNewSessionPage from "./pro/pages/ProNewSessionPage";
import ProSessionLayout from "./pro/components/ProSessionLayout";
import ProDashboardPage from "./pro/pages/ProDashboardPage";
import ProRecommendationsPage from "./pro/pages/ProRecommendationsPage";
import ProHistoryPage from "./pro/pages/ProHistoryPage";
import ProOverviewPage from "./pro/pages/ProOverviewPage";
import ProExplainPage from "./pro/pages/ProExplainPage";
import ProComparePage from "./pro/pages/ProComparePage";
import ProValidatePage from "./pro/pages/ProValidatePage";
import ProSettingsPage from "./pro/pages/ProSettingsPage";
import ProBudgetPage from "./pro/pages/ProBudgetPage";

function ClassicApp() {
  return (
    <AppShell>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<NewSessionPage />} />
        <Route path="/sessions/:name" element={<SessionLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="recommend" element={<RecommendationsPage />} />
          <Route path="history" element={<HistoryPage />} />
          <Route path="overview" element={<OverviewPage />} />
          <Route path="explain" element={<ExplainPage />} />
          <Route path="compare" element={<ComparePage />} />
          <Route path="validate" element={<ValidatePage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="budget" element={<BudgetPage />} />
        </Route>
      </Routes>
    </AppShell>
  );
}

function ProApp() {
  return (
    <ProAppShell>
      <Routes>
        <Route path="/" element={<ProSessionListPage />} />
        <Route path="/new" element={<ProNewSessionPage />} />
        <Route path="/sessions/:name" element={<ProSessionLayout />}>
          <Route index element={<ProDashboardPage />} />
          <Route path="recommend" element={<ProRecommendationsPage />} />
          <Route path="history" element={<ProHistoryPage />} />
          <Route path="overview" element={<ProOverviewPage />} />
          <Route path="explain" element={<ProExplainPage />} />
          <Route path="compare" element={<ProComparePage />} />
          <Route path="validate" element={<ProValidatePage />} />
          <Route path="settings" element={<ProSettingsPage />} />
          <Route path="budget" element={<ProBudgetPage />} />
        </Route>
      </Routes>
    </ProAppShell>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/pro/*" element={<ProApp />} />
        <Route path="/*" element={<ClassicApp />} />
      </Routes>
    </BrowserRouter>
  );
}
