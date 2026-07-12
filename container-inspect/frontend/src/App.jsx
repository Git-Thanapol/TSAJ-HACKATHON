import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./routes/Dashboard.jsx";
import Twin from "./routes/Twin.jsx";
import Report from "./routes/Report.jsx";
import YardSystem from "./routes/YardSystem.jsx";

const tabs = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/twin", label: "3D Twin" },
  { to: "/report", label: "Report" },
  { to: "/yard", label: "Yard System (external)" },
];

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <nav className="flex gap-1 border-b border-slate-800 px-4 py-2">
        <span className="mr-4 font-semibold tracking-tight">container-inspect</span>
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.end}
            className={({ isActive }) =>
              `rounded px-3 py-1 text-sm ${isActive ? "bg-slate-800" : "text-slate-400 hover:text-slate-100"}`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/twin" element={<Twin />} />
          <Route path="/report" element={<Report />} />
          <Route path="/yard" element={<YardSystem />} />
        </Routes>
      </main>
    </div>
  );
}
