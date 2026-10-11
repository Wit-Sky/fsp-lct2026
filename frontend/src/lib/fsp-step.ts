import { useEffect, useState } from "react";

const keyFor = (userId: number) => `fsp_skip:${userId}`;

function readSkipped(userId: number | null) {
  if (userId == null) return false;
  try { return localStorage.getItem(keyFor(userId)) === "1"; } catch { return false; }
}

/** Пока API не хранит выбор, он относится только к конкретному аккаунту в этом браузере. */
export function useFspSkip(userId: number | null) {
  const [skipped, setSkipped] = useState(() => readSkipped(userId));
  useEffect(() => { setSkipped(readSkipped(userId)); }, [userId]);
  const skip = () => {
    if (userId == null) return;
    try { localStorage.setItem(keyFor(userId), "1"); } catch { /* выбор работает и без доступа к storage */ }
    setSkipped(true);
  };
  return { skipped, skip };
}
