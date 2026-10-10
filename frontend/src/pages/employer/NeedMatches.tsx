import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { FspResults, GradeBadge, SkillChips, StatusBadge } from "../../components/Badges";
import Explain from "../../components/Explain";
import InviteModal from "../../components/InviteModal";
import { Empty, ErrorBox, Loading } from "../../components/States";
import { get, post, type S } from "../../lib/api";
import { useCatalog } from "../../lib/catalog";
import { GRADE, SPEC, WORK_FORMAT, money, pct } from "../../lib/format";

/**
 * Главный экран продукта: подборка по потребности.
 * Фильтры живут в адресе страницы — уточнение не теряет исходный запрос (потребность), его можно вернуть кнопкой «Сбросить».
 */
export default function NeedMatches() {
  const needId = Number(useParams().needId);
  const [params, setParams] = useSearchParams();
  const gradeAdj = params.get("grade_adj") === "1";
  const fspOnly = params.get("fsp_only") === "1";
  const extra = (params.get("skills") ?? "").split(",").filter(Boolean);
  const [inviting, setInviting] = useState<S["CandidateCard"] | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const qc = useQueryClient();
  const { data: cat } = useCatalog();

  const need = useQuery({ queryKey: ["need", needId], queryFn: () => get<S["NeedOut"]>(`/needs/${needId}`) });
  const cats = useQuery({ queryKey: ["need-cats", needId], queryFn: () => get<S["CategoryCount"][]>(`/needs/${needId}/categories`) });
  const qs = new URLSearchParams({ grade_adj: String(gradeAdj), fsp_only: String(fspOnly), limit: "50" });
  if (extra.length) qs.set("skills", extra.join(","));
  const matches = useQuery({
    queryKey: ["matches", needId, gradeAdj, fspOnly, extra.join(",")],
    queryFn: () => get<S["MatchesOut"]>(`/needs/${needId}/matches?${qs}`),
    placeholderData: keepPreviousData,
  });

  const publish = useMutation({
    mutationFn: () => post<S["NeedOut"]>(`/needs/${needId}/publish`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["need", needId] });
      qc.invalidateQueries({ queryKey: ["needs"] });
    },
  });

  const setFilter = (key: string, value: string | null) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };
  const toggleExtra = (s: string) => {
    const set = new Set(extra);
    if (set.has(s)) set.delete(s);
    else set.add(s);
    setFilter("skills", [...set].join(",") || null);
  };
  const filtersOn = gradeAdj || fspOnly || extra.length > 0;

  if (need.isLoading) return <Loading />;
  if (need.error) return <ErrorBox error={need.error} />;
  const n = need.data!;
  const needSkills = new Set(n.skills.map((s) => String((s as { name: string }).name).toLowerCase()));
  extra.forEach((s) => needSkills.add(s.toLowerCase()));

  return (
    <div className="space-y-5">
      <div>
        <Link to="/employer" className="text-sm text-fsp hover:underline">← Все потребности</Link>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold">{n.title}</h1>
            <p className="text-slate-600">
              {SPEC[n.spec]} · {GRADE[n.grade]}
              {n.work_format ? ` · ${WORK_FORMAT[n.work_format]}` : ""} · <b className="text-fsp">{money(n.salary_from, n.salary_to, n.salary_type)}</b>
            </p>
          </div>
          {n.published ? (
            <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm text-emerald-800">Опубликована как вакансия</span>
          ) : (
            <button className="btn-ghost" disabled={publish.isPending} onClick={() => publish.mutate()}>
              Опубликовать как вакансию
            </button>
          )}
        </div>
      </div>

      {/* Категории: целевая и соседние */}
      {cats.data && (
        <div className="-mx-4 flex snap-x gap-3 overflow-x-auto px-4 pb-1 sm:mx-0 sm:grid sm:grid-cols-3 sm:px-0">
          {cats.data.map((c) => (
            <div key={`${c.spec}-${c.grade}`} className={`card min-w-[230px] snap-start p-4 sm:min-w-0 sm:p-5 ${c.target ? "order-first border-fsp ring-1 ring-fsp/30 sm:order-none" : "opacity-80"}`}>
              <p className="text-sm text-slate-500">{c.target ? "Целевая категория" : "Соседняя категория"}</p>
              <p className="font-bold">{SPEC[c.spec]} · {GRADE[c.grade]}</p>
              <p className="mt-1 text-sm">
                <b>{c.total}</b> кандидатов · {c.confirmed} подтверждены · {c.with_fsp} с ФСП
              </p>
            </div>
          ))}
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
        <aside className="card h-fit space-y-4 lg:sticky lg:top-4">
          <div className="flex items-center justify-between">
            <button className="font-bold lg:pointer-events-none" onClick={() => setShowFilters(!showFilters)}>
              Уточнить{filtersOn ? " •" : ""} <span className="text-fsp lg:hidden">{showFilters ? "▲" : "▼"}</span>
            </button>
            {filtersOn && (
              <button className="text-sm text-fsp hover:underline" onClick={() => setParams({}, { replace: true })}>
                Сбросить
              </button>
            )}
          </div>
          <div className={`space-y-4 ${showFilters ? "" : "hidden lg:block"}`}>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5" checked={gradeAdj} onChange={(e) => setFilter("grade_adj", e.target.checked ? "1" : null)} />
            Соседние грейды
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input type="checkbox" className="mt-0.5" checked={fspOnly} onChange={(e) => setFilter("fsp_only", e.target.checked ? "1" : null)} />
            Только с результатами ФСП
          </label>
          <div>
            <p className="mb-2 text-sm font-medium">Обязательные навыки</p>
            <div className="flex flex-wrap gap-1.5">
              {(cat?.skills[n.spec] ?? []).map((s) => (
                <button
                  key={s}
                  onClick={() => toggleExtra(s)}
                  className={`rounded-md border px-2 py-0.5 text-xs ${extra.includes(s) ? "border-fsp bg-fsp text-white" : "border-slate-300 bg-white"}`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
          <p className="text-xs text-slate-500">Исходный запрос сохраняется: фильтры только сужают выдачу.</p>
          </div>
        </aside>

        <section className="space-y-3">
          {matches.isLoading ? (
            <Loading text="Подбираем кандидатов…" />
          ) : matches.error ? (
            <ErrorBox error={matches.error} />
          ) : !matches.data?.items.length ? (
            <Empty
              title="Никто не подошёл под фильтры"
              hint="Попробуйте включить соседние грейды или убрать обязательные навыки."
              action={filtersOn && <button className="btn-ghost" onClick={() => setParams({}, { replace: true })}>Сбросить фильтры</button>}
            />
          ) : (
            <>
              <p className={`text-sm text-slate-500 ${matches.isFetching ? "animate-pulse" : ""}`}>
                Найдено: {matches.data.total}. Сначала — лучшие по соответствию потребности.
              </p>
              {matches.data.items.map((m, i) => (
                <MatchCard key={m.candidate_id} rank={i + 1} m={m} highlight={needSkills} onInvite={() => setInviting(m.candidate)} />
              ))}
            </>
          )}
        </section>
      </div>

      {inviting && <InviteModal candidate={inviting} need={n} onClose={() => setInviting(null)} />}
    </div>
  );
}

function MatchCard({ m, rank, highlight, onInvite }: { m: S["MatchOut"]; rank: number; highlight: Set<string>; onInvite: () => void }) {
  const [open, setOpen] = useState(rank <= 1);
  const c = m.candidate;
  return (
    <article className="card">
      <div className="flex flex-col gap-3 sm:flex-row sm:gap-4">
        <div className="flex shrink-0 items-center gap-2 sm:w-16 sm:flex-col sm:gap-0">
          <div className="flex h-11 w-11 items-center justify-center rounded-full bg-fsp font-bold text-white sm:h-14 sm:w-14 sm:text-lg">{Math.round(m.score)}</div>
          <span className="text-xs text-slate-500 sm:mt-1">из 100</span>
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <Link to={`/employer/candidates/${c.id}`} className="font-bold hover:text-fsp">
              {c.full_name ?? `Кандидат №${c.id}`}
            </Link>
            <GradeBadge grade={c.grade} status={c.status} />
            {c.minor && <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-800">младше 18</span>}
            <StatusBadge status={c.invitation_status} />
          </div>
          <p className="text-sm text-slate-600">
            {[c.city, c.experience_years != null ? `стаж ${c.experience_years} г.` : null, c.work_format ? WORK_FORMAT[c.work_format] : null,
              c.salary_expect_from ? `ожидает от ${c.salary_expect_from.toLocaleString("ru-RU")} ₽` : null, c.percentile != null ? `тест лучше ${pct(c.percentile)} категории` : null]
              .filter(Boolean)
              .join(" · ")}
          </p>
          <SkillChips skills={c.skills} highlight={highlight} />
          <FspResults results={c.results} compact />
          <div className="flex flex-wrap items-center gap-3 pt-1">
            <button className="text-sm font-semibold text-fsp hover:underline" onClick={() => setOpen(!open)}>
              {open ? "Скрыть объяснение" : "Почему он здесь"}
            </button>
            <span className="text-sm text-slate-500">
              {c.contacts_hidden ? "🔒 Контакты откроются после принятия приглашения" : `📇 ${[c.email, c.phone, c.telegram].filter(Boolean).join(" · ")}`}
            </span>
            <div className="flex-1" />
            {c.invitation_status ? (
              <span className="text-sm text-slate-500">Приглашение отправлено</span>
            ) : (
              <button className="btn-accent" onClick={onInvite}>Пригласить</button>
            )}
          </div>
          {open && (
            <div className="-mx-2 mt-2 rounded-lg bg-slate-50 p-3 sm:mx-0 sm:p-4">
              <Explain items={m.explain} />
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
