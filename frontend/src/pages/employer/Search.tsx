import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { FspResults, GradeBadge, SkillChips, SpecBadge, StatusBadge } from "../../components/Badges";
import InviteModal from "../../components/InviteModal";
import { Empty, ErrorBox, Loading } from "../../components/States";
import { get, type S } from "../../lib/api";
import { useCatalog } from "../../lib/catalog";
import { pct } from "../../lib/format";

/** Поиск по всему банку кандидатов: специализация, грейд, статус, стек, наличие ФСП. */
export default function Search() {
  const { data: cat } = useCatalog();
  const [params, setParams] = useSearchParams();
  const [inviting, setInviting] = useState<S["CandidateCard"] | null>(null);
  const spec = params.get("spec") ?? "";
  const skills = (params.get("skills") ?? "").split(",").filter(Boolean);

  const qs = new URLSearchParams();
  for (const k of ["spec", "grade", "status", "fsp", "q"]) if (params.get(k)) qs.set(k, params.get(k)!);
  if (skills.length) qs.set("skills", skills.join(","));
  qs.set("limit", "60");
  const list = useQuery({
    queryKey: ["candidates", qs.toString()],
    queryFn: () => get<S["CandidateCard"][]>(`/candidates?${qs}`),
    placeholderData: keepPreviousData,
  });

  const set = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    if (k === "spec") next.delete("skills");
    setParams(next, { replace: true });
  };
  const toggleSkill = (s: string) => {
    const st = new Set(skills);
    if (st.has(s)) st.delete(s);
    else st.add(s);
    set("skills", [...st].join(","));
  };
  const hl = new Set(skills.map((s) => s.toLowerCase()));
  const skillPool = spec ? cat?.skills[spec] ?? [] : ((cat?.all_skills as string[] | undefined) ?? []);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">База кандидатов</h1>
        <p className="text-slate-600">Вся база с фильтрами. Подтверждённые грейды — выше, контакты скрыты до принятия приглашения.</p>
      </div>

      <div className="card grid gap-3 md:grid-cols-6">
        <input className="input md:col-span-2" placeholder="Имя, город, о себе" defaultValue={params.get("q") ?? ""}
          onKeyDown={(e) => e.key === "Enter" && set("q", (e.target as HTMLInputElement).value)}
          onBlur={(e) => set("q", e.target.value)} />
        <select className="input" aria-label="Специализация" value={spec} onChange={(e) => set("spec", e.target.value)}>
          <option value="">Все специализации</option>
          {cat?.specs.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
        </select>
        <select className="input" aria-label="Грейд" value={params.get("grade") ?? ""} onChange={(e) => set("grade", e.target.value)}>
          <option value="">Любой грейд</option>
          {cat?.grades.map((g) => <option key={g.id} value={g.id}>{g.title}</option>)}
        </select>
        <>
          <select className="input" aria-label="Статус грейда" value={params.get("status") ?? ""} onChange={(e) => set("status", e.target.value)}>
            <option value="">Любой статус</option>
            <option value="confirmed">Подтверждён</option>
            <option value="unconfirmed">Не подтверждён</option>
          </select>
          <select className="input" aria-label="ФСП" value={params.get("fsp") ?? ""} onChange={(e) => set("fsp", e.target.value)}>
            <option value="">ФСП: все</option>
            <option value="true">с ФСП</option>
            <option value="false">без ФСП</option>
          </select>
        </>
        <div className="flex flex-wrap gap-1.5 md:col-span-6">
          {skillPool.map((s) => (
            <button key={s} onClick={() => toggleSkill(s)}
              className={`rounded-md border px-2 py-0.5 text-xs ${skills.includes(s) ? "border-fsp bg-fsp text-white" : "border-slate-300 bg-white"}`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {list.isLoading ? <Loading /> : list.error ? <ErrorBox error={list.error} /> : !list.data?.length ? (
        <Empty title="Никого не нашли" hint="Ослабьте фильтры." />
      ) : (
        <div className={`grid gap-3 md:grid-cols-2 ${list.isFetching ? "opacity-70" : ""}`}>
          {list.data.map((c) => (
            <article key={c.id} className="card space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Link to={`/employer/candidates/${c.id}`} className="font-bold hover:text-fsp">{c.full_name ?? `Кандидат №${c.id}`}</Link>
                <SpecBadge spec={c.spec} />
                <GradeBadge grade={c.grade} status={c.status} />
                <StatusBadge status={c.invitation_status} />
              </div>
              <p className="text-sm text-slate-600">
                {[c.city, c.experience_years != null ? `стаж ${c.experience_years} г.` : null, c.percentile != null ? `тест лучше ${pct(c.percentile)} категории` : null].filter(Boolean).join(" · ")}
              </p>
              <SkillChips skills={c.skills} highlight={hl} />
              <FspResults results={c.results} compact />
              <div className="flex justify-end">
                {!c.invitation_status && <button className="btn-ghost text-sm" onClick={() => setInviting(c)}>Пригласить</button>}
              </div>
            </article>
          ))}
        </div>
      )}
      {inviting && <InviteModal candidate={inviting} onClose={() => setInviting(null)} />}
    </div>
  );
}
