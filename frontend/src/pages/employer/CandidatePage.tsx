import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { FspResults, GradeBadge, SkillChips, SpecBadge, StatusBadge } from "../../components/Badges";
import InviteModal from "../../components/InviteModal";
import { ErrorBox, Loading } from "../../components/States";
import { get, type S } from "../../lib/api";
import { WORK_FORMAT, date, pct, decimal } from "../../lib/format";

export default function CandidatePage() {
  const id = Number(useParams().candId);
  const navigate = useNavigate();
  const [inviting, setInviting] = useState(false);
  const q = useQuery({ queryKey: ["candidate", id], queryFn: () => get<S["CandidateCard"]>(`/candidates/${id}`) });
  if (q.isPending) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const c = q.data!;

  const rows: [string, string][] = [
    ["Город", c.city ?? "—"],
    ["Стаж", c.experience_years != null ? `${c.experience_years} г.` : "—"],
    ["Формат работы", c.work_format ? WORK_FORMAT[c.work_format] : "—"],
    ["Ожидания", c.salary_expect_from ? `от ${c.salary_expect_from.toLocaleString("ru-RU")} ₽` : "—"],
    ["Тест", c.theta != null ? `θ = ${decimal(c.theta)}, лучше ${pct(c.percentile)} категории, ${date(c.tested_at)}` : "не проходил"],
  ];

  return (
    <div className="space-y-5">
      <button className="text-sm text-fsp hover:underline" onClick={() => navigate(-1)}>← Назад</button>
      <div className="card space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold">{c.full_name ?? `Кандидат №${c.id}`}</h1>
          <SpecBadge spec={c.spec} />
          <GradeBadge grade={c.grade} status={c.status} />
          {c.minor && <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-800">младше 18 — нужно согласие родителя</span>}
          <StatusBadge status={c.invitation_status} />
        </div>
        {c.about && <p className="text-slate-700">{c.about}</p>}
        <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
          {rows.map(([k, v]) => (
            <div key={k}>
              <dt className="text-xs uppercase tracking-wide text-slate-500">{k}</dt>
              <dd>{v}</dd>
            </div>
          ))}
        </dl>
        <div>
          <h2 className="mb-2 font-semibold">Стек</h2>
          <SkillChips skills={c.skills} />
        </div>
        <div>
          <h2 className="mb-2 font-semibold">Подтверждённые результаты ФСП</h2>
          <FspResults results={c.results} />
        </div>
        <div className="rounded-lg bg-slate-50 p-4">
          <h2 className="font-semibold">Контакты</h2>
          {c.contacts_hidden ? (
            <p className="text-sm text-slate-600">🔒 Откроются, когда кандидат примет ваше приглашение или сам откликнется на вакансию.</p>
          ) : (
            <p className="text-sm">{[c.email, c.phone, c.telegram].filter(Boolean).join(" · ")}</p>
          )}
        </div>
        {!c.invitation_status && <button className="btn-accent" onClick={() => setInviting(true)}>Пригласить</button>}
      </div>
      {inviting && <InviteModal candidate={c} onClose={() => setInviting(false)} onSent={() => q.refetch()} />}
    </div>
  );
}
