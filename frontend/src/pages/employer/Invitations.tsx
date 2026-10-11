import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { StatusBadge } from "../../components/Badges";
import { Empty, ErrorBox, Loading } from "../../components/States";
import { get, type S } from "../../lib/api";
import { dateTime, money } from "../../lib/format";

export default function EmployerInvitations() {
  const q = useQuery({
    queryKey: ["employer-invitations"],
    queryFn: () => get<S["InvitationOut"][]>("/employer/invitations"),
    refetchInterval: 15000,
  });
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Мои приглашения</h1>
        <p className="text-slate-600">Статусы обновляются сами. Когда кандидат принимает приглашение, здесь появляются его контакты.</p>
      </div>
      {q.isPending ? <Loading /> : q.error ? <ErrorBox error={q.error} /> : !q.data?.length ? (
        <Empty title="Вы ещё никого не пригласили" hint="Откройте подборку по потребности и нажмите «Пригласить»."
          action={<Link className="btn-primary" to="/employer">К подбору</Link>} />
      ) : (
        <div className="space-y-3">
          {q.data.map((i) => (
            <article key={i.id} className="card flex flex-wrap items-start gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <Link to={`/employer/candidates/${i.candidate_id}`} className="font-bold hover:text-fsp">
                    {i.candidate_name ?? `Кандидат №${i.candidate_id}`}
                  </Link>
                  <StatusBadge status={i.status} />
                </div>
                <p className="text-sm text-slate-600">
                  {i.need_title ?? "Без привязки к вакансии"} · {money(i.salary_from, i.salary_to, i.salary_type)}
                </p>
                <p className="mt-1 text-xs text-slate-500">Отправлено {dateTime(i.created_at)} · обновлено {dateTime(i.updated_at)}</p>
              </div>
              <div className="text-sm">
                {i.candidate_contacts ? (
                  <div className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-900">
                    📇 {Object.values(i.candidate_contacts).filter(Boolean).join(" · ")}
                  </div>
                ) : (
                  <span className="text-slate-500">🔒 контакты после принятия</span>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
