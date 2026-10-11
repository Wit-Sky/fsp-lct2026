// Подписи и форматирование, общие для обоих кабинетов.

export const SPEC: Record<string, string> = { backend: "Бэкенд", frontend: "Фронтенд", bas: "БАС-разработчик" };
export const GRADE: Record<string, string> = { junior: "Junior", middle: "Middle", senior: "Senior" };
export const WORK_FORMAT: Record<string, string> = { office: "Офис", remote: "Удалённо", hybrid: "Гибрид" };
export const SALARY_TYPE: Record<string, string> = { gross: "до вычета НДФЛ (гросс)", net: "на руки (нетто)" };
export const SALARY_TYPE_SHORT: Record<string, string> = { gross: "гросс", net: "нетто" };
export const STATUS: Record<string, string> = { sent: "Отправлено", viewed: "Просмотрено", accepted: "Принято", declined: "Отклонено" };
export const RESULT_ROLE: Record<string, string> = { winner: "Победитель", prize: "Призёр", participant: "Участник" };
export const FACTOR: Record<string, string> = {
  stack: "Стек",
  test: "Тест",
  fsp: "ФСП",
  freshness: "Свежесть",
  preferences: "Условия",
};

const rub = new Intl.NumberFormat("ru-RU");

export function money(from?: number | null, to?: number | null, type?: string | null) {
  const range = from && to ? `${rub.format(from)} – ${rub.format(to)} ₽` : from ? `от ${rub.format(from)} ₽` : "—";
  return type ? `${range}, ${SALARY_TYPE_SHORT[type] ?? type}` : range;
}

export const pct = (v?: number | null) => (v == null ? "—" : `${Math.round(v * 100)} %`);

export function decimal(v: number | null | undefined, digits = 2) {
  if (v == null) return "—";
  return new Intl.NumberFormat("ru-RU", { minimumFractionDigits: digits, maximumFractionDigits: digits })
    .format(v).replace(/^-/, "−");
}

export function candidateNoun(count: number) {
  const n = Math.abs(count) % 100;
  if (n >= 11 && n <= 14) return "кандидатов";
  const last = n % 10;
  return last === 1 ? "кандидат" : last >= 2 && last <= 4 ? "кандидата" : "кандидатов";
}

export function dateTime(iso?: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("ru-RU", { day: "numeric", month: "long", hour: "2-digit", minute: "2-digit" });
}

export function date(iso?: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("ru-RU", { day: "numeric", month: "long", year: "numeric" });
}

export const statusTone: Record<string, string> = {
  sent: "bg-slate-100 text-slate-700",
  viewed: "bg-fsp-soft/20 text-fsp-dark",
  accepted: "bg-emerald-100 text-emerald-800",
  declined: "bg-rose-100 text-rose-700",
};
