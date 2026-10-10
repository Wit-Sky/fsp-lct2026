import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { GradeBadge } from "../../components/Badges";
import { Empty, ErrorBox, Loading } from "../../components/States";
import { ApiError, get, post, type S } from "../../lib/api";
import { useCatalog } from "../../lib/catalog";
import { GRADE, SPEC, dateTime } from "../../lib/format";

const KIND: Record<string, string> = { solve: "решить", approach: "предложить подход" };
export const RATING = ["не решено", "частично", "хорошо", "отлично"];

/** Регулярные задания: короткая задача кандидатам категории; открытые ответы оценивает работодатель (0–3) — свежий сигнал в профиле. */
export default function EmployerTasks() {
  const q = useQuery({ queryKey: ["employer-tasks"], queryFn: () => get<S["TaskOut"][]>("/employer/tasks") });
  const [creating, setCreating] = useState(false);
  const [open, setOpen] = useState<number | null>(null);

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Регулярные задания</h1>
          <p className="text-slate-600">Короткая задача кандидатам категории: решить или предложить подход. Ответы — живой сигнал о кандидате.</p>
        </div>
        {!creating && <button className="btn-accent" onClick={() => setCreating(true)}>+ Новое задание</button>}
      </div>
      {creating && <TaskForm onDone={() => setCreating(false)} />}
      {q.isLoading ? <Loading /> : q.error ? <ErrorBox error={q.error} /> : !q.data?.length ? (
        !creating && <Empty title="Заданий пока нет" hint="Например: «Как бы вы спроектировали очередь уведомлений на 10 тыс. пользователей?»" />
      ) : (
        <div className="space-y-3">
          {q.data.map((t) => (
            <article key={t.id} className={`card ${t.active ? "" : "opacity-70"}`}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <h2 className="font-bold">{t.title}</h2>
                  <p className="text-sm text-slate-600">
                    {SPEC[t.spec]} · {t.grade ? GRADE[t.grade] : "все грейды"} · {KIND[t.kind] ?? t.kind} · {dateTime(t.created_at)}
                    {!t.active && " · снято"}
                  </p>
                </div>
                <button className="text-sm font-semibold text-fsp hover:underline" onClick={() => setOpen(open === t.id ? null : t.id)}>
                  Ответы: {t.answers} {open === t.id ? "▲" : "▼"}
                </button>
              </div>
              <p className="mt-2 whitespace-pre-line text-slate-700">{t.text}</p>
              {open === t.id && <Answers task={t} />}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function TaskForm({ onDone }: { onDone: () => void }) {
  const qc = useQueryClient();
  const { data: cat } = useCatalog();
  const [f, setF] = useState({ title: "", text: "", spec: "backend", grade: "", kind: "approach" });
  const [error, setError] = useState<string | null>(null);
  const create = useMutation({
    mutationFn: () => post<S["TaskOut"]>("/tasks", { ...f, grade: f.grade || null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["employer-tasks"] }); onDone(); },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Не удалось опубликовать"),
  });
  const submit = (e: FormEvent) => { e.preventDefault(); setError(null); create.mutate(); };
  return (
    <form className="card space-y-3 border-fsp/40" onSubmit={submit}>
      <div><label className="label" htmlFor="t-title">Заголовок</label><input id="t-title" className="input" required minLength={3} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} /></div>
      <div><label className="label" htmlFor="t-text">Условие</label><textarea id="t-text" className="input min-h-28" required minLength={10} value={f.text} onChange={(e) => setF({ ...f, text: e.target.value })} /></div>
      <div className="grid gap-3 sm:grid-cols-3">
        <select className="input" aria-label="Специализация" value={f.spec} onChange={(e) => setF({ ...f, spec: e.target.value })}>
          {cat?.specs.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
        </select>
        <select className="input" aria-label="Грейд" value={f.grade} onChange={(e) => setF({ ...f, grade: e.target.value })}>
          <option value="">Все грейды</option>
          {cat?.grades.map((g) => <option key={g.id} value={g.id}>{g.title}</option>)}
        </select>
        <select className="input" aria-label="Тип" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
          <option value="approach">Предложить подход</option>
          <option value="solve">Решить</option>
        </select>
      </div>
      {error && <p className="text-sm text-fsp-accent">{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" className="btn-ghost" onClick={onDone}>Отмена</button>
        <button className="btn-primary" disabled={create.isPending}>Опубликовать</button>
      </div>
    </form>
  );
}

function Answers({ task }: { task: S["TaskOut"] }) {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["task-answers", task.id], queryFn: () => get<S["TaskAnswerOut"][]>(`/tasks/${task.id}/answers`) });
  const close = useMutation({
    mutationFn: () => post<S["TaskOut"]>(`/tasks/${task.id}/close`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["employer-tasks"] }),
  });
  const review = useMutation({
    mutationFn: ({ id, rating }: { id: number; rating: number }) => post<S["TaskAnswerOut"]>(`/task-answers/${id}/review`, { rating }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["task-answers", task.id] }),
  });
  if (q.isLoading) return <p className="mt-3 text-sm text-slate-500">Загружаем ответы…</p>;
  return (
    <div className="mt-4 space-y-3 border-t pt-4">
      {!q.data?.length && <p className="text-sm text-slate-500">Ответов пока нет — задание предлагается кандидатам в их кабинете.</p>}
      {q.data?.map((a) => (
        <div key={a.id} className="rounded-lg bg-slate-50 p-3">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <b>{a.candidate_name ?? `Кандидат №${a.candidate_id}`}</b>
            {a.candidate_grade && <GradeBadge grade={a.candidate_grade} status="confirmed" />}
            <span className="text-slate-500">{dateTime(a.created_at)}</span>
          </div>
          <p className="mt-2 whitespace-pre-line text-sm">{a.answer}</p>
          <div className="mt-2 flex flex-wrap items-center gap-1.5 text-sm">
            <span className="text-slate-600">Оценка:</span>
            {RATING.map((r, i) => (
              <button key={r} disabled={review.isPending} onClick={() => review.mutate({ id: a.id, rating: i })}
                className={`rounded-md border px-2 py-0.5 ${a.rating === i ? "border-fsp bg-fsp text-white" : "border-slate-300 bg-white"}`}>
                {i} · {r}
              </button>
            ))}
          </div>
        </div>
      ))}
      {task.active && <button className="text-sm text-slate-500 hover:text-fsp-accent" onClick={() => close.mutate()}>Снять задание</button>}
    </div>
  );
}
