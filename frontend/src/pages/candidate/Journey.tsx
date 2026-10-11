import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { GradeBadge, SpecBadge } from "../../components/Badges";
import StartTest from "../../components/StartTest";
import { ErrorBox, Loading } from "../../components/States";
import { get, type S } from "../../lib/api";
import { pct } from "../../lib/format";

export const FSP_SKIP_KEY = "fsp_skip";
const skipped = () => {
  try { return localStorage.getItem(FSP_SKIP_KEY) === "1"; } catch { return false; }
};

/** Обязательный путь кандидата: профиль → FSP ID → специализация и грейд → тест → категория. */
export default function Journey() {
  const profile = useQuery({ queryKey: ["profile"], queryFn: () => get<S["ProfileOut"]>("/me/profile") });
  const category = useQuery({ queryKey: ["category"], queryFn: () => get<S["CategoryOut"]>("/me/category") });
  const invites = useQuery({ queryKey: ["my-invitations"], queryFn: () => get<S["InvitationOut"][]>("/me/invitations") });
  if (profile.isPending || category.isPending) return <Loading />;
  if (!profile.data || !category.data) return <ErrorBox error={profile.error ?? category.error} />;
  const p = profile.data;
  const c = category.data;

  const steps = [
    { key: "profile", title: "Профиль", done: !!p.full_name && p.consent_pd && (!p.minor || p.parent_consent) },
    { key: "fsp", title: "ФСП ID", done: p.fsp_linked || skipped() },
    { key: "test", title: "Специализация, грейд и тест", done: c.status !== "none" },
    { key: "category", title: "Категория", done: c.status === "confirmed" },
  ];
  const current = steps.find((s) => !s.done)?.key ?? "done";
  const newInvites = invites.data?.filter((i) => i.status === "sent").length ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Мой путь{p.full_name ? `, ${p.full_name.split(" ")[1] ?? p.full_name}` : ""}</h1>
        <p className="text-slate-600">Пройдите шаги — и работодатели увидят вас в своей категории и смогут пригласить.</p>
      </div>

      <ol className="grid gap-2 sm:grid-cols-4">
        {steps.map((s, i) => (
          <li key={s.key} className={`rounded-lg border p-3 text-sm ${s.done ? "border-emerald-300 bg-emerald-50" : s.key === current ? "border-fsp bg-white ring-1 ring-fsp" : "border-slate-200 bg-white text-slate-500"}`}>
            <span className="font-semibold">{s.done ? "✓" : i + 1}. {s.title}</span>
          </li>
        ))}
      </ol>

      {newInvites > 0 && (
        <Link to="/candidate/invitations" className="card block border-fsp-accent bg-fsp-tint/40">
          <b>📩 Новых приглашений: {newInvites}.</b> Условия и зарплата — внутри.
        </Link>
      )}

      {current === "profile" && (
        <div className="card space-y-3">
          <h2 className="text-lg font-bold">Шаг 1. Заполните профиль</h2>
          <p className="text-slate-600">ФИО, контакты, стек и согласие на обработку данных. Можно загрузить PDF-резюме — поля заполнятся сами.</p>
          <Link className="btn-primary" to="/candidate/profile">Заполнить профиль</Link>
        </div>
      )}
      {current === "fsp" && (
        <div className="card space-y-3">
          <h2 className="text-lg font-bold">Шаг 2. Привяжите ФСП ID</h2>
          <p className="text-slate-600">Результаты соревнований ФСП подтягиваются автоматически и поднимают вас внутри категории. На грейд они не влияют.</p>
          <div className="flex flex-wrap gap-2">
            <Link className="btn-primary" to="/candidate/profile#fsp">Привязать ФСП ID</Link>
            <button className="btn-ghost" onClick={() => { try { localStorage.setItem(FSP_SKIP_KEY, "1"); } catch { /* */ } profile.refetch(); }}>
              У меня нет истории ФСП
            </button>
          </div>
        </div>
      )}
      {current === "test" && (
        <div className="card space-y-3">
          <h2 className="text-lg font-bold">Шаг 3. Выберите специализацию и грейд</h2>
          <StartTest defaultSpec={p.spec} />
        </div>
      )}
      {(current === "category" || current === "done") && (
        <div className="card space-y-3">
          <h2 className="text-lg font-bold">{c.status === "confirmed" ? "Вы в категории" : "Грейд пока не подтверждён"}</h2>
          <div className="flex flex-wrap items-center gap-2">
            <SpecBadge spec={c.spec} />
            <GradeBadge grade={c.grade} status={c.status} />
            {c.percentile != null && <span className="text-sm text-slate-600">тест лучше {pct(c.percentile)} категории</span>}
          </div>
          <p className="text-slate-600">
            {c.status === "confirmed"
              ? "Работодатели видят вас в подборке своей категории. Приглашения придут сюда с зарплатой и условиями."
              : "Работодатели видят заявленный грейд с пометкой «не подтверждён» — ниже в выдаче. Можно сразу пройти тест на уровень ниже."}
          </p>
          <Link className="btn-primary" to="/candidate/category">Категория и попытки</Link>
        </div>
      )}
    </div>
  );
}
