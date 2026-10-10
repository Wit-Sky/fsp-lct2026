import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ErrorBox, Loading } from "../../components/States";
import { ApiError, get, post, type S } from "../../lib/api";
import { GRADE, SPEC } from "../../lib/format";

/** Прохождение теста: задания по одному, без возврата назад; таймер — по дедлайну с сервера. */
export default function TestRun() {
  const id = Number(useParams().attemptId);
  const navigate = useNavigate();
  const initial = useQuery({ queryKey: ["attempt", id], queryFn: () => get<S["TestStateOut"]>(`/tests/${id}`), gcTime: 0 });
  const [state, setState] = useState<S["TestStateOut"] | null>(null);
  const [answer, setAnswer] = useState<unknown>(null);
  const [order, setOrder] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now());

  useEffect(() => { if (initial.data) setState(initial.data); }, [initial.data]);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    setAnswer(null);
    setOrder(state?.item?.kind === "order" ? [...(state.item.options ?? [])] : []);
  }, [state?.item?.item_id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (state?.finished) navigate(`/candidate/result/${id}`, { replace: true }); }, [state?.finished, id, navigate]);

  const submit = useMutation({
    mutationFn: (a: unknown) => post<S["TestStateOut"]>(`/tests/${id}/answer`, { item_id: state!.item!.item_id, answer: a }),
    onSuccess: (st) => { setError(null); setState(st); },
    onError: async (e) => {
      if (e instanceof ApiError && (e.code === "item_not_current" || e.code === "finished")) {
        const st = await get<S["TestStateOut"]>(`/tests/${id}`);
        setState(st);
      } else setError(e instanceof ApiError ? e.message : "Не удалось отправить ответ");
    },
  });

  if (initial.isLoading || !state) return <Loading text="Готовим задания…" />;
  if (initial.error) return <ErrorBox error={initial.error} />;
  const item = state.item;
  const left = Math.max(0, Math.floor((new Date(state.deadline).getTime() - now) / 1000));
  const mm = String(Math.floor(left / 60)).padStart(1, "0");
  const ss = String(left % 60).padStart(2, "0");

  if (!item) return <Loading text="Считаем результат…" />;

  const value = item.kind === "order" ? order : answer;
  const ready = item.kind === "order" ? true : answer !== null && answer !== "";
  const move = (i: number, d: number) => {
    const j = i + d;
    if (j < 0 || j >= order.length) return;
    const next = [...order];
    [next[i], next[j]] = [next[j], next[i]];
    setOrder(next);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-600">{SPEC[state.spec]} · тест на {GRADE[state.claimed_grade]}</p>
        <span className={`rounded-full px-3 py-1 font-mono text-sm font-semibold ${left < 60 ? "bg-rose-100 text-rose-700" : "bg-fsp/10 text-fsp"}`}>
          ⏱ {mm}:{ss}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-slate-200">
        <div className="h-full bg-fsp transition-all" style={{ width: `${(state.answered / state.total) * 100}%` }} />
      </div>

      <div className="card space-y-4">
        <p className="text-sm text-slate-500">Задание {item.no} из {item.total} · тема: {item.topic}</p>
        <div className="text-lg font-medium">
          {item.text.split("\n").map((line, i) =>
            /\||^-{3,}/.test(line) ? (
              <pre key={i} className="font-mono text-sm leading-6">{line}</pre>
            ) : (
              <p key={i} className={line ? "" : "h-3"}>{line}</p>
            ),
          )}
        </div>
        {item.code && <pre className="overflow-x-auto rounded-lg bg-fsp-ink p-4 text-sm text-slate-100"><code>{item.code}</code></pre>}

        {item.kind === "single" && (
          <div className="space-y-2">
            {item.options?.map((o, i) => (
              <label key={i} className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 ${answer === o ? "border-fsp bg-fsp/5" : "border-slate-200 hover:border-fsp/50"}`}>
                <input type="radio" name="opt" className="mt-1" checked={answer === o} onChange={() => setAnswer(o)} />
                <span className="whitespace-pre-line">{o}</span>
              </label>
            ))}
          </div>
        )}
        {item.kind === "number" && (
          <div className="max-w-xs">
            <label className="label" htmlFor="num">Ваш ответ (число)</label>
            <input id="num" className="input" inputMode="decimal" autoFocus value={(answer as string) ?? ""}
              onChange={(e) => setAnswer(e.target.value.replace(",", "."))} />
          </div>
        )}
        {item.kind === "order" && (
          <div className="space-y-2">
            <p className="text-sm text-slate-600">Расставьте в правильном порядке стрелками.</p>
            {order.map((o, i) => (
              <div key={o} className="flex items-center gap-2 rounded-lg border border-slate-200 p-2">
                <span className="w-6 text-center font-semibold text-fsp">{i + 1}</span>
                <span className="flex-1">{o}</span>
                <button type="button" aria-label="Выше" className="btn-ghost px-2 py-1" disabled={i === 0} onClick={() => move(i, -1)}>↑</button>
                <button type="button" aria-label="Ниже" className="btn-ghost px-2 py-1" disabled={i === order.length - 1} onClick={() => move(i, 1)}>↓</button>
              </div>
            ))}
          </div>
        )}

        {error && <p className="text-sm text-fsp-accent">{error}</p>}
        <div className="flex justify-end">
          <button className="btn-primary" disabled={!ready || submit.isPending}
            onClick={() => submit.mutate(item.kind === "number" ? Number(value) : value)}>
            {item.no === item.total ? "Завершить тест" : "Ответить и дальше →"}
          </button>
        </div>
      </div>
      <p className="text-center text-xs text-slate-500">Варианты заданий уникальны для вас: пересказ чужих ответов не поможет.</p>
    </div>
  );
}
