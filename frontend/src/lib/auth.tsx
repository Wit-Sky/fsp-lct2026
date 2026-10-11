import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { post, tokenStore, type Role, type Token } from "./api";

type AuthCtx = {
  token: Token | null;
  role: Role | null;
  signIn: (t: Token) => void;
  demo: (role: Role) => Promise<Token>;
  signOut: () => void;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const qc = useQueryClient();
  const [token, setToken] = useState<Token | null>(() => tokenStore.get());

  const signIn = useCallback((t: Token) => {
    qc.clear();
    tokenStore.set(t);
    setToken(t);
  }, [qc]);
  const signOut = useCallback(() => {
    qc.clear();
    tokenStore.set(null);
    setToken(null);
  }, [qc]);
  const demo = useCallback(
    async (role: Role) => {
      const t = await post<Token>(`/auth/demo/${role}`);
      signIn(t);
      return t;
    },
    [signIn],
  );

  useEffect(() => {
    const onLogout = () => { qc.clear(); setToken(null); };
    window.addEventListener("fsp:logout", onLogout);
    return () => window.removeEventListener("fsp:logout", onLogout);
  }, [qc]);

  return (
    <Ctx.Provider value={{ token, role: (token?.role as Role) ?? null, signIn, demo, signOut }}>
      {children}
    </Ctx.Provider>
  );
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth вне AuthProvider");
  return c;
}

export const homeFor = (role: Role | null) => (role === "employer" ? "/employer" : role === "candidate" ? "/candidate" : "/");
