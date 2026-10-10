import type { S } from "../lib/api";
import { GRADE, RESULT_ROLE, SPEC, STATUS, statusTone } from "../lib/format";

export function GradeBadge({ grade, status }: { grade?: string | null; status?: string | null }) {
  if (!grade) return <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-xs text-slate-600">Без категории</span>;
  const ok = status === "confirmed";
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        ok ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
      }`}
      title={ok ? "Грейд подтверждён тестом" : "Кандидат заявил грейд, но тест его не подтвердил — показан ниже в выдаче"}
    >
      {GRADE[grade] ?? grade} · {ok ? "подтверждён" : "не подтверждён"}
    </span>
  );
}

export function SpecBadge({ spec }: { spec?: string | null }) {
  if (!spec) return null;
  return <span className="rounded-full bg-fsp/10 px-2.5 py-0.5 text-xs font-semibold text-fsp">{SPEC[spec] ?? spec}</span>;
}

export function StatusBadge({ status }: { status?: string | null }) {
  if (!status) return null;
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${statusTone[status] ?? "bg-slate-100"}`}>
      {STATUS[status] ?? status}
    </span>
  );
}

/** Подтверждённые результаты ФСП или явная пометка, что истории нет (обязательный случай ТЗ). */
export function FspResults({ results, compact }: { results: S["ResultOut"][]; compact?: boolean }) {
  if (!results.length)
    return <span className="text-xs text-slate-500">Нет истории ФСП — оценка по тесту и стеку</span>;
  const shown = compact ? results.slice(0, 2) : results;
  return (
    <div className="flex flex-wrap gap-1.5">
      {shown.map((r, i) => (
        <span
          key={r.id ?? i}
          className="rounded-md bg-fsp-tint px-2 py-0.5 text-xs text-fsp-dark"
          title={`${r.event}, ${r.year}${r.team ? ", команда" : ""}`}
        >
          🏆 {RESULT_ROLE[r.role]}{r.place ? ` · ${r.place} место` : ""} · {r.discipline} · {r.year}
        </span>
      ))}
      {compact && results.length > 2 && <span className="text-xs text-slate-500">ещё {results.length - 2}</span>}
    </div>
  );
}

export function SkillChips({ skills, highlight }: { skills: string[]; highlight?: Set<string> }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      {skills.map((s) => {
        const hit = highlight?.has(s.toLowerCase());
        return (
          <span
            key={s}
            className={`rounded-md px-2 py-0.5 text-xs ${hit ? "bg-fsp text-white" : "bg-slate-100 text-slate-700"}`}
          >
            {s}
          </span>
        );
      })}
    </div>
  );
}
