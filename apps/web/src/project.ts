// Active project persistence in localStorage.

const PROJECT_KEY = "cgi.activeProjectId";
const TOKEN_KEY = "cgi.projectToken";

export function getActiveProjectId(): string | null {
  try {
    return localStorage.getItem(PROJECT_KEY);
  } catch {
    return null;
  }
}

export function setActiveProjectId(id: string): void {
  try {
    localStorage.setItem(PROJECT_KEY, id);
  } catch {
    /* ignore */
  }
}

export function clearActiveProjectId(): void {
  try {
    localStorage.removeItem(PROJECT_KEY);
  } catch {
    /* ignore */
  }
}

export function getProjectToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setProjectToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    /* ignore */
  }
}
