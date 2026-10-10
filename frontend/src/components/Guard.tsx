import { Navigate, Outlet } from "react-router-dom";
import type { Role } from "../lib/api";
import { useAuth } from "../lib/auth";

/** Пускает только авторизованного пользователя нужной роли. */
export default function Guard({ role }: { role: Role }) {
  const { role: current } = useAuth();
  if (!current) return <Navigate to="/" replace />;
  if (current !== role) return <Navigate to={current === "employer" ? "/employer" : "/candidate"} replace />;
  return <Outlet />;
}
