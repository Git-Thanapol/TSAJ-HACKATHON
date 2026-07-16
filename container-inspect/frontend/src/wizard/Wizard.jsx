import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import Starfield from "./Starfield.jsx";
import { RingChrome, StepArc, RadialOptions, RecentArc, RingLink } from "./Ring.jsx";
import CenterStage from "./CenterStage.jsx";
import MenuOverlay from "./MenuOverlay.jsx";
import { VisionPanel, LidarPanel, ReviewPanel, RecordPanel, MEASURABLE } from "./panels.jsx";

const STEPS = [
  { id: "select", label: "เลือกมาตรฐานการตรวจ", title: "เลือกมาตรฐานการตรวจและตู้", sub: "SELECT STANDARD & CONTAINER · ISO 6346 CHECK-DIGIT VALIDATED" },
  { id: "vision", label: "Vision", title: "Vision ระบุโซนที่ควรตรวจ", sub: "LOCAL YOLO ZONING · TRIAGE ONLY — NEVER PASS/FAIL" },
  { id: "lidar", label: "LiDAR", title: "LiDAR scan วัดขนาดจริง", sub: "METROLOGY · MEASURED MM VS STANDARD LIMIT" },
  { id: "review", label: "ทบทวน & เซ็น", title: "ผู้ตรวจทบทวนและเซ็นรับรอง", sub: "PRECEDENCE · HUMAN > METROLOGY > VISION" },
  { id: "record", label: "บันทึก", title: "บันทึกและส่งต่อ", sub: "HASH-CHAINED RECORD · WEBHOOK inspection.completed" },
];

export default function Wizard() {
  const [step, setStep] = useState(1);
  const [meta, setMeta] = useState(null);
  const [form, setForm] = useState({ container_id: "", direction: "inbound", standard: "" });
  const [inspection, setInspection] = useState(null);
  const [vision, setVision] = useState(null);
  const [metrology, setMetrology] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [visionScanning, setVisionScanning] = useState(false);
  const [overrides, setOverrides] = useState({});
  const [signedBy, setSignedBy] = useState("user:117");
  const [signed, setSigned] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [recent, setRecent] = useState([]);

  // recent signed inspections for the right-arc list (newest first)
  useEffect(() => {
    api("/v0/inspections")
      .then((r) => setRecent(r.inspections.filter((i) => i.status === "signed")))
      .catch(() => {});
  }, [signed, step]);

  useEffect(() => {
    api("/v0/meta")
      .then((m) => {
        setMeta(m);
        setForm((f) => ({
          ...f,
          container_id: m.demo_containers[0]?.container_id ?? "",
          standard: m.standards[0]?.name ?? "",
        }));
      })
      .catch((e) => setError(e.message));
  }, []);

  function restart() {
    setStep(1);
    setInspection(null);
    setVision(null);
    setMetrology(null);
    setOverrides({});
    setSigned(null);
    setError(null);
  }

  async function call(fn) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (err) {
      setError(err.detail?.reason || err.message);
    } finally {
      setBusy(false);
    }
  }

  const startInspection = () =>
    call(async () => {
      const insp = await api("/v0/inspections", { method: "POST", body: JSON.stringify(form) });
      setInspection(insp);
      setVision(null);
      setMetrology(null);
      setOverrides({});
      setSigned(null);
      setStep(2);
    });

  const runVision = () => {
    setVisionScanning(true); // beam sweeps the model while YOLO runs (min 2.4s so it reads on stage)
    call(async () => {
      const [res] = await Promise.all([
        api(`/v0/inspections/${inspection.inspection_id}/run-vision`, { method: "POST" }),
        new Promise((r) => setTimeout(r, 2400)),
      ]);
      setVision({ zones: res.zones, photos: res.photos });
    }).finally(() => setVisionScanning(false));
  };

  const runLidar = () => {
    setScanning(true); // video starts; API runs behind the sweep
    call(async () => {
      const res = await api(`/v0/inspections/${inspection.inspection_id}/run-metrology`, { method: "POST" });
      setMetrology({ mode: res.mode, measurements: res.measurements });
    });
  };

  const sign = () =>
    call(async () => {
      const body = {
        signed_by: signedBy,
        overrides: Object.entries(overrides)
          .filter(([, o]) => o.active)
          .map(([key, o]) => {
            const [component, concern] = key.split("|");
            return { component, concern, result: o.result, note: o.note || null };
          }),
      };
      const res = await api(`/v0/inspections/${inspection.inspection_id}/sign`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setSigned({ record: res.record, webhook: res.webhook });
      setStep(5);
    });

  // unique (component, concern) with attached measurement where mm decides
  const findings = useMemo(() => {
    if (!vision) return [];
    return [...new Map(vision.zones.map((z) => [`${z.component}|${z.concern}`, z])).values()].map((z) => {
      const m = metrology?.measurements.find(
        (mm) => mm.component === z.component && MEASURABLE.has(z.concern),
      );
      return { component: z.component, concern: z.concern, measurement: m ?? null };
    });
  }, [vision, metrology]);

  const current = STEPS[step - 1];
  const containerOpts =
    meta?.demo_containers.map((c) => ({ value: c.container_id, label: c.container_id })) ?? [];

  return (
    <div className="stage font-body">
      <Starfield />
      <RingChrome />
      <CenterStage scanning={scanning} visionScanning={visionScanning} onScanEnd={() => setScanning(false)} />
      <StepArc steps={STEPS} current={step} onJump={signed ? null : setStep} />
      {step === 1 && (
        <>
          <RadialOptions
            options={containerOpts}
            value={form.container_id}
            onSelect={(v) => setForm({ ...form, container_id: v })}
          />
          <RecentArc items={recent} />
          <RingLink angle={-38} href="/yard" label="Yard System ↗" />
        </>
      )}

      {/* header chrome */}
      <header className="absolute inset-x-0 top-0 flex items-start justify-between p-6">
        <span className="font-display text-sm font-semibold tracking-[0.2em] text-slate-200">
          CONTAINER<span className="text-cyan-400">-INSPECT</span>
        </span>
        <div className="pointer-events-none absolute inset-x-0 top-6 mx-auto w-fit max-w-xl text-center">
          <p className="eyebrow">STEP {step} / {STEPS.length}</p>
          <h1 className="step-title mt-2">{current.title}</h1>
          <p className="mt-1 font-display text-[0.65rem] uppercase tracking-[0.3em] text-slate-500">{current.sub}</p>
        </div>
        <button className="btn-ghost" onClick={() => setMenuOpen(true)}>MENU</button>
      </header>

      {error && (
        <p className="absolute inset-x-0 top-36 mx-auto w-fit rounded-full border border-red-900 bg-red-950/80 px-5 py-2 text-sm text-red-300">
          {error}
        </p>
      )}

      {/* step 1 bottom controls */}
      {step === 1 && (
        <div className="absolute inset-x-0 bottom-10 flex flex-wrap items-center justify-center gap-3">
          <select
            value={form.direction}
            onChange={(e) => setForm({ ...form, direction: e.target.value })}
            className="select-pill"
            aria-label="ทิศทาง"
          >
            <option value="inbound">ขาเข้า (inbound)</option>
            <option value="outbound">ขาออก (outbound)</option>
          </select>
          <select
            value={form.standard}
            onChange={(e) => setForm({ ...form, standard: e.target.value })}
            className="select-pill"
            aria-label="มาตรฐาน"
          >
            {meta?.standards.map((s) => (
              <option key={s.name} value={s.name}>{s.name} · {s.version} ({s.mode})</option>
            ))}
          </select>
          <button className="btn-primary" disabled={busy || !meta || !form.container_id} onClick={startInspection}>
            เริ่มการตรวจ
          </button>
        </div>
      )}

      {inspection && step >= 2 && (
        <p className="absolute bottom-6 left-6 font-mono text-xs text-slate-600">
          {inspection.container_id} · {inspection.standard.name} {inspection.standard.version} · {inspection.direction}
          <span className="ml-2 rounded-full bg-emerald-950 px-2 py-0.5 text-[0.6rem] text-emerald-300">ISO 6346 ✓</span>
        </p>
      )}

      {step === 2 && <VisionPanel vision={vision} busy={busy} onRun={runVision} onNext={() => setStep(3)} />}
      {step === 3 && (
        <LidarPanel
          metrology={metrology}
          scanning={scanning}
          busy={busy}
          onScan={runLidar}
          onNext={() => setStep(4)}
        />
      )}
      {step === 4 && (
        <ReviewPanel
          findings={findings}
          overrides={overrides}
          setOverrides={setOverrides}
          signedBy={signedBy}
          setSignedBy={setSignedBy}
          busy={busy}
          onSign={sign}
        />
      )}
      {step === 5 && signed && (
        <RecordPanel
          signed={signed}
          inspectionId={inspection.inspection_id}
          onOpenYard={() => setMenuOpen(true)}
          onRestart={restart}
        />
      )}

      <p className="absolute bottom-6 right-6 max-w-xs text-right text-[0.65rem] text-slate-600">
        ระบบช่วยตัดสินใจ (decision support) — มนุษย์เซ็นรับรองทุกการตรวจ
      </p>

      <MenuOverlay open={menuOpen} onClose={() => setMenuOpen(false)} />
    </div>
  );
}
