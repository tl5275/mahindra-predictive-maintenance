import { buildApiUrl } from "./config";

const DEFAULT_TIMEOUT_MS = 10000;

export class ApiRequestError extends Error {
  constructor({ message, status = null, code = "UNKNOWN_ERROR", url = "", details = null, cause = null }) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.url = url;
    this.details = details;
    this.cause = cause;
  }
}

function createApiError(options) {
  return new ApiRequestError(options);
}

function createTimeoutError() {
  if (typeof DOMException === "function") {
    return new DOMException("Request timed out", "TimeoutError");
  }

  const error = new Error("Request timed out");
  error.name = "TimeoutError";
  return error;
}

function mergeAbortSignals(externalSignal, internalController) {
  if (!externalSignal) {
    return {
      signal: internalController.signal,
      cleanup: () => {},
    };
  }

  if (typeof AbortSignal !== "undefined" && typeof AbortSignal.any === "function") {
    return {
      signal: AbortSignal.any([externalSignal, internalController.signal]),
      cleanup: () => {},
    };
  }

  const abort = () => internalController.abort(externalSignal.reason);
  if (externalSignal.aborted) {
    abort();
  } else {
    externalSignal.addEventListener("abort", abort, { once: true });
  }

  return {
    signal: internalController.signal,
    cleanup: () => externalSignal.removeEventListener("abort", abort),
  };
}

async function parseResponseBody(response) {
  const rawText = await response.text();
  const trimmed = rawText.trim();
  if (!trimmed) {
    return null;
  }

  const contentType = (response.headers.get("content-type") || "").toLowerCase();
  const expectsJson = contentType.includes("application/json") || trimmed.startsWith("{") || trimmed.startsWith("[");
  if (!expectsJson) {
    return { message: trimmed };
  }

  try {
    return JSON.parse(trimmed);
  } catch (error) {
    throw createApiError({
      message: "Received an invalid JSON response from the API.",
      status: response.status,
      code: "INVALID_JSON",
      url: response.url,
      details: { rawText: trimmed.slice(0, 500) },
      cause: error,
    });
  }
}

async function request(
  path,
  {
    method = "GET",
    headers = {},
    body,
    timeoutMs = DEFAULT_TIMEOUT_MS,
    signal,
  } = {},
) {
  let url;
  try {
    url = buildApiUrl(path);
  } catch (error) {
    throw createApiError({
      message: error instanceof Error ? error.message : "Invalid API configuration.",
      code: "CONFIG_ERROR",
      url: String(path),
      cause: error,
    });
  }

  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => controller.abort(createTimeoutError()), timeoutMs);
  const { signal: requestSignal, cleanup } = mergeAbortSignals(signal, controller);
  const isJsonBody =
    body !== undefined &&
    body !== null &&
    !(body instanceof FormData) &&
    !(typeof Blob !== "undefined" && body instanceof Blob) &&
    typeof body !== "string";

  try {
    const response = await fetch(url, {
      method,
      headers: {
        Accept: "application/json",
        ...(isJsonBody ? { "Content-Type": "application/json" } : {}),
        ...headers,
      },
      body:
        body === undefined || body === null
          ? undefined
          : isJsonBody
            ? JSON.stringify(body)
            : body,
      signal: requestSignal,
    });

    const payload = await parseResponseBody(response);
    if (!response.ok) {
      throw createApiError({
        message:
          (typeof payload?.detail === "string" && payload.detail) ||
          (typeof payload?.message === "string" && payload.message) ||
          `API request failed with status ${response.status}.`,
        status: response.status,
        code: `HTTP_${response.status}`,
        url,
        details: payload,
      });
    }

    return payload;
  } catch (error) {
    if (error instanceof ApiRequestError) {
      throw error;
    }

    if (error?.name === "AbortError" || error?.name === "TimeoutError") {
      throw createApiError({
        message: `Request timed out after ${timeoutMs}ms.`,
        code: "TIMEOUT",
        url,
        cause: error,
      });
    }

    throw createApiError({
      message: "Network request failed.",
      code: "NETWORK_ERROR",
      url,
      cause: error,
    });
  } finally {
    globalThis.clearTimeout(timeoutId);
    cleanup();
  }
}

export function getFleet(limit = 250, offset = 0) {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  return request(`/fleet?${params.toString()}`);
}

export function getVehicle(vehicleId, historyLimit = 50) {
  const params = new URLSearchParams({
    history_limit: String(historyLimit),
  });
  return request(`/vehicle/${encodeURIComponent(vehicleId)}?${params.toString()}`);
}

export function getAlerts(limit = 25) {
  const params = new URLSearchParams({
    limit: String(limit),
  });
  return request(`/alerts?${params.toString()}`);
}

export function getSystemStatus() {
  return request("/system-status");
}

export function getMetrics() {
  return request("/metrics");
}

export function postClientMetrics(payload) {
  return request("/metrics/client", {
    method: "POST",
    body: payload,
    timeoutMs: 5000,
  });
}
