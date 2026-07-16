// Everything that sits ON the giant ring derives its position from --ring-r,
// so the dots always land exactly on the stroke at any viewport size.
// Angle convention: 0° = right, 90° = down, 180° = left.

function onRingStyle(angleDeg) {
  return {
    position: "absolute",
    transform: `rotate(${angleDeg}deg) translateX(var(--ring-r)) rotate(${-angleDeg}deg)`,
  };
}

export function RingChrome() {
  return (
    <>
      <div className="ring" aria-hidden="true" />
      <div className="beam" aria-hidden="true" />
    </>
  );
}

// left arc: step 01 at the top (208°) descending to the last step (152°)
export function StepArc({ steps, current, onJump }) {
  const start = 208;
  const gap = (152 - start) / (steps.length - 1);
  return (
    <div className="on-ring" aria-label="ขั้นตอนการตรวจ">
      {steps.map((s, i) => {
        const n = i + 1;
        const state = n < current ? "done" : n === current ? "active" : "";
        const clickable = n < current && onJump;
        return (
          <div key={s.id} style={onRingStyle(start + gap * i)}>
            <button
              type="button"
              disabled={!clickable}
              onClick={() => clickable && onJump(n)}
              className={`flex -translate-y-1/2 items-center gap-3 bg-transparent ${clickable ? "cursor-pointer" : "cursor-default"}`}
            >
              <span className={`node-dot ${state}`} />
              <span className={`node-label ${state}`}>
                {String(n).padStart(2, "0")} {s.label}
              </span>
            </button>
          </div>
        );
      })}
    </div>
  );
}

// a single link pinned on the ring (e.g. the external Yard System screen)
export function RingLink({ angle, href, label }) {
  return (
    <div className="on-ring">
      <div style={onRingStyle(angle)}>
        <a href={href} target="_blank" rel="noreferrer" className="radial-opt -translate-y-1/2 -translate-x-2">
          <span className="opt-dot" />
          <span>{label}</span>
        </a>
      </div>
    </div>
  );
}

// lower-right arc: recent signed inspections, newest first.
// First 3 in focus, the rest fade away with distance.
export function RecentArc({ items }) {
  if (!items.length) return null;
  const shown = items.slice(0, 5);
  const opacity = (i) => (i < 3 ? 1 : Math.max(0.12, 0.35 - (i - 3) * 0.2));
  return (
    <div className="on-ring" aria-label="การตรวจล่าสุด">
      <div style={onRingStyle(7)}>
        <span className="node-label block -translate-x-full -translate-y-1/2 pr-4 !text-[0.62rem] text-slate-500">
          การตรวจล่าสุด
        </span>
      </div>
      {shown.map((it, i) => (
        <div key={it.inspection_id} style={{ ...onRingStyle(13 + i * 6), opacity: opacity(i) }}>
          {/* dot sits on the ring; text runs inward so nothing clips at the edge */}
          <span className="flex -translate-x-full -translate-y-1/2 flex-row-reverse items-center gap-2 whitespace-nowrap text-xs">
            <span className={`opt-dot ${i === 0 ? "border-cyan-400 bg-cyan-400" : "border-slate-500"}`} />
            <span className="font-mono text-slate-300">{it.container_id}</span>
            <span className="text-slate-500">{it.standard_name} · {(it.created_at ?? "").slice(5, 16)}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

// upper-right arc: radial container choices (Autoneum "HATCHBACK" style).
// Text runs inward from the ring so it never clips the viewport edge.
export function RadialOptions({ options, value, onSelect }) {
  const n = options.length;
  const spread = Math.min(14 * (n - 1), 36);
  const start = -14 - spread / 2;
  return (
    <div className="on-ring">
      {options.map((opt, i) => (
        <div key={opt.value} style={onRingStyle(start + (n > 1 ? (spread / (n - 1)) * i : 0))}>
          <button
            type="button"
            onClick={() => onSelect(opt.value)}
            className={`radial-opt -translate-y-1/2 -translate-x-full flex-row-reverse ${value === opt.value ? "selected" : ""}`}
          >
            <span className="opt-dot" />
            <span>{opt.label}</span>
          </button>
        </div>
      ))}
    </div>
  );
}
