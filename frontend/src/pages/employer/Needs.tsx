import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Empty, ErrorBox, Loading } from "../../components/States";
import { ApiError, get, post, type S } from "../../lib/api";
import { useCatalog } from "../../lib/catalog";
import { GRADE, SALARY_TYPE, SPEC, WORK_FORMAT, money } from "../../lib/format";

/** Кабинет работодателя: потребности («кого вы ищете») → подборка. */
export default function Needs() {
  const needs = useQuery({ queryKey: ["needs"], queryFn: () => get<S["NeedOut"][]>("/employer/needs") });
  const [creating, setCreating] = useState(false);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Подбор</h1>
          <p className="text-slate-600">Опишите, кто нужен, — система покажет категорию и кандидатов с объяснением.</p>
        </div>
        {!creating && (
          <button className="btn-accent" onClick={() => setCreating(true)}>+ Кого вы ищете</button>
        )}
      </div>

      {creating && <NeedWizard onCancel={() => setCreating(false)} />}

      {needs.isLoading ? (
        <Loading />
      ) : needs.error ? (
        <ErrorBox error={needs.error} />
      ) : !needs.data?.length ? (
        !creating && <Empty title="Пока нет ни одной потребности" hint="Начните с описания: специализация, грейд, стек и зарплата." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {needs.data.map((n) => (
            <Link key={n.id} to={`/employer/needs/${n.id}`} className="card block transition hover:border-fsp hover:shadow">
              <div className="flex items-start justify-between gap-3">
                <h2 className="font-bold">{n.title}</h2>
                {n.published && <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-800">вакансия</span>}
              </div>
              <p className="mt-1 text-sm text-slate-600">
                {SPEC[n.spec] ?? n.spec} · {GRADE[n.grade] ?? n.grade}
                {n.work_format ? ` · ${WORK_FORMAT[n.work_format]}` : ""}
              </p>
              <p className="mt-2 font-semibold text-fsp">{money(n.salary_from, n.salary_to, n.salary_type)}</p>
              <p className="mt-2 text-sm text-slate-500">
                {n.skills.map((s) => String((s as { name: string }).name)).join(" · ")}
              </p>
              <span className="mt-3 inline-block text-sm font-semibold text-fsp">Открыть подборку →</span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function NeedWizard({ onCancel }: { onCancel: () => void }) {
  const { data: cat } = useCatalog();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [spec, setSpec] = useState("backend");
  const [grade, setGrade] = useState("middle");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [skills, setSkills] = useState<Record<string, number>>({});
  const [from, setFrom] = useState(0);
  const [to, setTo] = useState(0);
  const [salaryType, setSalaryType] = useState<"gross" | "net">("net");
  const [workFormat, setWorkFormat] = useState("hybrid");
  const [error, setError] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      post<S["NeedCreated"]>("/needs", {
        title: title || `${SPEC[spec]} (${GRADE[grade]})`,
        spec,
        grade,
        skills: Object.entries(skills).map(([name, weight]) => ({ name, weight })),
        description: description || null,
        salary_from: from,
        salary_to: to,
        salary_type: salaryType,
        work_format: workFormat,
      }),
    onSuccess: (n) => {
      qc.invalidateQueries({ queryKey: ["needs"] });
      navigate(`/employer/needs/${n.id}`);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Не удалось сохранить"),
  });

  const toggleSkill = (s: string) =>
    setSkills((prev) => {
      const next = { ...prev };
      if (next[s]) delete next[s];
      else next[s] = 2;
      return next;
    });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!Object.keys(skills).length) return setError("Выберите хотя бы один навык");
    if (!from || !to || from > to) return setError("Зарплата обязательна: укажите «от» и «до»");
    setError(null);
    create.mutate();
  };

  const specSkills = cat?.skills[spec] ?? [];

  return (
    <form className="card space-y-5 border-fsp/40" onSubmit={submit}>
      <h2 className="text-lg font-bold">Кого вы ищете</h2>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <span className="label">Специализация</span>
          <div className="flex flex-wrap gap-2">
            {(cat?.specs ?? []).map((s) => (
              <button
                type="button"
                key={s.id}
                onClick={() => {
                  setSpec(s.id);
                  setSkills({});
                }}
                className={`btn border ${spec === s.id ? "border-fsp bg-fsp text-white" : "border-slate-300 bg-white"}`}
              >
                {s.title}
              </button>
            ))}
          </div>
        </div>
        <div>
          <span className="label">Грейд</span>
          <div className="flex flex-wrap gap-2">
            {(cat?.grades ?? []).map((g) => (
              <button
                type="button"
                key={g.id}
                onClick={() => setGrade(g.id)}
                className={`btn border ${grade === g.id ? "border-fsp bg-fsp text-white" : "border-slate-300 bg-white"}`}
              >
                {g.title}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <span className="label">Стек — отметьте навыки и их важность (1 — желательно, 3 — обязательно)</span>
        <div className="flex flex-wrap gap-2">
          {specSkills.map((s) => {
            const w = skills[s];
            return (
              <div key={s} className={`flex items-center overflow-hidden rounded-lg border ${w ? "border-fsp" : "border-slate-300"}`}>
                <button type="button" onClick={() => toggleSkill(s)} className={`px-3 py-1.5 text-sm ${w ? "bg-fsp text-white" : "bg-white"}`}>
                  {s}
                </button>
                {w && (
                  <select
                    aria-label={`Важность ${s}`}
                    className="border-l border-fsp bg-fsp/5 px-1 py-1.5 text-sm"
                    value={w}
                    onChange={(e) => setSkills({ ...skills, [s]: +e.target.value })}
                  >
                    <option value={1}>1</option>
                    <option value={2}>2</option>
                    <option value={3}>3</option>
                  </select>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label" htmlFor="n-title">Название позиции</label>
          <input id="n-title" className="input" placeholder={`${SPEC[spec]} (${GRADE[grade]})`} value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div>
          <span className="label">Формат работы</span>
          <div className="flex flex-wrap gap-2">
            {Object.entries(WORK_FORMAT).map(([k, v]) => (
              <button
                type="button"
                key={k}
                onClick={() => setWorkFormat(k)}
                className={`btn border ${workFormat === k ? "border-fsp bg-fsp/5 text-fsp" : "border-slate-300 bg-white"}`}
              >
                {v}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div>
        <label className="label" htmlFor="n-desc">Чем занимается команда</label>
        <textarea id="n-desc" className="input min-h-20" value={description} onChange={(e) => setDescription(e.target.value)} />
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div>
          <label className="label" htmlFor="n-from">Зарплата от, ₽</label>
          <input id="n-from" className="input" type="number" min={1} required value={from || ""} onChange={(e) => setFrom(+e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="n-to">до, ₽</label>
          <input id="n-to" className="input" type="number" min={1} required value={to || ""} onChange={(e) => setTo(+e.target.value)} />
        </div>
        <div>
          <span className="label">Сумма</span>
          <div className="flex flex-col gap-1 text-sm">
            {(["net", "gross"] as const).map((t) => (
              <label key={t} className="flex items-center gap-2">
                <input type="radio" name="n-type" checked={salaryType === t} onChange={() => setSalaryType(t)} /> {SALARY_TYPE[t]}
              </label>
            ))}
          </div>
        </div>
      </div>

      {error && <p className="text-sm text-fsp-accent">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-ghost" onClick={onCancel}>Отмена</button>
        <button className="btn-primary" disabled={create.isPending}>{create.isPending ? "Подбираем…" : "Показать подборку"}</button>
      </div>
    </form>
  );
}
