import type { S } from "../lib/api";
import { FACTOR } from "../lib/format";

/**
 * «Почему он здесь»: вклад каждого фактора в итоговый скор 0–100 (вес × значение × 100)
 * и текст объяснения от бэкенда. Факторы без веса (например, множитель за неподтверждённый грейд) — отдельной строкой.
 */
export default function Explain({ items }: { items: S["ExplainItem"][] }) {
  return (
    <ul className="space-y-2.5">
      {items.map((e, i) => {
        const weighted = e.weight != null && e.value != null;
        const points = weighted ? e.weight! * e.value! * 100 : 0;
        const max = weighted ? e.weight! * 100 : 0;
        return (
          <li key={i} className="text-sm">
            {weighted ? (
              <>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-semibold">{FACTOR[e.factor] ?? e.factor}</span>
                  <span className="tabular-nums text-slate-500">
                    {points.toFixed(1)} из {max.toFixed(0)}
                  </span>
                </div>
                <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full rounded-full bg-fsp" style={{ width: `${max ? (points / max) * 100 : 0}%` }} />
                </div>
                <p className="mt-1 text-slate-600">{e.text}</p>
              </>
            ) : (
              <p className="rounded-md bg-amber-50 px-3 py-2 text-amber-900">{e.text}</p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
