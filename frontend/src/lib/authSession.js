const STORAGE_KEYS = {
  accessToken: "nextdmarc_access_token",
  tenantId: "nextdmarc_tenant_id",
  role: "nextdmarc_role",
  csrfToken: "nextdmarc_csrf_token"
};

const FALLBACK_API_BASE_URL = "http://localhost:8000/api/v1";

function getStorage() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
}

function normalizeApiBaseUrl(rawValue) {
  const value = (rawValue || FALLBACK_API_BASE_URL).trim();
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function decodeJwtPayload(token) {
  if (!token || typeof token !== "string") {
    return null;
  }

  const parts = token.split(".");
  if (parts.length !== 3) {
    return null;
  }

  const payloadPart = parts[1];
  const padded = payloadPart + "=".repeat((4 - (payloadPart.length % 4 || 4)) % 4);
  const base64 = padded.replace(/-/g, "+").replace(/_/g, "/");

  try {
    const decoded = window.atob(base64);
    return JSON.parse(decoded);
  } catch {
    return null;
  }
}

function buildSessionFromAccessToken(accessToken, csrfToken) {
  const payload = decodeJwtPayload(accessToken);
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const tenantId = typeof payload.tenant_id === "string" ? payload.tenant_id : "";
  const role = typeof payload.role === "string" ? payload.role : "";

  if (!tenantId || !role) {
    return null;
  }

  return {
    accessToken,
    tenantId,
    role,
    csrfToken: csrfToken || ""
  };
}

function extractErrorMessage(data, fallbackMessage) {
  if (data && typeof data === "object") {
    const error = data.error;
    if (error && typeof error === "object" && typeof error.message === "string") {
      return error.message;
    }
    if (typeof data.detail === "string") {
      return data.detail;
    }
  }
  return fallbackMessage;
}

async function parseJsonSafe(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

export function getApiBaseUrl() {
  return normalizeApiBaseUrl(process.env.NEXT_PUBLIC_API_BASE_URL);
}

export function getAuthSession() {
  const storage = getStorage();
  if (!storage) {
    return null;
  }

  const accessToken = storage.getItem(STORAGE_KEYS.accessToken) || "";
  const tenantId = storage.getItem(STORAGE_KEYS.tenantId) || "";
  const role = storage.getItem(STORAGE_KEYS.role) || "";
  const csrfToken = storage.getItem(STORAGE_KEYS.csrfToken) || "";

  if (!accessToken || !tenantId || !role) {
    return null;
  }

  return { accessToken, tenantId, role, csrfToken };
}

export function saveAuthSession(session) {
  const storage = getStorage();
  if (!storage || !session) {
    return;
  }

  storage.setItem(STORAGE_KEYS.accessToken, session.accessToken);
  storage.setItem(STORAGE_KEYS.tenantId, session.tenantId);
  storage.setItem(STORAGE_KEYS.role, session.role);

  if (session.csrfToken) {
    storage.setItem(STORAGE_KEYS.csrfToken, session.csrfToken);
  } else {
    storage.removeItem(STORAGE_KEYS.csrfToken);
  }
}

export function clearAuthSession() {
  const storage = getStorage();
  if (!storage) {
    return;
  }

  storage.removeItem(STORAGE_KEYS.accessToken);
  storage.removeItem(STORAGE_KEYS.tenantId);
  storage.removeItem(STORAGE_KEYS.role);
  storage.removeItem(STORAGE_KEYS.csrfToken);
}

export async function registerTenantAdmin(payload) {
  const response = await fetch(`${getApiBaseUrl()}/auth/register-tenant`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    credentials: "include",
    body: JSON.stringify(payload)
  });

  const data = await parseJsonSafe(response);
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Tenant registration failed"));
  }

  return data;
}

export async function loginWithPassword(payload) {
  const response = await fetch(`${getApiBaseUrl()}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    credentials: "include",
    body: JSON.stringify(payload)
  });

  const data = await parseJsonSafe(response);
  if (!response.ok) {
    throw new Error(extractErrorMessage(data, "Login failed"));
  }

  const session = buildSessionFromAccessToken(data?.access_token, data?.csrf_token || "");
  if (!session) {
    throw new Error("Login succeeded but token payload is missing tenant or role claims");
  }

  saveAuthSession(session);
  return session;
}

export async function refreshAuthSession() {
  const response = await fetch(`${getApiBaseUrl()}/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    credentials: "include",
    body: JSON.stringify({})
  });

  const data = await parseJsonSafe(response);
  if (!response.ok) {
    clearAuthSession();
    return null;
  }

  const session = buildSessionFromAccessToken(data?.access_token, data?.csrf_token || "");
  if (!session) {
    clearAuthSession();
    return null;
  }

  saveAuthSession(session);
  return session;
}

export async function logoutAuthSession() {
  try {
    await fetch(`${getApiBaseUrl()}/auth/logout`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      credentials: "include",
      body: JSON.stringify({})
    });
  } finally {
    clearAuthSession();
  }
}
