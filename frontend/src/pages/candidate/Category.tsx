import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { GradeBadge, SpecBadge } from "../../components/Badges";
import StartTest from "../../components/StartTest";
import { ErrorBox, Loading } from "../../components/States";
import ThetaScale from "../../components/ThetaScale";
import { get, type S } from "../../lib/api";
import { useCatalog } from "../../lib/catalog";
import { GRADE, SPEC, dateTime, pct, decimal } from "../../lib/format";

export default function Category() {
  const { data: cat } = useCatalog();
  const q = useQuery({ queryKey: ["category"], queryFn: () => get<S["CategoryOut"]>("/me/category") });
  if (q.isPending) return <Loading />;
  if (!q.data) return <ErrorBox error={q.error} />;
  const c = q.data;
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold">Моя категория</h1>
      {c.status === "none" ? (
        <div className="card space-y-3"><p>Категории пока нет — пройдите тест.</p><StartTest /></div>
      ) : (
        <>
          <div className="card space-y-2">
            <div className="flex flex-wrap items-center gap-2"><SpecBadge spec={c.spec} /><GradeBadge grade={c.grade} status={c.status} /></div>
            <p className="text-sm text-slate-600">
              θ = {decimal(c.theta)} · лучше {pct(c.percentile)} категории · тест {dateTime(c.tested_at)}
              {c.confirmed_at ? ` · подтверждён ${dateTime(c.confirmed_at)}` : ""}
            </p>
            {c.theta != null && <ThetaScale theta={c.theta} thresholds={cat?.grades ?? []} />}
          </div>
          <div className="card space-y-3">
            <h2 className="font-bold">Сменить грейд</h2>
            <ul className="text-sm text-slate-600">
              {Object.entries(c.can_retest).map(([g, until]) => (
                <li key={g}>{GRADE[g]}: {until && new Date(until) > new Date() ? `доступно ${dateTime(until)}` : "доступно сейчас"}</li>
              ))}
            </ul>
            <StartTest defaultSpec={c.spec} defaultGrade={c.suggest_upgrade ? undefined : c.grade} compact />
          </div>
        </>
      )}
      {c.attempts.length > 0 && (
        <div className="card">
          <h2 className="mb-2 font-bold">История попыток</h2>
          <table className="w-full text-sm">
            <thead className="text-left text-slate-500"><tr><th className="py-1">Когда</th><th>Специализация</th><th>Грейд</th><th>θ</th><th>Итог</th></tr></thead>
            <tbody>
              {c.attempts.map((a) => (
                <tr key={a.id} className="border-t">
                  <td className="py-1.5">{dateTime(a.started_at)}</td><td>{SPEC[a.spec]}</td><td>{GRADE[a.claimed_grade]}</td>
                  <td className="tabular-nums">{decimal(a.theta)}</td>
                  <td>{a.finished_at ? <Link className="text-fsp hover:underline" to={`/candidate/result/${a.id}`}>{a.result === "confirmed" ? "подтверждён" : "не подтверждён"}</Link> : <Link className="text-fsp" to={`/candidate/test/${a.id}`}>продолжить</Link>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
