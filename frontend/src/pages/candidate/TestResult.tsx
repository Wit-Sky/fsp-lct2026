import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import StartTest from "../../components/StartTest";
import { ErrorBox, Loading } from "../../components/States";
import ThetaScale from "../../components/ThetaScale";
import { get, type S } from "../../lib/api";
import { useCatalog } from "../../lib/catalog";
import { GRADE, SPEC, dateTime } from "../../lib/format";

const ORDER = ["junior", "middle", "senior"];

export default function TestResult() {
  const id = Number(useParams().attemptId);
  const { data: cat } = useCatalog();
  const q = useQuery({ queryKey: ["result", id], queryFn: () => get<S["TestResultOut"]>(`/tests/${id}/result`) });
  const [retry, setRetry] = useState<string | null>(null);
  if (q.isPending) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const r = q.data!;
  const lower = ORDER[ORDER.indexOf(r.claimed_grade) - 1];
  const higher = ORDER[ORDER.indexOf(r.claimed_grade) + 1];

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <div className={`card ${r.confirmed ? "border-emerald-300 bg-emerald-50" : "border-amber-300 bg-amber-50"}`}>
        <p className="text-sm text-slate-600">{SPEC[r.spec]} · тест на {GRADE[r.claimed_grade]}</p>
        <h1 className="mt-1 text-2xl font-bold">{r.confirmed ? `Грейд ${GRADE[r.claimed_grade]} подтверждён` : `Грейд ${GRADE[r.claimed_grade]} пока не подтверждён`}</h1>
        <p className="mt-1 text-slate-700">
          Верных ответов: {r.correct} из {r.total}. Оценка способности θ = {r.theta.toFixed(2)}
          {r.grade ? ` — уровень ${GRADE[r.grade]}` : " — ниже порога Junior"}.
        </p>
        {!r.confirmed && <p className="mt-1 text-sm text-slate-600">Работодатели видят заявленный грейд с пометкой «не подтверждён», ниже в выдаче. Принудительно грейд не понижается.</p>}
      </div>

      <div className="card">
        <h2 className="font-bold">Где вы на шкале</h2>
        <ThetaScale theta={r.theta} thresholds={cat?.grades ?? []} />
        <p className="mt-3 text-xs text-slate-500">θ считается по модели Раша: учитываются не только верные ответы, но и сложность каждого задания.</p>
      </div>

      <div className="card">
        <h2 className="mb-3 font-bold">Разбор по темам</h2>
        <div className="space-y-2">
          {(r.topics as { topic: string; total: number; correct: number }[]).map((t) => (
            <div key={t.topic} className="flex items-center gap-3 text-sm">
              <span className="w-24 shrink-0">{t.topic}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-100">
                <div className="h-full bg-fsp" style={{ width: `${(t.correct / t.total) * 100}%` }} />
              </div>
              <span className="w-12 text-right tabular-nums">{t.correct}/{t.total}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card space-y-3">
        <h2 className="font-bold">Что дальше</h2>
        {r.next_attempt_at && <p className="text-sm text-slate-600">Повтор на этот или более высокий грейд — не раньше {dateTime(r.next_attempt_at)}.</p>}
        <div className="flex flex-wrap gap-2">
          {!r.confirmed && lower && <button className="btn-primary" onClick={() => setRetry(lower)}>Пройти на {GRADE[lower]} — сейчас</button>}
          {r.suggest_upgrade && higher && <button className="btn-accent" onClick={() => setRetry(higher)}>Вы справились уверенно — тест на {GRADE[higher]}</button>}
          <Link className="btn-ghost" to="/candidate/category">Моя категория</Link>
        </div>
        {retry && <div className="border-t pt-4"><StartTest key={retry} defaultSpec={r.spec} defaultGrade={retry} compact /></div>}
      </div>
    </div>
  );
}
