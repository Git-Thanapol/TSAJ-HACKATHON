import { useEffect, useRef, useState } from "react";
import { api } from "../api.js";

// Plays the EXTERNAL consumer: a yard/terminal system that subscribed to the
// inspection.completed webhook. It only polls its own inbox — no internal state.
export default function YardSystem() {
  const [deliveries, setDeliveries] = useState([]);
  const [flash, setFlash] = useState(false);
  const count = useRef(0);

  useEffect(() => {
    let alive = true;
    const poll = async () => {
      try {
        const r = await api("/v0/yard/inbox");
        if (!alive) return;
        if (r.deliveries.length > count.current) {
          setFlash(true);
          setTimeout(() => setFlash(false), 1500);
        }
        count.current = r.deliveries.length;
        setDeliveries([...r.deliveries].reverse());
      } catch {
        /* backend down: keep last view */
      }
    };
    poll();
    const t = setInterval(poll, 2000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  return (
    <div className="stage overflow-y-auto font-body">
      <section className="mx-auto max-w-4xl space-y-4 p-8">
        <div className="flex items-center gap-3">
          <h1 className="font-display text-lg uppercase tracking-[0.25em] text-slate-200">
            Yard System <span className="text-slate-500">· ระบบภายนอกที่รับข้อมูล</span>
          </h1>
          <span
            className={`rounded-full px-3 py-1 font-display text-[0.65rem] uppercase tracking-widest transition-colors ${
              flash ? "bg-emerald-400 text-emerald-950" : "glass text-slate-300"
            }`}
          >
            {flash ? "ได้รับ webhook!" : `${deliveries.length} รายการ`}
          </span>
        </div>
        <p className="text-sm text-slate-400">
          สมัครรับเหตุการณ์ <span className="font-mono text-cyan-300">inspection.completed</span> — นี่คือข้อมูลที่ซอฟต์แวร์ลานตู้/ท่าเรือใด ๆ
          จะได้รับผ่าน API (เราเป็น middleware ไม่ใช่ระบบปิด)
        </p>

        {deliveries.length === 0 && (
          <p className="text-sm text-slate-500">กล่องรับยังว่าง — เซ็นรับรองการตรวจในหน้า wizard ก่อน</p>
        )}

        <ul className="space-y-3">
          {deliveries.map((d, i) => {
            const rec = d.payload ?? {};
            const concerns = (rec.findings ?? []).filter((f) => f.result === "concern").length;
            return (
              <li key={i} className="glass p-4">
                <div className="flex flex-wrap items-center gap-2 text-sm">
                  <span className="rounded bg-emerald-950 px-2 py-0.5 font-display text-[0.6rem] uppercase tracking-widest text-emerald-300">
                    {d.event}
                  </span>
                  <span className="font-mono">{rec.container_id}</span>
                  <span className="text-slate-400">{rec.standard?.name}</span>
                  <span className="text-slate-400">{rec.direction}</span>
                  <span className="ml-auto text-xs text-slate-500">
                    {concerns} concern · เซ็นโดย {rec.signed_by}
                  </span>
                </div>
                <details className="mt-2">
                  <summary className="cursor-pointer text-xs text-slate-500">ข้อมูลดิบ (raw payload)</summary>
                  <pre className="mt-2 max-h-64 overflow-auto rounded bg-black/50 p-3 text-xs text-slate-300">
                    {JSON.stringify(d, null, 2)}
                  </pre>
                </details>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
