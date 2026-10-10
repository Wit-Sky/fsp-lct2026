import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Empty, ErrorBox, Loading } from "../../components/States";
import { ApiError, get, post, type S } from "../../lib/api";
import { GRADE, dateTime } from "../../lib/format";
import { RATING } from "../employer/Tasks";

const KIND: Record<string, string> = { solve: "Решите задачу", approach: "Предложите подход" };

/** Регулярные задания от работодателей: ответ поддерживает профиль свежим, оценку видит кандидат. */
export default function CandidateTasks() {
  const q = useQuery({ queryKey: ["my-tasks"], queryFn: () => get<S["MyTasksOut"]>("/me/tasks") });
  if (q.isLoading) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const d = q.data!;
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Задания от работодателей</h1>
        <p className="text-slate-600">Короткие задачи по вашей специализации. Ответ держит профиль свежим — работодатели видят актуальный сигнал.</p>
      </div>
      {!d.offered.length ? (
        <Empty title="Новых заданий нет" hint="Они появятся, когда работодатели вашей специализации опубликуют задачи." />
      ) : (
        <div className="space-y-3">{d.offered.map((t) => <Offered key={t.id} t={t} />)}</div>
      )}
      {d.answered.length > 0 && (
        <div className="card">
          <h2 className="mb-3 font-bold">Мои ответы</h2>
          <ul className="space-y-3">
            {d.answered.map((a) => (
              <li key={a.id} className="border-t pt-3 first:border-0 first:pt-0">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <b>{a.task_title}</b>
                  <span className={`rounded-full px-2.5 py-0.5 text-xs ${a.rating == null ? "bg-slate-100 text-slate-600" : "bg-emerald-100 text-emerald-800"}`}>
                    {a.rating == null ? "ждёт оценки" : `оценка ${a.rating}/3 · ${RATING[a.rating]}`}
                  </span>
                </div>
                <p className="mt-1 line-clamp-3 whitespace-pre-line text-sm text-slate-600">{a.answer}</p>
                {a.feedback && <p className="mt-1 text-sm text-fsp-dark">💬 {a.feedback}</p>}
                <p className="mt-1 text-xs text-slate-500">{dateTime(a.created_at)}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Offered({ t }: { t: S["TaskOut"] }) {
  const qc = useQueryClient();
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const send = useMutation({
    mutationFn: () => post<S["TaskAnswerOut"]>(`/tasks/${t.id}/answer`, { answer }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-tasks"] }),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Не удалось отправить"),
  });
  return (
    <article className="card space-y-3">
      <div>
        <p className="text-sm text-slate-500">{t.company} · {KIND[t.kind] ?? t.kind}{t.grade ? ` · ${GRADE[t.grade]}` : ""}</p>
        <h2 className="font-bold">{t.title}</h2>
      </div>
      <p className="whitespace-pre-line text-slate-700">{t.text}</p>
      <textarea className="input min-h-28" placeholder="Ваше решение или подход (от 10 символов)" value={answer} onChange={(e) => setAnswer(e.target.value)} />
      {error && <p className="text-sm text-fsp-accent">{error}</p>}
      <div className="flex justify-end">
        <button className="btn-primary" disabled={answer.trim().length < 10 || send.isPending} onClick={() => { setError(null); send.mutate(); }}>Отправить ответ</button>
      </div>
    </article>
  );
}
