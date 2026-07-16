import { useEffect, useState } from "react";
import { api } from "../api.js";

const DIRECTION_TH = { inbound: "ขาเข้า", outbound: "ขาออก" };

// MENU overlay: per-container history (hash-chained), Yard System inbox,
// and past signed inspections
export default function MenuOverlay({ open, onClose }) {
  const [deliveries, setDeliveries] = useState([]);
  const [signed, setSigned] = useState([]);
  const [containers, setContainers] = useState([]);
  const [selectedContainer, setSelectedContainer] = useState("");
  const [history, setHistory] = useState(null);

  useEffect(() => {
    if (!open) return;
    let alive = true;
    api("/v0/meta")
      .then((m) => {
        if (!alive) return;
        const ids = m.demo_containers.map((c) => c.container_id);
        setContainers(ids);
        setSelectedContainer((s) => s || ids[0] || "");
      })
      .catch(() => {});
    const load = async () => {
      try {
        const [inbox, list] = await Promise.all([api("/v0/yard/inbox"), api("/v0/inspections")]);
        if (!alive) return;
        setDeliveries([...inbox.deliveries].reverse());
        setSigned(list.inspections.filter((i) => i.status === "signed"));
      } catch {
        /* backend down: keep last view */
      }
    };
    load();
    const t = setInterval(load, 2000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, [open]);

  useEffect(() => {
    if (!open || !selectedContainer) return;
    api(`/v0/containers/${selectedContainer}/history`)
      .then((h) => setHistory(h))
      .catch(() => setHistory(null));
  }, [open, selectedContainer]);

  if (!open) return null;

  // newest first; the signed record events carry direction + report
  const completed = history
    ? [...history.events].reverse().filter((e) => e.type === "inspection.completed")
    : [];

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div
        className="glass absolute right-6 top-6 bottom-6 flex w-[34rem] flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center border-b hairline px-5 py-3">
          <h2 className="font-display text-sm uppercase tracking-[0.3em] text-slate-300">เมนู</h2>
          <button className="btn-ghost ml-auto !px-3 !py-1" onClick={onClose}>ปิด</button>
        </div>
        <div className="flex-1 space-y-6 overflow-y-auto p-5 text-sm">
          <section>
            <h3 className="font-display text-xs uppercase tracking-[0.3em] text-cyan-300">
              รหัสตู้คอนเทนเนอร์ · Container ID
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              เลือกตู้เพื่อดูประวัติการตรวจ (append-only hash chain) และรายงาน
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {containers.map((id) => (
                <button
                  key={id}
                  onClick={() => setSelectedContainer(id)}
                  className={`rounded-full border px-3 py-1 font-mono text-xs transition-colors ${
                    selectedContainer === id
                      ? "border-cyan-400 text-cyan-300"
                      : "border-slate-700 text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {id}
                </button>
              ))}
            </div>
            <ul className="mt-3 space-y-2">
              {completed.map((e) => {
                const rec = e.payload?.record ?? {};
                const concerns = (rec.findings ?? []).filter((f) => f.result === "concern").length;
                return (
                  <li key={e.event_id} className="rounded border hairline px-3 py-2 text-xs">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`rounded-full px-2 py-0.5 font-display text-[0.62rem] uppercase tracking-widest ${
                        rec.direction === "outbound" ? "bg-indigo-950 text-indigo-300" : "bg-cyan-950 text-cyan-300"
                      }`}>
                        {DIRECTION_TH[rec.direction] ?? rec.direction}
                      </span>
                      <span className="text-slate-300">{rec.standard?.name}</span>
                      <span className="text-slate-500">{(e.ts ?? "").slice(0, 16).replace("T", " ")}</span>
                      <span className="text-amber-300">{concerns} concern</span>
                      <a
                        href={`/v0/inspections/${e.inspection_id}/report.pdf`}
                        target="_blank"
                        rel="noreferrer"
                        className="ml-auto font-semibold text-cyan-400"
                      >
                        รายงาน PDF
                      </a>
                    </div>
                    <p className="mt-1 truncate font-mono text-[0.62rem] text-slate-600">
                      เซ็นโดย {rec.signed_by} · hash {(e.hash ?? "").slice(0, 18)}…
                    </p>
                  </li>
                );
              })}
              {history && completed.length === 0 && (
                <li className="text-xs text-slate-600">ตู้นี้ยังไม่มีการตรวจที่เซ็นรับรอง</li>
              )}
            </ul>
            {history && (
              <p className="mt-2 text-[0.65rem] text-slate-600">
                เหตุการณ์ทั้งหมดในสายโซ่ {history.events.length} รายการ — ประวัติเพิ่มได้อย่างเดียว แก้ย้อนหลังไม่ได้
              </p>
            )}
          </section>

          <section>
            <h3 className="font-display text-xs uppercase tracking-[0.3em] text-cyan-300">
              Yard System · webhook inbox
            </h3>
            <p className="mt-1 text-xs text-slate-500">
              สิ่งที่ระบบภายนอกได้รับจากเหตุการณ์ <span className="font-mono">inspection.completed</span>
              {" "}(เปิดจอแยกได้ที่ <a href="/yard" target="_blank" rel="noreferrer" className="text-cyan-400">/yard</a>)
            </p>
            <ul className="mt-3 space-y-2">
              {deliveries.slice(0, 5).map((d, i) => {
                const rec = d.payload ?? {};
                const concerns = (rec.findings ?? []).filter((f) => f.result === "concern").length;
                return (
                  <li key={i} className="rounded border hairline px-3 py-2 text-xs">
                    <span className="font-mono text-slate-200">{rec.container_id}</span>
                    <span className="text-slate-500"> · {rec.standard?.name} · {DIRECTION_TH[rec.direction] ?? rec.direction} · </span>
                    <span className="text-amber-300">{concerns} concern</span>
                    <span className="text-slate-500"> · เซ็นโดย {rec.signed_by}</span>
                  </li>
                );
              })}
              {deliveries.length === 0 && <li className="text-xs text-slate-600">ยังไม่มี delivery</li>}
            </ul>
          </section>

          <section>
            <h3 className="font-display text-xs uppercase tracking-[0.3em] text-cyan-300">
              การตรวจที่เซ็นแล้ว (ทุกตู้)
            </h3>
            <ul className="mt-3 space-y-2">
              {signed.slice(0, 8).map((i) => (
                <li key={i.inspection_id} className="flex items-center gap-2 rounded border hairline px-3 py-2 text-xs">
                  <span className="font-mono text-slate-200">{i.container_id}</span>
                  <span className="text-slate-500">{i.standard_name} · {DIRECTION_TH[i.direction] ?? i.direction} · {i.created_at}</span>
                  <a
                    href={`/v0/inspections/${i.inspection_id}/report.pdf`}
                    target="_blank"
                    rel="noreferrer"
                    className="ml-auto text-cyan-400"
                  >
                    PDF
                  </a>
                </li>
              ))}
              {signed.length === 0 && <li className="text-xs text-slate-600">ยังไม่มีการตรวจที่เซ็นรับรอง</li>}
            </ul>
          </section>
        </div>
      </div>
    </div>
  );
}
