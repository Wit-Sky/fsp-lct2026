import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { StatusBadge } from "../../components/Badges";
import { Empty, ErrorBox, Loading } from "../../components/States";
import { get, post, type S } from "../../lib/api";
import { dateTime, money } from "../../lib/format";

/** Входящие приглашения: компания, предложение и зарплата видны сразу; принять → работодатель получает контакты. */
export default function CandidateInvitations() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["my-invitations"], queryFn: () => get<S["InvitationOut"][]>("/me/invitations"), refetchInterval: 15000 });
  const [open, setOpen] = useState<number | null>(null);
  const view = useMutation({
    mutationFn: (id: number) => get<S["InvitationOut"]>(`/invitations/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-invitations"] }),
  });
  const decide = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "accept" | "decline" }) => post<S["InvitationOut"]>(`/invitations/${id}/${action}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-invitations"] }),
  });

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Приглашения</h1>
        <p className="text-slate-600">Работодатели сами выходят на вас. Условия и зарплата — до начала общения.</p>
      </div>
      {q.isLoading ? <Loading /> : q.error ? <ErrorBox error={q.error} /> : !q.data?.length ? (
        <Empty title="Приглашений пока нет" hint="Подтверждённый грейд и привязанный ФСП ID поднимают вас в подборках. Пока ждёте — посмотрите открытые вакансии." />
      ) : (
        <div className="space-y-3">
          {q.data.map((i) => {
            const expanded = open === i.id;
            return (
              <article key={i.id} className={`card ${i.status === "sent" ? "border-fsp-accent" : ""}`}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-bold">{i.company}</h2>
                      <StatusBadge status={i.status} />
                    </div>
                    <p className="text-sm text-slate-600">{i.need_title ?? "Персональное предложение"} · {dateTime(i.created_at)}</p>
                  </div>
                  <p className="text-lg font-bold text-fsp">{money(i.salary_from, i.salary_to, i.salary_type)}</p>
                </div>
                {expanded ? (
                  <div className="mt-3 space-y-3">
                    <p className="whitespace-pre-line text-slate-700">{i.message}</p>
                    <p className="text-sm text-slate-600">Связь: {i.contact_method}</p>
                    {(i.status === "sent" || i.status === "viewed") && (
                      <div className="flex flex-wrap gap-2">
                        <button className="btn-accent" disabled={decide.isPending} onClick={() => decide.mutate({ id: i.id, action: "accept" })}>Принять — работодатель увидит мои контакты</button>
                        <button className="btn-ghost" disabled={decide.isPending} onClick={() => decide.mutate({ id: i.id, action: "decline" })}>Отклонить</button>
                      </div>
                    )}
                    {i.status === "accepted" && <p className="text-sm text-emerald-700">Вы приняли приглашение — работодатель видит ваши контакты и свяжется с вами.</p>}
                  </div>
                ) : (
                  <button className="mt-2 text-sm font-semibold text-fsp hover:underline"
                    onClick={() => { setOpen(i.id); if (i.status === "sent") view.mutate(i.id); }}>
                    Открыть предложение
                  </button>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
