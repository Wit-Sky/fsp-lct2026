import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { ApiError, post, type S } from "../lib/api";
import { SALARY_TYPE } from "../lib/format";

type Props = {
  candidate: { id: number; full_name?: string | null };
  need?: S["NeedOut"] | null;
  onClose: () => void;
  onSent?: (inv: S["InvitationOut"]) => void;
};

/** Адресное приглашение: зарплата «от–до» и тип (гросс/нетто) обязательны — кандидат видит условия до общения. */
export default function InviteModal({ candidate, need, onClose, onSent }: Props) {
  const qc = useQueryClient();
  const [message, setMessage] = useState(
    need ? `Здравствуйте! Приглашаем вас на позицию «${need.title}». ${need.description ?? ""}`.trim() : "",
  );
  const [from, setFrom] = useState(need?.salary_from ?? 0);
  const [to, setTo] = useState(need?.salary_to ?? 0);
  const [type, setType] = useState<"gross" | "net">((need?.salary_type as "gross" | "net") ?? "net");
  const [contact, setContact] = useState("Telegram или телефон HR — напишем в течение дня");
  const [error, setError] = useState<string | null>(null);

  const send = useMutation({
    mutationFn: () =>
      post<S["InvitationOut"]>("/invitations", {
        candidate_id: candidate.id,
        need_id: need?.id ?? null,
        message,
        salary_from: from,
        salary_to: to,
        salary_type: type,
        contact_method: contact,
      }),
    onSuccess: (inv) => {
      qc.invalidateQueries({ queryKey: ["matches"] });
      qc.invalidateQueries({ queryKey: ["employer-invitations"] });
      qc.invalidateQueries({ queryKey: ["candidates"] });
      onSent?.(inv);
      onClose();
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Не удалось отправить"),
  });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!from || !to || from > to) return setError("Укажите зарплату «от» и «до» (от не больше до)");
    setError(null);
    send.mutate();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4" onClick={onClose}>
      <form
        className="max-h-[95vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-6 sm:rounded-2xl"
        onClick={(e) => e.stopPropagation()}
        onSubmit={submit}
      >
        <h2 className="text-lg font-bold">Пригласить: {candidate.full_name ?? `кандидат №${candidate.id}`}</h2>
        <p className="mt-1 text-sm text-slate-600">
          Кандидат сразу увидит компанию, предложение и зарплату. Контакты откроются, когда он примет приглашение.
        </p>
        <div className="mt-4 space-y-3">
          <div>
            <label className="label" htmlFor="inv-msg">Предложение</label>
            <textarea id="inv-msg" className="input min-h-28" required value={message} onChange={(e) => setMessage(e.target.value)} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label" htmlFor="inv-from">Зарплата от, ₽</label>
              <input id="inv-from" className="input" type="number" min={1} required value={from || ""} onChange={(e) => setFrom(+e.target.value)} />
            </div>
            <div>
              <label className="label" htmlFor="inv-to">до, ₽</label>
              <input id="inv-to" className="input" type="number" min={1} required value={to || ""} onChange={(e) => setTo(+e.target.value)} />
            </div>
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
            {(["net", "gross"] as const).map((t) => (
              <label key={t} className="flex items-center gap-2">
                <input type="radio" name="inv-type" checked={type === t} onChange={() => setType(t)} /> {SALARY_TYPE[t]}
              </label>
            ))}
          </div>
          <div>
            <label className="label" htmlFor="inv-contact">Как вы свяжетесь</label>
            <input id="inv-contact" className="input" required value={contact} onChange={(e) => setContact(e.target.value)} />
          </div>
        </div>
        {error && <p className="mt-3 text-sm text-fsp-accent">{error}</p>}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="btn-ghost" onClick={onClose}>Отмена</button>
          <button className="btn-accent" disabled={send.isPending}>{send.isPending ? "Отправляем…" : "Отправить приглашение"}</button>
        </div>
      </form>
    </div>
  );
}
