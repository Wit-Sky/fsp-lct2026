// Режим тестирования (для Стаси): ?qa=1 включает кнопку баг-репорта, ?qa=0 выключает. Жюри её не видит.
// Здесь же — кольцевой буфер последних ошибок API и JS, которые попадают в отчёт автоматически.

const QA_KEY = "fsp_qa";
const MAX = 15;

export type QaEvent = { at: string; kind: "api" | "js"; text: string };
const events: QaEvent[] = [];

export function initQaMode(): boolean {
  try {
    const q = new URLSearchParams(window.location.search).get("qa");
    if (q === "1") localStorage.setItem(QA_KEY, "1");
    if (q === "0") localStorage.removeItem(QA_KEY);
    return localStorage.getItem(QA_KEY) === "1";
  } catch {
    return false;
  }
}

/** Убирает из строки всё, похожее на токены: параметр token=…, JWT. */
export const scrub = (s: string) =>
  s.replace(/([?&](token|state|code)=)[^&\s]+/gi, "$1…").replace(/eyJ[\w-]+\.[\w-]+\.[\w-]+/g, "<jwt>");

export function recordQaEvent(kind: QaEvent["kind"], text: string) {
  events.push({ at: new Date().toLocaleTimeString("ru-RU"), kind, text: scrub(text).slice(0, 300) });
  if (events.length > MAX) events.shift();
}

export const qaEvents = () => [...events];

window.addEventListener("error", (e) => recordQaEvent("js", `${e.message} @ ${e.filename?.split("/").pop()}:${e.lineno}`));
window.addEventListener("unhandledrejection", (e) => recordQaEvent("js", `unhandled: ${String(e.reason)}`));
