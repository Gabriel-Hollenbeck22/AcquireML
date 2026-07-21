import { BrowserRouter, Route, Routes } from "react-router-dom";
import SessionListPage from "./pages/SessionListPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SessionListPage />} />
        <Route path="/new" element={<div>New session (coming in Task 5)</div>} />
      </Routes>
    </BrowserRouter>
  );
}
