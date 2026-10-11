import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { initQaMode, qaEvents, scrub } from "../lib/qa";

const REPO_ISSUES = "https://github.com/Wit-Sky/fsp-lct2026/issues/new";
const SEVERITY = ["блокер — сквозной путь не проходит", "заметно жюри", "мелочь"];
const qaOn = initQaMode();

/** Плавающая кнопка баг-репорта: только в режиме тестирования. Контекст собирается сам, токены вырезаются. */
export default function BugReport() {
  const [open, setOpen] = useState(false);
  const [did, setDid] = useState("");
  const [expected, setExpected] = useState("");
  const [got, setGot] = useState("");
  const [severity, setSeverity] = useState(1);
  const [copied, setCopied] = useState(false);
  const { role, token } = useAuth();
  const loc = useLocation();
  if (!qaOn) return null;

  const context = [
    `Страница: ${scrub(window.location.origin + loc.pathname + loc.search)}`,
    `Роль: ${role ?? "не вошёл"}${token ? ` (user_id ${token.user_id})` : ""}`,
    `Экран: ${window.innerWidth}×${window.innerHeight}, ${navigator.userAgent}`,
    `Время: ${new Date().toLocaleString("ru-RU")}`,
  ].join("\n");
  const log = qaEvents().map((e) => `${e.at} [${e.kind}] ${e.text}`).join("\n") || "—";
  const title = `[${SEVERITY[severity].split(" ")[0]}] ${did.split("\n")[0].slice(0, 70) || "Ошибка"}`;
  const body = `**Что делала**\n${did || "—"}\n\n**Что ожидала**\n${expected || "—"}\n\n**Что получила**\n${got || "—"}\n\n**Важность:** ${SEVERITY[severity]}\n\n**Контекст (автоматически)**\n\`\`\`\n${context}\n\`\`\`\n\n**Последние ошибки API/JS**\n\`\`\`\n${log}\n\`\`\`\n\nСкриншот — перетащите в это поле.`;

  const openIssue = () => {
    const url = `${REPO_ISSUES}?${new URLSearchParams({ title, body: body.slice(0, 6000), labels: "bug" })}`;
    window.open(url, "_blank", "noopener");
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${title}\n\n${body}`);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* без доступа к буферу — пусть копирует вручную */
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 z-40 flex h-11 w-11 items-center justify-center rounded-full bg-amber-500 text-xl shadow-lg hover:bg-amber-600"
        title="Сообщить об ошибке (режим тестирования; ?qa=0 в адресе выключает)"
        aria-label="Сообщить об ошибке"
      >
        🐞
      </button>
      {open && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 sm:items-center sm:p-4" onClick={() => setOpen(false)}>
          <div className="max-h-[95vh] w-full max-w-lg space-y-3 overflow-y-auto rounded-t-2xl bg-white p-5 sm:rounded-2xl" onClick={(e) => e.stopPropagation()}>
            <h2 className="text-lg font-bold">Баг-репорт</h2>
            <div><label className="label" htmlFor="b-did">Что делала (шаги)</label><textarea id="b-did" className="input min-h-20" value={did} onChange={(e) => setDid(e.target.value)} /></div>
            <div><label className="label" htmlFor="b-exp">Что ожидала</label><input id="b-exp" className="input" value={expected} onChange={(e) => setExpected(e.target.value)} /></div>
            <div><label className="label" htmlFor="b-got">Что получила</label><input id="b-got" className="input" value={got} onChange={(e) => setGot(e.target.value)} /></div>
            <div className="flex flex-col gap-1 text-sm">
              {SEVERITY.map((s, i) => (
                <label key={s} className="flex items-center gap-2"><input type="radio" name="b-sev" checked={severity === i} onChange={() => setSeverity(i)} /> {s}</label>
              ))}
            </div>
            <details className="rounded-lg bg-slate-50 p-3 text-xs">
              <summary className="cursor-pointer font-semibold">Контекст, который приложится сам</summary>
              <pre className="mt-2 whitespace-pre-wrap">{context}{"\n\n"}{log}</pre>
            </details>
            <div className="flex flex-wrap justify-end gap-2">
              <button className="btn-ghost" onClick={copy}>{copied ? "Скопировано ✓" : "Скопировать для чата"}</button>
              <button className="btn-primary" disabled={!did.trim()} onClick={openIssue}>Создать issue на GitHub</button>
            </div>
            <p className="text-xs text-slate-500">Откроется GitHub с заполненным текстом — проверьте, приложите скриншот и нажмите «Submit new issue».</p>
          </div>
        </div>
      )}
    </>
  );
}
