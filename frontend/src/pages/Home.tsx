import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ApiError, post, type Role, type S, type Token } from "../lib/api";
import { homeFor, useAuth } from "../lib/auth";

export default function Home() {
  const { role, demo } = useAuth();
  const navigate = useNavigate();
  const [busy, setBusy] = useState<Role | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (role) return <Navigate to={homeFor(role)} replace />;

  const runDemo = async (r: Role) => {
    setBusy(r);
    setError(null);
    try {
      const t = await demo(r);
      navigate(homeFor(t.role as Role));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Не удалось войти");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-gradient-to-br from-fsp to-fsp-dark p-8 text-white">
        <h1 className="max-w-3xl text-3xl font-bold leading-tight">
          Работодатель сам находит ИТ-специалиста — по подтверждённому грейду, а не по резюме
        </h1>
        <p className="mt-3 max-w-2xl text-white/85">
          Кандидат проходит короткий тест и попадает в категорию «специализация × грейд». Результаты соревнований ФСП
          поднимают его внутри категории. Работодатель видит, почему кандидат в подборке, и приглашает его с зарплатой.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button className="btn bg-white text-fsp hover:bg-fsp-tint" disabled={!!busy} onClick={() => runDemo("candidate")}>
            {busy === "candidate" ? "Входим…" : "Я кандидат — демо"}
          </button>
          <button className="btn-accent" disabled={!!busy} onClick={() => runDemo("employer")}>
            {busy === "employer" ? "Входим…" : "Я работодатель — демо"}
          </button>
        </div>
        {error && <p className="mt-3 text-sm text-fsp-tint">{error}</p>}
      </section>

      <div className="grid gap-6 md:grid-cols-2">
        <RegisterCard />
        <LoginCard />
      </div>
    </div>
  );
}

function RegisterCard() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("candidate");
  const [sent, setSent] = useState<S["RegisterOut"] | null>(null);
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const register = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const r = await post<S["RegisterOut"]>("/auth/register", { email, password, role });
      setSent(r);
      if (r.verify_code) setCode(r.verify_code);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ошибка регистрации");
    }
  };

  const verify = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const t = await post<Token>("/auth/verify", { email, code });
      signIn(t);
      navigate(homeFor(t.role as Role));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Неверный код");
    }
  };

  return (
    <div className="card">
      <h2 className="text-lg font-bold">Регистрация по email</h2>
      {!sent ? (
        <form className="mt-4 space-y-3" onSubmit={register}>
          <div className="flex gap-2">
            {(["candidate", "employer"] as Role[]).map((r) => (
              <button
                type="button"
                key={r}
                onClick={() => setRole(r)}
                className={`btn flex-1 border ${role === r ? "border-fsp bg-fsp/5 text-fsp" : "border-slate-300 bg-white"}`}
              >
                {r === "candidate" ? "Ищу работу" : "Ищу сотрудников"}
              </button>
            ))}
          </div>
          <div>
            <label className="label" htmlFor="r-email">Email</label>
            <input id="r-email" className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div>
            <label className="label" htmlFor="r-pass">Пароль</label>
            <input id="r-pass" className="input" type="password" minLength={4} required value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
          <button className="btn-primary w-full">Получить код подтверждения</button>
        </form>
      ) : (
        <form className="mt-4 space-y-3" onSubmit={verify}>
          <p className="text-sm text-slate-600">
            Код отправлен на <b>{sent.email}</b>.
            {sent.verify_code && " На демо письмо имитируется — код уже подставлен."}
          </p>
          <div>
            <label className="label" htmlFor="r-code">Код из письма</label>
            <input id="r-code" className="input tracking-[0.4em]" inputMode="numeric" maxLength={6} required value={code} onChange={(e) => setCode(e.target.value)} />
          </div>
          <button className="btn-primary w-full">Подтвердить и войти</button>
        </form>
      )}
      {error && <p className="mt-3 text-sm text-fsp-accent">{error}</p>}
    </div>
  );
}

function LoginCard() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);

  const login = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const t = await post<Token>("/auth/login", { email, password });
      signIn(t);
      navigate(homeFor(t.role as Role));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не удалось войти");
    }
  };

  return (
    <div className="card">
      <h2 className="text-lg font-bold">Вход</h2>
      <form className="mt-4 space-y-3" onSubmit={login}>
        <div>
          <label className="label" htmlFor="l-email">Email</label>
          <input id="l-email" className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <label className="label" htmlFor="l-pass">Пароль</label>
          <input id="l-pass" className="input" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>
        <button className="btn-ghost w-full">Войти</button>
      </form>
      {error && <p className="mt-3 text-sm text-fsp-accent">{error}</p>}
    </div>
  );
}
