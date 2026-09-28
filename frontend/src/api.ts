function getApiBase() {
  if (import.meta.env.VITE_API_BASE_URL) return import.meta.env.VITE_API_BASE_URL;
  if (typeof window !== "undefined") return `${window.location.protocol}//${window.location.hostname}:8000/api/v1`;
  return "http://127.0.0.1:8000/api/v1";
}

const API_BASE = getApiBase();

export type User = { id: string; email: string; full_name: string; role: "PATIENT" | "ADMIN" };
export type Centre = { id: string; name: string; location: string; is_active: boolean };
export type DiagnosticTest = { id: string; centre_id: string; name: string; description: string; price: string; currency: string; is_active: boolean };
export type Booking = { id: string; test_id: string; centre_id: string; appointment_at: string; amount: string; currency: string; status: "PENDING" | "CONFIRMED" | "FAILED" | "CANCELLED" };

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem("eve_token");
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers ?? {}) },
    });
  } catch {
    throw new Error("Unable to reach the API. Start the backend on port 8000 and try again.");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Something went wrong. Please try again.");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function saveSession(token: string, user: User) {
  sessionStorage.setItem("eve_token", token);
  sessionStorage.setItem("eve_user", JSON.stringify(user));
}

export function clearSession() {
  sessionStorage.removeItem("eve_token");
  sessionStorage.removeItem("eve_user");
}
