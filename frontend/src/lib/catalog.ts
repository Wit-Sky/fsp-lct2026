import { useQuery } from "@tanstack/react-query";
import { get } from "./api";

export type Catalog = {
  specs: { id: string; title: string }[];
  grades: { id: string; title: string; threshold: number }[];
  skills: Record<string, string[]>;
  [k: string]: unknown;
};

/** Справочники (специализации, грейды, навыки) — `/api/catalog`, меняются редко. */
export const useCatalog = () =>
  useQuery({ queryKey: ["catalog"], queryFn: () => get<Catalog>("/catalog"), staleTime: Infinity });
