const BASE_URL = '/api';

type Params = Record<string, string | number | boolean | undefined>;

/** Normalised error for every failed request: {detail, code} from the backend. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
  }
}

function buildUrl(path: string, params?: Params): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined) search.set(key, String(value));
  }
  const query = search.toString();
  return `${BASE_URL}${path}${query ? `?${query}` : ''}`;
}

async function readError(response: Response): Promise<{ code: string; detail: string }> {
  try {
    const body: unknown = await response.json();
    if (
      typeof body === 'object' &&
      body !== null &&
      'detail' in body &&
      'code' in body &&
      typeof body.detail === 'string' &&
      typeof body.code === 'string'
    ) {
      return { code: body.code, detail: body.detail };
    }
  } catch {
    // Body was not JSON; fall through to the generic message.
  }
  return { code: 'HTTP_ERROR', detail: `Request failed (${response.status}).` };
}

export async function request<T>(
  path: string,
  options: { params?: Params; signal?: AbortSignal; method?: 'GET' | 'POST' } = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.params), {
      method: options.method ?? 'GET',
      headers: { Accept: 'application/json' },
      signal: options.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err;
    throw new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the API. Is the backend running?');
  }

  if (!response.ok) {
    const { code, detail } = await readError(response);
    throw new ApiError(response.status, code, detail);
  }
  return (await response.json()) as T;
}

export function getHealth(signal?: AbortSignal): Promise<{ status: string }> {
  return request('/health', { signal });
}
