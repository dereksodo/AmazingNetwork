import { useCallback, useEffect, useState } from 'react';
import { api, ApiError } from './api/client';

/** Load a resource; `reload` fetches it again and keeps showing the old data meanwhile. */
export function useResource<T>(path: string) {
  const [state, setState] = useState<{ path: string; data?: T; error?: ApiError }>({ path });
  const reload = useCallback(
    () =>
      api.get<T>(path).then(
        (data) => setState({ path, data }),
        (error: ApiError) => setState({ path, error }),
      ),
    [path],
  );
  useEffect(() => {
    void reload();
  }, [reload]);
  const current = state.path === path ? state : { data: undefined, error: undefined };
  return { data: current.data, error: current.error, reload };
}

/** Run an action and keep its error message for display. */
export function useAction() {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const run = useCallback(async (action: () => Promise<unknown>) => {
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (problem) {
      setError((problem as Error).message);
    } finally {
      setBusy(false);
    }
  }, []);
  return { run, error, busy };
}
