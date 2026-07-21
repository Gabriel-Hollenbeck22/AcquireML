import { BrowserRouter, Route, Routes } from "react-router-dom";
import SessionListPage from "./pages/SessionListPage";
import NewSessionPage from "./pages/NewSessionPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<NewSessionPage />} />
      </Routes>
    </BrowserRouter>
  );
}
