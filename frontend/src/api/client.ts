/** The only place that calls the REST API. */

const TOKEN_KEY = 'connect-token';

/** The token lives in sessionStorage, so two tabs can be signed in as different people. */
export const session = {
  get token() {
    return sessionStorage.getItem(TOKEN_KEY);
  },
  start: (token: string) => sessionStorage.setItem(TOKEN_KEY, token),
  end: () => sessionStorage.removeItem(TOKEN_KEY),
};

/** An error answer of the API. */
export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details: Record<string, number> | null,
  ) {
    super(message);
  }
}

async function send(method: string, path: string, body?: unknown, headers = {}): Promise<Response> {
  const form = body instanceof FormData;
  const response = await fetch(`/api/v1${path}`, {
    method,
    headers: {
      ...(session.token ? { Authorization: `Bearer ${session.token}` } : {}),
      ...(body === undefined || form ? {} : { 'Content-Type': 'application/json' }),
      ...headers,
    },
    body: form ? body : JSON.stringify(body),
  });
  if (!response.ok) {
    const { error } = await response.json();
    const fields = Array.isArray(error.details)
      ? error.details.map((d: { field: string; message: string }) => ` ${d.field}: ${d.message}.`)
      : [];
    throw new ApiError(response.status, error.code, error.message + fields.join(''), error.details);
  }
  return response;
}

async function json<T>(method: string, path: string, body?: unknown, headers = {}): Promise<T> {
  const response = await send(method, path, body, headers);
  return response.status === 204 ? (undefined as T) : response.json();
}

export const api = {
  get: <T>(path: string) => json<T>('GET', path),
  post: <T = void>(path: string, body?: unknown) => json<T>('POST', path, body),
  put: <T = void>(path: string, body?: unknown) => json<T>('PUT', path, body),
  patch: <T = void>(path: string, body: unknown, headers = {}) =>
    json<T>('PATCH', path, body, headers),
  delete: (path: string) => json<void>('DELETE', path),
  blob: async (path: string) => (await send('GET', path)).blob(),
};
