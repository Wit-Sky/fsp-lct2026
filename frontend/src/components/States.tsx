import type { ReactNode } from "react";
import { ApiError } from "../lib/api";

export const Loading = ({ text = "Загружаем…" }: { text?: string }) => (
  <div className="card animate-pulse text-slate-500">{text}</div>
);

export const ErrorBox = ({ error }: { error: unknown }) => (
  <div className="card border-rose-200 bg-rose-50 text-rose-800">
    {error instanceof ApiError ? error.message : "Что-то пошло не так. Обновите страницу."}
  </div>
);

export const Empty = ({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) => (
  <div className="card text-center">
    <p className="font-semibold">{title}</p>
    {hint && <p className="mt-1 text-sm text-slate-600">{hint}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);
