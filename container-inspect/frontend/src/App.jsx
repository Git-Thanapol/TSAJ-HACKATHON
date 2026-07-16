import { Route, Routes } from "react-router-dom";
import Wizard from "./wizard/Wizard.jsx";
import YardSystem from "./routes/YardSystem.jsx";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Wizard />} />
      {/* external-consumer view — open on a second screen during the demo */}
      <Route path="/yard" element={<YardSystem />} />
    </Routes>
  );
}
