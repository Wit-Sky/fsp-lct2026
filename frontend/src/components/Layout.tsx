import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import BugReport from "./BugReport";
import ErrorBoundary from "./ErrorBoundary";

const candidateNav = [
  { to: "/candidate", label: "Мой путь", end: true },
  { to: "/candidate/category", label: "Категория" },
  { to: "/candidate/invitations", label: "Приглашения" },
  { to: "/candidate/tasks", label: "Задания" },
  { to: "/candidate/vacancies", label: "Вакансии" },
  { to: "/candidate/profile", label: "Профиль" },
];
const employerNav = [
  { to: "/employer", label: "Подбор", end: true },
  { to: "/employer/search", label: "База кандидатов" },
  { to: "/employer/invitations", label: "Приглашения" },
  { to: "/employer/tasks", label: "Задания" },
  { to: "/employer/company", label: "Компания" },
];

export default function Layout() {
  const { role, signOut } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const nav = role === "employer" ? employerNav : role === "candidate" ? candidateNav : [];

  return (
    <div className="flex min-h-screen flex-col">
      <header className="bg-fsp-dark text-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <NavLink to="/" className="text-lg font-bold tracking-tight">
            ФСП <span className="text-fsp-pink">Талант</span>
          </NavLink>
          <nav className="order-last -mx-4 flex w-[calc(100%+2rem)] gap-1 overflow-x-auto px-4 sm:order-none sm:mx-0 sm:w-auto sm:flex-1 sm:px-0">
            {nav.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-md px-3 py-1.5 text-sm ${isActive ? "bg-white/15 font-semibold" : "text-white/80 hover:text-white"}`
                }
              >
                {n.label}
              </NavLink>
            ))}
          </nav>
          {role && (
            <div className="ml-auto flex items-center gap-3 text-sm">
              <span className="rounded-full bg-white/10 px-3 py-1">{role === "employer" ? "Работодатель" : "Кандидат"}</span>
              <button
                className="text-white/80 hover:text-white"
                onClick={() => {
                  signOut();
                  navigate("/");
                }}
              >
                Выйти
              </button>
            </div>
          )}
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
        <ErrorBoundary resetKey={location.pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
      <footer className="border-t border-slate-200 py-4 text-center text-xs text-slate-500">
        ЛЦТ-2026 · спецтрек Федерации спортивного программирования
      </footer>
      <BugReport />
    </div>
  );
}
