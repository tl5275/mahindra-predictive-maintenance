const ABSOLUTE_URL_PATTERN = /^[a-z][a-z\d+\-.]*:\/\//i;

function trimSlashes(value) {
  return String(value || "").replace(/^\/+|\/+$/g, "");
}

function serializeBaseUrl(url) {
  const pathname = url.pathname.replace(/\/+$/, "");
  return `${url.protocol}//${url.host}${pathname}`;
}

function normalizeBaseUrl(value) {
  if (typeof value !== "string" || !value.trim()) {
    return null;
  }

  try {
    return serializeBaseUrl(new URL(value.trim()));
  } catch {
    return null;
  }
}

function joinUrlPath(basePath = "", nextPath = "") {
  const base = trimSlashes(basePath);
  const next = trimSlashes(nextPath);
  return `/${[base, next].filter(Boolean).join("/")}`;
}

function resolveApiUrl() {
  const envUrl = normalizeBaseUrl(import.meta.env.VITE_API_URL);
  if (envUrl) {
    return envUrl;
  }

  if (import.meta.env.DEV) {
    return "http://localhost:8000";
  }

  return null;
}

export const API_URL = resolveApiUrl();

export function getApiUrl() {
  if (API_URL) {
    return API_URL;
  }

  throw new Error("Missing VITE_API_URL. Configure it in your Vite environment for production.");
}

export function buildApiUrl(path = "") {
  const normalizedPath = String(path || "");
  if (ABSOLUTE_URL_PATTERN.test(normalizedPath)) {
    return normalizedPath;
  }

  const [relativePath, search = ""] = normalizedPath.split("?");
  const apiUrl = new URL(`${getApiUrl()}/`);

  if (relativePath) {
    apiUrl.pathname = joinUrlPath(apiUrl.pathname, relativePath);
  }
  apiUrl.search = search ? `?${search}` : "";
  apiUrl.hash = "";

  return apiUrl.toString();
}

export function buildFleetWebSocketUrl() {
  const apiUrl = new URL(`${getApiUrl()}/`);
  apiUrl.protocol = apiUrl.protocol === "https:" ? "wss:" : "ws:";
  apiUrl.pathname = joinUrlPath(apiUrl.pathname, "/ws/fleet");
  apiUrl.search = "";
  apiUrl.hash = "";
  return apiUrl.toString();
}
