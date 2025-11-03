import {
  ReactNode,
  createContext,
  useContext,
  useMemo,
  useState,
  useCallback,
  useEffect,
} from "react";
import { apiClient, type ApiClient } from "../services/api";

interface BackendContextValue {
  client: ApiClient;
  backendReachable: boolean;
  lastError: string | null;
  refreshHealth: () => Promise<void>;
}

const BackendContext = createContext<BackendContextValue | undefined>(undefined);

interface BackendProviderProps {
  children: ReactNode;
}

export function BackendProvider({ children }: BackendProviderProps) {
  const [backendReachable, setBackendReachable] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);

  const refreshHealth = useCallback(async () => {
    try {
      const response = await fetch(`${apiClient.baseUrl()}/api/v1/health`);
      setBackendReachable(response.ok);
      setLastError(response.ok ? null : response.statusText);
    } catch (error) {
      setBackendReachable(false);
      setLastError((error as Error).message);
    }
  }, []);

  useEffect(() => {
    void refreshHealth();
  }, [refreshHealth]);

  const value = useMemo<BackendContextValue>(
    () => ({
      client: apiClient,
      backendReachable,
      lastError,
      refreshHealth,
    }),
    [backendReachable, lastError, refreshHealth],
  );

  return (
    <BackendContext.Provider value={value}>{children}</BackendContext.Provider>
  );
}

export function useBackend(): BackendContextValue {
  const ctx = useContext(BackendContext);
  if (!ctx) {
    throw new Error("useBackend must be used within BackendProvider");
  }
  return ctx;
}
