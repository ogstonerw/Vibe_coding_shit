import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { BotFarmRepository } from "../data/BotFarmRepository";
import { botFarmRepository } from "../data/repository";
import type { FarmSnapshot } from "../domain/botFarm";

interface FarmDataState {
  snapshot: FarmSnapshot | null;
  loading: boolean;
  error: string | null;
}

const FarmDataContext = createContext<FarmDataState | null>(null);

interface FarmDataProviderProps {
  children: ReactNode;
  repository?: BotFarmRepository;
}

export function FarmDataProvider({ children, repository = botFarmRepository }: FarmDataProviderProps) {
  const [snapshot, setSnapshot] = useState<FarmSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    repository
      .getFarmSnapshot()
      .then((farmSnapshot) => {
        if (active) setSnapshot(farmSnapshot);
      })
      .catch(() => {
        if (active) setError("Не удалось загрузить состояние фермы");
      });

    return () => {
      active = false;
    };
  }, [repository]);

  const value = useMemo(
    () => ({ snapshot, error, loading: snapshot === null && error === null }),
    [error, snapshot],
  );

  return <FarmDataContext.Provider value={value}>{children}</FarmDataContext.Provider>;
}

export function useFarmData() {
  const context = useContext(FarmDataContext);
  if (!context) throw new Error("useFarmData must be used inside FarmDataProvider");
  return context;
}
