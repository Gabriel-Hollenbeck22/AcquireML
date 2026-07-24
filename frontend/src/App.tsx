import { BrowserRouter, Route, Routes } from "react-router-dom";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";
import SessionLayout from "./components/SessionLayout";
import DashboardPage from "./pages/DashboardPage";
import RecommendationsPage from "./pages/RecommendationsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<NewSessionPage />} />
        <Route path="/sessions/:name" element={<SessionLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="recommend" element={<RecommendationsPage />} />
          <Route path="history" element={<div>History (coming in Task 5)</div>} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
