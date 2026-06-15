// Custom error types for the API layer.
//
// Why these exist:
//   The backend returns structured error bodies (e.g. 409 with
//   `detail.conflicts`). The default `Error` type discards this
//   structure, so the UI was showing "Request failed with status code 409"
//   instead of the actual conflict list. These classes carry the
//   structured payload so the UI can render it directly.

export interface PortConflict {
  host_port: number
  services: string[]
}

export class PortConflictError extends Error {
  readonly name = 'PortConflictError'
  readonly status: number
  readonly conflicts: PortConflict[]

  constructor(status: number, conflicts: PortConflict[], message?: string) {
    const first = conflicts[0]
    const fallback = first
      ? `Конфликт порта ${first.host_port} между: ${first.services.join(', ')}`
      : 'Конфликт портов в выбранных компонентах'
    super(message ?? fallback)
    this.status = status
    this.conflicts = conflicts
  }
}

export class ApiError extends Error {
  readonly name = 'ApiError'
  readonly status: number
  readonly detail: unknown

  constructor(status: number, message: string, detail?: unknown) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

/**
 * Inspect a failed `fetch` response and throw a structured error.
 *
 * - 409 with `detail.conflicts` → `PortConflictError`
 * - any other non-ok → `ApiError` with status + detail
 * - non-JSON body → `ApiError` with status and a generic message
 */
export async function throwOnError(res: Response, fallbackMessage: string): Promise<never> {
  let body: unknown = null
  try {
    body = await res.json()
  } catch {
    throw new ApiError(res.status, fallbackMessage)
  }

  const detail = (body as { detail?: unknown })?.detail
  if (
    res.status === 409 &&
    detail &&
    typeof detail === 'object' &&
    'conflicts' in detail &&
    Array.isArray((detail as { conflicts: unknown }).conflicts)
  ) {
    const conflicts = (detail as { conflicts: PortConflict[] }).conflicts
    throw new PortConflictError(res.status, conflicts)
  }

  const detailMsg =
    detail && typeof detail === 'object' && 'message' in detail
      ? String((detail as { message: unknown }).message)
      : typeof detail === 'string'
        ? detail
        : null
  throw new ApiError(res.status, detailMsg ?? fallbackMessage, detail)
}
