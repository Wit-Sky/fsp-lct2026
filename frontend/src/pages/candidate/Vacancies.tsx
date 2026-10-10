import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { StatusBadge } from "../../components/Badges";
import { Empty, ErrorBox, Loading } from "../../components/States";
import { ApiError, get, post, type S } from "../../lib/api";
import { GRADE, SPEC, WORK_FORMAT, money } from "../../lib/format";

/** Дополнительный сценарий: кандидат, пока без приглашений, может откликнуться сам — тогда контакты откроются этой компании. */
export default function Vacancies() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<"list" | "mine">("list");
  const list = useQuery({ queryKey: ["vacancies"], queryFn: () => get<S["VacancyOut"][]>("/vacancies") });
  const mine = useQuery({ queryKey: ["my-applications"], queryFn: () => get<S["ApplicationOut"][]>("/me/applications") });
  const [err, setErr] = useState<string | null>(null);
  const apply = useMutation({
    mutationFn: (id: number) => post<S["ApplicationOut"]>(`/vacancies/${id}/apply`, {}),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["vacancies"] }); qc.invalidateQueries({ queryKey: ["my-applications"] }); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Не удалось откликнуться"),
  });

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Вакансии</h1>
          <p className="text-slate-600">Главный путь — приглашения от работодателей. Здесь можно проявить инициативу самому.</p>
        </div>
        <div className="flex rounded-lg border border-slate-300 bg-white p-1 text-sm">
          <button className={`rounded-md px-3 py-1 ${tab === "list" ? "bg-fsp text-white" : ""}`} onClick={() => setTab("list")}>Открытые</button>
          <button className={`rounded-md px-3 py-1 ${tab === "mine" ? "bg-fsp text-white" : ""}`} onClick={() => setTab("mine")}>Мои отклики</button>
        </div>
      </div>
      {err && <p className="text-sm text-fsp-accent">{err}</p>}
      {tab === "list" ? (
        list.isLoading ? <Loading /> : list.error ? <ErrorBox error={list.error} /> : !list.data?.length ? <Empty title="Открытых вакансий пока нет" /> : (
          <div className="grid gap-3 md:grid-cols-2">
            {list.data.map((v) => (
              <article key={v.id} className="card space-y-2">
                <h2 className="font-bold">{v.title}</h2>
                <p className="text-sm text-slate-600">{v.company} · {SPEC[v.spec]} · {GRADE[v.grade]}{v.work_format ? ` · ${WORK_FORMAT[v.work_format]}` : ""}</p>
                <p className="font-semibold text-fsp">{money(v.salary_from, v.salary_to, v.salary_type)}</p>
                {v.description && <p className="text-sm text-slate-700">{v.description}</p>}
                <p className="text-xs text-slate-500">{v.skills.map((s) => String((s as { name: string }).name)).join(" · ")}</p>
                <div className="flex justify-end">
                  {v.applied ? <span className="text-sm text-emerald-700">Вы откликнулись</span> :
                    <button className="btn-primary" disabled={apply.isPending} onClick={() => { setErr(null); apply.mutate(v.id); }}>Откликнуться</button>}
                </div>
              </article>
            ))}
          </div>
        )
      ) : mine.isLoading ? <Loading /> : !mine.data?.length ? <Empty title="Откликов пока нет" /> : (
        <div className="space-y-2">
          {mine.data.map((a) => (
            <div key={a.id} className="card flex flex-wrap items-center justify-between gap-2">
              <div><b>{a.need_title}</b> <span className="text-slate-600">· {a.company}</span></div>
              <div className="flex items-center gap-3"><span className="text-sm">{money(a.salary_from, a.salary_to, a.salary_type)}</span><StatusBadge status={a.status} /></div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
