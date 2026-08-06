import { BrowserRouter, Route, Routes } from "react-router-dom";
import AppShell from "./components/AppShell";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionLayout from "./components/SessionLayout";
import DashboardPage from "./pages/DashboardPage";
import RecommendationsPage from "./pages/RecommendationsPage";
import HistoryPage from "./pages/HistoryPage";
import SettingsPage from "./pages/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/" element={<SessionListPage />} />
          <Route path="/new" element={<NewSessionPage />} />
          <Route path="/sessions/:name" element={<SessionLayout />}>
            <Route index element={<DashboardPage />} />
            <Route path="recommend" element={<RecommendationsPage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}
