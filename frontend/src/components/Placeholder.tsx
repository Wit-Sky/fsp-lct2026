/** Заглушка экрана, который делается на шаге 2 (team/EVGENY.md). */
export default function Placeholder({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="card">
      <h1 className="text-xl font-bold">{title}</h1>
      <p className="mt-2 text-slate-600">{hint ?? "Экран в работе."}</p>
    </div>
  );
}
