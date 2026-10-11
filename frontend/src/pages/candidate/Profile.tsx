import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { FspResults } from "../../components/Badges";
import { ErrorBox, Loading } from "../../components/States";
import { ApiError, api, get, post, put, tokenStore, type S } from "../../lib/api";
import { useCatalog } from "../../lib/catalog";
import { WORK_FORMAT } from "../../lib/format";

const VISIBLE: [string, string][] = [
  ["full_name", "ФИО"], ["city", "Город"], ["birth_date", "Дата рождения"],
  ["about", "О себе"], ["experience_years", "Стаж"], ["results", "Результаты ФСП"],
];

export default function Profile() {
  const qc = useQueryClient();
  const { data: cat } = useCatalog();
  const [params, setParams] = useSearchParams();
  const q = useQuery({ queryKey: ["profile"], queryFn: () => get<S["ProfileOut"]>("/me/profile") });
  const results = useQuery({ queryKey: ["results"], queryFn: () => get<S["ResultsOut"]>("/me/results") });
  const [f, setF] = useState<Partial<S["ProfileIn"]>>({});
  const [msg, setMsg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const fspFlag = params.get("fsp");

  useEffect(() => {
    if (!q.data) return;
    const { user_id: _u, email: _e, minor: _m, published: _p, fsp_linked: _l, fsp_id: _i, fsp_skipped: _s, ...rest } = q.data;
    setF(rest as Partial<S["ProfileIn"]>);
  }, [q.data]);
  useEffect(() => {
    if (fspFlag) {
      qc.invalidateQueries({ queryKey: ["results"] });
      qc.invalidateQueries({ queryKey: ["profile"] });
    }
  }, [fspFlag, qc]);

  const save = useMutation({
    mutationFn: () => put<S["ProfileOut"]>("/me/profile", f),
    onSuccess: (p) => { qc.setQueryData(["profile"], p); setMsg(p.published ? "Сохранено. Профиль виден работодателям." : "Сохранено. Профиль скрыт: нужно согласие на обработку данных."); },
    onError: (e) => setMsg(e instanceof ApiError ? e.message : "Ошибка сохранения"),
  });
  const parse = useMutation({
    mutationFn: (file: File) => { const fd = new FormData(); fd.append("file", file); return api<S["ResumeDraft"]>("POST", "/me/resume/parse", fd); },
    onSuccess: (d) => {
      setF((prev) => ({
        ...prev,
        full_name: d.full_name || prev.full_name,
        phone: d.phone || prev.phone,
        telegram: d.telegram || prev.telegram,
        experience_years: d.experience_years ?? prev.experience_years,
        spec: (d.spec as S["ProfileIn"]["spec"]) || prev.spec,
        skills: d.skills.length ? d.skills : prev.skills,
      }));
      setMsg(`Из резюме распознано: ${[d.full_name && "ФИО", d.phone && "телефон", d.skills.length && `${d.skills.length} навыков`, d.experience_years != null && "стаж"].filter(Boolean).join(", ") || "немного"}. Проверьте и сохраните.`);
    },
    onError: (e) => setMsg(e instanceof ApiError ? e.message : "Не удалось разобрать PDF"),
  });
  const unlink = useMutation({
    mutationFn: () => api("DELETE", "/me/fsp"),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["results"] }); qc.invalidateQueries({ queryKey: ["profile"] }); },
  });
  const link = useMutation({
    mutationFn: () => post<S["FspStartOut"]>("/auth/fsp/start"),
    onSuccess: (data) => { window.location.assign(data.authorize_url); },
  });

  if (q.isPending) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const p = q.data!;
  const minor = f.birth_date ? (Date.now() - new Date(f.birth_date).getTime()) / (365.25 * 864e5) < 18 : p.minor;
  const field = (k: keyof S["ProfileIn"]) => ({
    value: (f[k] as string | number | null | undefined) ?? "",
    onChange: (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value || null }),
  });
  const skillPool = f.spec ? cat?.skills[f.spec] ?? [] : ((cat?.all_skills as string[] | undefined) ?? []);
  const toggleSkill = (s: string) => {
    const cur = new Set(f.skills ?? []);
    if (cur.has(s)) cur.delete(s); else cur.add(s);
    setF({ ...f, skills: [...cur] });
  };
  const downloadPdf = async () => {
    const t = tokenStore.get();
    const res = await fetch("/api/me/profile.pdf", { headers: t ? { Authorization: `Bearer ${t.access_token}` } : {} });
    if (!res.ok) return setMsg("Не удалось сформировать PDF");
    const url = URL.createObjectURL(await res.blob());
    const a = document.createElement("a");
    a.href = url; a.download = "profile.pdf"; a.click();
    URL.revokeObjectURL(url);
  };
  const submit = (e: FormEvent) => {
    e.preventDefault(); setMsg(null);
    save.mutate();
  };
  const fspResults = results.data?.sources?.fsp ?? [];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Профиль и резюме</h1>
          <p className="text-slate-600">{p.email} · {p.published ? "виден работодателям" : "скрыт от работодателей"}</p>
        </div>
        <div className="flex gap-2">
          <input ref={fileRef} type="file" accept="application/pdf" hidden onChange={(e) => e.target.files?.[0] && parse.mutate(e.target.files[0])} />
          <button className="btn-ghost" onClick={() => fileRef.current?.click()} disabled={parse.isPending}>{parse.isPending ? "Читаем PDF…" : "Загрузить PDF-резюме"}</button>
          <button className="btn-ghost" onClick={downloadPdf}>Скачать мой профиль PDF</button>
        </div>
      </div>

      <section id="fsp" className="card space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold">ФСП ID</h2>
          {p.fsp_linked ? (
            <div className="flex items-center gap-3 text-sm">
              <span className="rounded-full bg-emerald-100 px-3 py-1 text-emerald-800">Привязан: {p.fsp_id}</span>
              <button className="text-slate-500 hover:text-fsp-accent" onClick={() => unlink.mutate()}>Отвязать</button>
            </div>
          ) : (
            <button className="btn-primary" onClick={() => link.mutate()} disabled={link.isPending}>
              {link.isPending ? "Подключаем…" : "Войти через ФСП ID"}
            </button>
          )}
        </div>
        {link.error && <ErrorBox error={link.error} />}
        {fspFlag === "linked" && <p className="text-sm text-emerald-700">ФСП ID привязан, результаты подтянуты. <button className="underline" onClick={() => setParams({})}>ок</button></p>}
        {fspFlag === "conflict" && <p className="text-sm text-fsp-accent">Этот ФСП ID уже привязан к другому профилю.</p>}
        <FspResults results={fspResults} />
        <p className="text-xs text-slate-500">Результаты приходят из реестра ФСП и не редактируются вручную. Они поднимают вас внутри категории, но не меняют грейд.</p>
      </section>

      <form className="card space-y-4" onSubmit={submit}>
        <div className="grid gap-4 md:grid-cols-2">
          <div><label className="label" htmlFor="p-name">ФИО</label><input id="p-name" className="input" required {...field("full_name")} /></div>
          <div><label className="label" htmlFor="p-birth">Дата рождения</label><input id="p-birth" className="input" type="date" {...field("birth_date")} /></div>
          <div><label className="label" htmlFor="p-phone">Телефон</label><input id="p-phone" className="input" {...field("phone")} /></div>
          <div><label className="label" htmlFor="p-tg">Telegram</label><input id="p-tg" className="input" placeholder="@nick" {...field("telegram")} /></div>
          <div><label className="label" htmlFor="p-city">Город</label><input id="p-city" className="input" {...field("city")} /></div>
          <div><label className="label" htmlFor="p-exp">Стаж, лет</label><input id="p-exp" className="input" type="number" min={0} step={0.5} {...field("experience_years")} /></div>
          <div>
            <label className="label" htmlFor="p-wf">Формат работы</label>
            <select id="p-wf" className="input" {...field("work_format")}>
              <option value="">Не важно</option>
              {Object.entries(WORK_FORMAT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          <div><label className="label" htmlFor="p-sal">Ожидания по зарплате от, ₽</label><input id="p-sal" className="input" type="number" min={0} {...field("salary_expect_from")} /></div>
        </div>
        <div>
          <label className="label" htmlFor="p-spec">Специализация</label>
          <select id="p-spec" className="input max-w-xs" {...field("spec")}>
            <option value="">Выберите</option>
            {cat?.specs.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
          </select>
        </div>
        <div>
          <span className="label">Стек</span>
          <div className="flex flex-wrap gap-1.5">
            {skillPool.map((s) => (
              <button type="button" key={s} onClick={() => toggleSkill(s)}
                className={`rounded-md border px-2 py-1 text-sm ${(f.skills ?? []).includes(s) ? "border-fsp bg-fsp text-white" : "border-slate-300 bg-white"}`}>{s}</button>
            ))}
          </div>
        </div>
        <div><label className="label" htmlFor="p-about">О себе (роли, софт-скиллы)</label><textarea id="p-about" className="input min-h-20" {...field("about")} /></div>

        <fieldset className="rounded-lg border border-slate-200 p-4">
          <legend className="px-1 text-sm font-semibold">Что видно работодателю</legend>
          <div className="flex flex-wrap gap-x-5 gap-y-2 text-sm">
            {VISIBLE.map(([k, label]) => (
              <label key={k} className="flex items-center gap-2">
                <input type="checkbox" checked={f.visible_fields?.[k] ?? true}
                  onChange={(e) => setF({ ...f, visible_fields: { ...(f.visible_fields ?? {}), [k]: e.target.checked } })} />
                {label}
              </label>
            ))}
          </div>
          <p className="mt-2 text-xs text-slate-500">Контакты (телефон, Telegram, email) работодатель увидит только после того, как вы примете его приглашение или откликнетесь сами.</p>
        </fieldset>

        <label className="flex items-start gap-2 text-sm">
          <input type="checkbox" className="mt-0.5" checked={!!f.consent_pd} onChange={(e) => setF({ ...f, consent_pd: e.target.checked })} />
          <span>Согласен(на) на обработку и публикацию данных профиля для работодателей платформы (152-ФЗ). Без согласия профиль не показывается в подборках.</span>
        </label>
        {minor && (
          <label className="flex items-start gap-2 rounded-lg bg-sky-50 p-3 text-sm text-sky-900">
            <input type="checkbox" className="mt-0.5" checked={!!f.parent_consent} onChange={(e) => setF({ ...f, parent_consent: e.target.checked })} />
            <span>Вам меньше 18 лет: нужно согласие родителя или законного представителя на обработку данных. Подтверждаю, что оно получено.</span>
          </label>
        )}
        <div className="flex flex-wrap items-center gap-3">
          <button className="btn-primary" disabled={save.isPending}>Сохранить профиль</button>
          {msg && <span className="text-sm text-slate-600">{msg}</span>}
        </div>
      </form>
    </div>
  );
}
