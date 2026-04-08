import {
  clearAuthSession,
  getApiBaseUrl,
  getAuthSession,
  refreshAuthSession
} from "lib/authSession";

const WRITE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

function extractErrorMessage(payload, fallbackMessage) {
  if (payload && typeof payload === "object") {
    const error = payload.error;
    if (error && typeof error === "object" && typeof error.message === "string") {
      return error.message;
    }
    if (typeof payload.detail === "string") {
      return payload.detail;
    }
  }
  return fallbackMessage;
}

async function parseResponsePayload(response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();
  return text || null;
}

function normalizePath(path) {
  if (!path) {
    return "";
  }
  return path.startsWith("/") ? path : `/${path}`;
}

export function toQueryString(params) {
  const search = new URLSearchParams();
  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === null || value === undefined || value === "") {
      return;
    }
    search.set(key, String(value));
  });
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export async function apiRequest(
  path,
  {
    method = "GET",
    body,
    headers = {},
    skipAuth = false,
    retryOnAuth = true
  } = {}
) {
  const normalizedMethod = method.toUpperCase();
  const session = getAuthSession();
  const requestHeaders = { ...headers };
  let requestBody = body;

  if (body !== undefined && !(body instanceof FormData)) {
    requestHeaders["Content-Type"] = "application/json";
    requestBody = JSON.stringify(body);
  }

  if (!skipAuth && session) {
    requestHeaders.Authorization = `Bearer ${session.accessToken}`;
    requestHeaders["X-Tenant-ID"] = session.tenantId;
    requestHeaders["X-Role"] = session.role;

    if (WRITE_METHODS.has(normalizedMethod) && session.csrfToken) {
      requestHeaders["X-CSRF-Token"] = session.csrfToken;
    }
  }

  const response = await fetch(`${getApiBaseUrl()}${normalizePath(path)}`, {
    method: normalizedMethod,
    headers: requestHeaders,
    credentials: "include",
    body: requestBody
  });

  if (response.status === 401 && !skipAuth && retryOnAuth) {
    const refreshed = await refreshAuthSession();
    if (refreshed) {
      return apiRequest(path, {
        method: normalizedMethod,
        body,
        headers,
        skipAuth,
        retryOnAuth: false
      });
    }
    clearAuthSession();
  }

  const payload = await parseResponsePayload(response);
  if (!response.ok) {
    const fallback = `Request failed (${response.status})`;
    throw new Error(extractErrorMessage(payload, fallback));
  }

  return payload;
}
