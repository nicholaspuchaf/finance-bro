import { describeError } from './i18n/core.js';

export async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail) ? body.detail.map((item) => item.msg).join('; ') : body.detail;
    const error = new Error(detail || `API error (${response.status})`);
    error.translation = describeError(body.detail || '', response.status);
    throw error;
  }
  return response.status === 204 ? null : response.json();
}
