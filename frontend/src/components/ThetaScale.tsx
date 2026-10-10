import { GRADE } from "../lib/format";

/** Шкала способности θ ∈ [−3; 3] с порогами грейдов и отметкой кандидата. */
export default function ThetaScale({ theta, thresholds }: { theta: number; thresholds: { id: string; threshold: number }[] }) {
  const x = (v: number) => ((Math.max(-3, Math.min(3, v)) + 3) / 6) * 100;
  return (
    <div className="pt-6">
      <div className="relative h-3 rounded-full bg-gradient-to-r from-slate-200 via-fsp-soft to-fsp">
        {thresholds.map((t) => (
          <div key={t.id} className="absolute -top-6 -translate-x-1/2 text-center text-xs text-slate-600" style={{ left: `${x(t.threshold)}%` }}>
            {GRADE[t.id]}
            <div className="mx-auto mt-0.5 h-9 w-px bg-slate-500" />
          </div>
        ))}
        <div className="absolute top-1/2 h-6 w-6 -translate-x-1/2 -translate-y-1/2 rounded-full border-4 border-white bg-fsp-accent shadow" style={{ left: `${x(theta)}%` }} title={`θ = ${theta}`} />
      </div>
      <div className="mt-2 flex justify-between text-xs text-slate-400"><span>−3</span><span>0</span><span>+3</span></div>
    </div>
  );
}
