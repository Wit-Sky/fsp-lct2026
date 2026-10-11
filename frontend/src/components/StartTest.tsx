import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError, get, post, type S } from "../lib/api";
import { useCatalog } from "../lib/catalog";
import { dateTime } from "../lib/format";

/**
 * Выбор специализации и самостоятельный выбор грейда → старт теста.
 * Кулдаун показывается заранее по /me/category.can_retest; на грейд ниже после провала — сразу.
 */
export default function StartTest({ defaultSpec, defaultGrade, compact }: { defaultSpec?: string | null; defaultGrade?: string | null; compact?: boolean }) {
  const { data: cat } = useCatalog();
  const navigate = useNavigate();
  const category = useQuery({ queryKey: ["category"], queryFn: () => get<S["CategoryOut"]>("/me/category") });
  const [spec, setSpec] = useState(defaultSpec ?? category.data?.spec ?? "backend");
  const [grade, setGrade] = useState(defaultGrade ?? "junior");
  const [error, setError] = useState<string | null>(null);

  const start = useMutation({
    mutationFn: () => post<S["TestStateOut"]>("/tests/start", { spec, claimed_grade: grade }),
    onSuccess: (st) => navigate(`/candidate/test/${st.attempt_id}`),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Не удалось начать тест"),
  });

  const lockedUntil = category.data?.spec === spec ? category.data?.can_retest?.[grade] : null;
  const locked = lockedUntil && new Date(lockedUntil) > new Date();
  const active = category.data?.attempts.find((a) => !a.finished_at && a.spec === spec && a.claimed_grade === grade);

  return (
    <div className="space-y-4">
      <div>
        <span className="label">Специализация</span>
        <div className="flex flex-wrap gap-2">
          {cat?.specs.map((s) => (
            <button key={s.id} type="button" onClick={() => setSpec(s.id)}
              className={`btn border ${spec === s.id ? "border-fsp bg-fsp text-white" : "border-slate-300 bg-white"}`}>
              {s.title}
            </button>
          ))}
        </div>
      </div>
      <div>
        <span className="label">На какой грейд вы претендуете?</span>
        <div className="grid gap-2 sm:grid-cols-3">
          {cat?.grades.map((g) => (
            <button key={g.id} type="button" onClick={() => setGrade(g.id)}
              className={`rounded-lg border p-3 text-left ${grade === g.id ? "border-fsp bg-fsp/5 ring-1 ring-fsp" : "border-slate-300 bg-white"}`}>
              <span className="font-semibold">{g.title}</span>
              <span className="block text-xs text-slate-500">
                {g.id === "junior" ? "до 1–2 лет опыта, базовые задачи" : g.id === "middle" ? "самостоятельно ведёт задачи" : "архитектура, сложные случаи"}
              </span>
            </button>
          ))}
        </div>
        <p className="mt-2 text-sm text-slate-600">
          Грейд выбираете вы — тест его подтверждает. {!compact && "Не подтвердили — можно сразу пройти тест на уровень ниже; повтор того же или более высокого грейда — после паузы."}
        </p>
      </div>
      <div className="rounded-lg bg-fsp-tint/60 p-3 text-sm text-fsp-dark">
        ⏱ 10 заданий, 5 минут. У каждого кандидата свои варианты: числа, код и порядок ответов. Вернуться к заданию нельзя.
      </div>
      {locked && <p className="text-sm text-amber-700">Тест на этот грейд будет доступен {dateTime(lockedUntil)}. Можно выбрать грейд ниже.</p>}
      {error && <p className="text-sm text-fsp-accent">{error}</p>}
      <button className="btn-accent" disabled={start.isPending || !!locked} onClick={() => { setError(null); start.mutate(); }}>
        {start.isPending ? "Готовим задания…" : active ? "Продолжить попытку" : "Начать тест"}
      </button>
    </div>
  );
}
