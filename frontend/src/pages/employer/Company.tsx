import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { ErrorBox, Loading } from "../../components/States";
import { ApiError, get, put, type S } from "../../lib/api";

export default function Company() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["employer"], queryFn: () => get<S["EmployerOut"]>("/employer") });
  const [form, setForm] = useState<S["EmployerIn"]>({});
  const [msg, setMsg] = useState<string | null>(null);
  useEffect(() => {
    if (q.data) setForm({ name: q.data.name, inn: q.data.inn, field: q.data.field, description: q.data.description, contacts: q.data.contacts });
  }, [q.data]);
  const save = useMutation({
    mutationFn: () => put<S["EmployerOut"]>("/employer", { ...form, inn: form.inn || null }),
    onSuccess: () => {
      setMsg("Сохранено");
      qc.invalidateQueries({ queryKey: ["employer"] });
    },
    onError: (e) => setMsg(e instanceof ApiError ? e.message : "Ошибка сохранения"),
  });
  if (q.isPending) return <Loading />;
  if (q.error) return <ErrorBox error={q.error} />;
  const f = (k: keyof S["EmployerIn"]) => ({
    value: (form[k] as string | null | undefined) ?? "",
    onChange: (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value }),
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    setMsg(null);
    save.mutate();
  };
  return (
    <form className="card max-w-2xl space-y-4" onSubmit={submit}>
      <h1 className="text-2xl font-bold">Профиль компании</h1>
      <div><label className="label" htmlFor="c-name">Название</label><input id="c-name" className="input" required {...f("name")} /></div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div><label className="label" htmlFor="c-field">Направление деятельности</label><input id="c-field" className="input" {...f("field")} /></div>
        <div><label className="label" htmlFor="c-inn">ИНН (необязательно, метка доверия)</label><input id="c-inn" className="input" inputMode="numeric" {...f("inn")} /></div>
      </div>
      <div><label className="label" htmlFor="c-desc">О компании</label><textarea id="c-desc" className="input min-h-24" {...f("description")} /></div>
      <div><label className="label" htmlFor="c-cont">Контактные данные</label><input id="c-cont" className="input" {...f("contacts")} /></div>
      <div className="flex items-center gap-3">
        <button className="btn-primary" disabled={save.isPending}>Сохранить</button>
        {msg && <span className="text-sm text-slate-600">{msg}</span>}
      </div>
    </form>
  );
}
