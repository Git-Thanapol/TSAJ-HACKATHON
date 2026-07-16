// Right-side step panels + shared chips. All copy Thai, technical words English.

const CONCERN_COLORS = {
  dent: "border-amber-400 text-amber-300",
  hole: "border-red-500 text-red-400",
  rust: "border-orange-500 text-orange-300",
};

// mirrors fusion.MEASURABLE_CONCERNS: mm decides deformation, not appearance
export const MEASURABLE = new Set(["dent", "hole"]);

// Thai display names for ruleset components (ids stay English in the record)
const COMPONENT_TH = {
  side_panel_left: "ผนังด้านซ้าย",
  side_panel_right: "ผนังด้านขวา",
  side_panel: "ผนังข้าง",
  end_panel: "ผนังท้าย",
  door: "ประตู",
  roof: "หลังคา",
  floor: "พื้น",
  corner_post: "เสามุม",
  understructure: "โครงใต้ท้อง",
};

export const componentTh = (c) => COMPONENT_TH[c] ?? c;

export function ResultChip({ result }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 font-display text-[0.65rem] uppercase tracking-widest ${
        result === "pass" ? "bg-emerald-950 text-emerald-300" : "bg-amber-950 text-amber-300"
      }`}
    >
      {result}
    </span>
  );
}

export function ConcernTag({ concern }) {
  return (
    <span className={`rounded border px-1.5 py-0.5 text-xs capitalize ${CONCERN_COLORS[concern] ?? "border-slate-500"}`}>
      {concern}
    </span>
  );
}

export function Panel({ title, children, footer }) {
  return (
    <aside className="glass absolute right-6 top-24 bottom-24 flex w-[24rem] flex-col overflow-hidden">
      <h2 className="border-b hairline px-5 py-3 font-display text-xs uppercase tracking-[0.3em] text-slate-300">
        {title}
      </h2>
      <div className="flex-1 space-y-3 overflow-y-auto p-5 text-sm">{children}</div>
      {footer && <div className="border-t hairline px-5 py-4">{footer}</div>}
    </aside>
  );
}

export function PhotoCard({ photo, zones }) {
  return (
    <figure className="overflow-hidden rounded-lg border hairline bg-black/40">
      <div className="relative">
        <img src={photo.url} alt={photo.component} className="block w-full" />
        {zones.map((z, i) => {
          const [cx, cy, w, h] = z.bbox;
          return (
            <div
              key={i}
              className={`absolute border-2 ${CONCERN_COLORS[z.concern] ?? "border-slate-300"}`}
              style={{
                left: `${(cx - w / 2) * 100}%`,
                top: `${(cy - h / 2) * 100}%`,
                width: `${w * 100}%`,
                height: `${h * 100}%`,
              }}
            >
              <span className="absolute -top-4 left-0 rounded bg-black/80 px-1 text-[0.6rem] capitalize">
                {z.concern}
              </span>
            </div>
          );
        })}
      </div>
      <figcaption className="px-2 py-1 text-[0.65rem] text-slate-400">
        {componentTh(photo.component)} · {zones.length} โซน
      </figcaption>
    </figure>
  );
}

export function VisionPanel({ vision, busy, onRun, onNext }) {
  return (
    <Panel
      title="Vision · โซนที่ควรตรวจ"
      footer={
        vision ? (
          <button className="btn-primary w-full" onClick={onNext}>ถัดไป · LiDAR scan</button>
        ) : (
          <button className="btn-primary w-full" disabled={busy} onClick={onRun}>
            {busy ? "กำลังสแกน…" : "เริ่ม vision scan"}
          </button>
        )
      }
    >
      <p className="rounded border border-cyan-900/60 bg-cyan-950/40 px-3 py-2 text-xs text-cyan-200">
        Vision ชี้<span className="font-semibold">จุดที่ควรตรวจ</span>เท่านั้น ไม่ใช่ผู้ตัดสิน
      </p>
      {vision ? (
        <div className="grid grid-cols-2 gap-2">
          {vision.photos.map((p) => (
            <PhotoCard key={p.file} photo={p} zones={vision.zones.filter((z) => z.image === p.file)} />
          ))}
        </div>
      ) : (
        <p className="text-xs text-slate-500">
          YOLO รันในเครื่องจาก weights บนดิสก์ — ไม่เรียก cloud API
        </p>
      )}
    </Panel>
  );
}

export function LidarPanel({ metrology, scanning, busy, onScan, onNext }) {
  return (
    <Panel
      title="LiDAR · ค่าที่วัดเทียบเกณฑ์"
      footer={
        metrology && !scanning ? (
          <button className="btn-primary w-full" onClick={onNext}>ถัดไป · ทบทวน & เซ็น</button>
        ) : (
          <button className="btn-primary w-full" disabled={busy || scanning} onClick={onScan}>
            {scanning ? "กำลังสแกน…" : "เริ่ม LiDAR scan"}
          </button>
        )
      }
    >
      {scanning && <p className="text-xs text-cyan-300">กำลังกวาดลำแสงรอบตู้… (mockup — ระบบจริงใช้ LiDAR/photogrammetry)</p>}
      {!scanning && metrology && (
        <ul className="space-y-2">
          {metrology.measurements.map((m) => (
            <li key={m.component} className="rounded border hairline px-3 py-2">
              <div className="flex items-center gap-2">
                <ResultChip result={m.result} />
                <span className="text-slate-300">{componentTh(m.component)}</span>
              </div>
              <p className="mt-1 text-xs text-slate-400">
                {m.measure}: <span className="font-mono text-slate-200">{m.value_mm} mm</span>
                <span className="text-slate-500"> · เกณฑ์ {m.limit_mm} mm · {m.source}</span>
              </p>
            </li>
          ))}
          {metrology.measurements.length === 0 && (
            <li className="text-xs text-slate-500">
              {metrology.mode === "appearance_only"
                ? "โปรไฟล์ appearance-only: ไม่มีเกณฑ์ mm — ทุกรายการส่งให้ผู้ตรวจตัดสิน"
                : "ไม่มีชิ้นส่วนที่วัดได้ — ทุกรายการส่งให้ผู้ตรวจตัดสิน"}
            </li>
          )}
        </ul>
      )}
      {!scanning && !metrology && (
        <p className="text-xs text-slate-500">กดปุ่มเพื่อยิงสแกนและประเมินค่าเทียบเกณฑ์มาตรฐาน</p>
      )}
    </Panel>
  );
}

export function ReviewPanel({ findings, overrides, setOverrides, signedBy, setSignedBy, busy, onSign }) {
  return (
    <Panel
      title="ทบทวน & เซ็นรับรอง"
      footer={
        <div className="flex items-center gap-3">
          <input
            value={signedBy}
            onChange={(e) => setSignedBy(e.target.value)}
            placeholder="ผู้เซ็นรับรอง"
            className="w-36 rounded-full border hairline bg-black/40 px-3 py-2 text-xs"
          />
          <button className="btn-primary flex-1" disabled={busy || !signedBy} onClick={onSign}>
            เซ็นรับรอง
          </button>
        </div>
      }
    >
      <p className="text-xs text-slate-500">
        ลำดับการตัดสิน <span className="font-mono">Human &gt; Metrology &gt; Vision</span> — ค่าที่วัดได้คงอยู่ในบันทึกเสมอ
      </p>
      <ul className="space-y-2">
        {findings.map((f) => {
          const key = `${f.component}|${f.concern}`;
          const o = overrides[key] ?? { active: false, result: "pass", note: "" };
          const machineResult = f.measurement ? f.measurement.result : "concern";
          return (
            <li key={key} className="rounded border hairline px-3 py-2">
              <div className="flex flex-wrap items-center gap-2">
                <ConcernTag concern={f.concern} />
                <span className="text-slate-300">{componentTh(f.component)}</span>
                <ResultChip result={machineResult} />
              </div>
              <p className="mt-1 text-xs text-slate-500">
                {f.measurement
                  ? `metrology ${f.measurement.value_mm}mm / เกณฑ์ ${f.measurement.limit_mm}mm`
                  : "รอผู้ตรวจตัดสิน"}
              </p>
              <label className="mt-2 flex items-center gap-2 text-xs text-slate-400">
                <input
                  type="checkbox"
                  checked={o.active}
                  onChange={(e) => setOverrides({ ...overrides, [key]: { ...o, active: e.target.checked } })}
                />
                เปลี่ยนผล (override)
              </label>
              {o.active && (
                <div className="mt-2 flex gap-2">
                  <select
                    value={o.result}
                    onChange={(e) => setOverrides({ ...overrides, [key]: { ...o, result: e.target.value } })}
                    className="select-pill !py-1 text-xs"
                  >
                    <option value="pass">pass</option>
                    <option value="concern">concern</option>
                  </select>
                  <input
                    value={o.note}
                    placeholder="หมายเหตุ (เช่น คราบแห้ง)"
                    onChange={(e) => setOverrides({ ...overrides, [key]: { ...o, note: e.target.value } })}
                    className="flex-1 rounded-full border hairline bg-black/40 px-3 py-1 text-xs"
                  />
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </Panel>
  );
}

export function RecordPanel({ signed, inspectionId, onOpenYard, onRestart }) {
  const rec = signed.record;
  return (
    <Panel
      title="บันทึกเข้า hash chain แล้ว"
      footer={
        <div className="flex flex-wrap gap-2">
          <a
            href={`/v0/inspections/${inspectionId}/report.pdf`}
            target="_blank"
            rel="noreferrer"
            className="btn-primary flex-1 text-center"
          >
            เปิด PDF
          </a>
          <button className="btn-ghost" onClick={onOpenYard}>Yard inbox</button>
          <button className="btn-ghost" onClick={onRestart}>ตรวจตู้ถัดไป</button>
        </div>
      }
    >
      <p className="text-xs text-slate-400">
        เซ็นโดย <span className="text-slate-200">{rec.signed_by}</span> เมื่อ {rec.signed_at}
      </p>
      <p className={`text-xs ${signed.webhook?.delivered ? "text-emerald-300" : "text-red-300"}`}>
        webhook inspection.completed — {signed.webhook?.delivered ? "ส่งถึง Yard System แล้ว" : "ส่งไม่สำเร็จ"}
      </p>
      <ul className="space-y-2">
        {rec.findings.map((f, i) => (
          <li key={i} className="rounded border hairline px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              <ResultChip result={f.result} />
              <ConcernTag concern={f.concern} />
              <span className="text-slate-300">{componentTh(f.component)}</span>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              โซนจาก: {f.zone_source} · ตัดสินโดย: {f.decision_source}
              {f.human_override && " · HUMAN OVERRIDE"}
              {f.note && ` · "${f.note}"`}
            </p>
          </li>
        ))}
      </ul>
      <div className="rounded border hairline bg-black/40 p-3">
        <p className="break-all font-mono text-[0.65rem] leading-relaxed text-slate-500">
          hash {rec.hash}
          <br />
          prev {rec.prev_hash}
        </p>
      </div>
      <p className="text-[0.65rem] text-slate-600">
        บันทึก JSON คือแหล่งข้อมูลจริง (source of truth) — PDF เรนเดอร์จากบันทึกนี้
      </p>
    </Panel>
  );
}
