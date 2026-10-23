/**
 * API client and shared auth utilities.
 */

const API_BASE = '/api';

// ── Token management ──────────────────────────────────────────────────────────
function getToken() { return localStorage.getItem('auth_token'); }
function setToken(t) { localStorage.setItem('auth_token', t); }
function removeToken() { localStorage.removeItem('auth_token'); }
function getUser() { try { return JSON.parse(localStorage.getItem('auth_user')); } catch { return null; } }
function setUser(u) { localStorage.setItem('auth_user', JSON.stringify(u)); }
function removeUser() { localStorage.removeItem('auth_user'); }

function isLoggedIn() { return !!getToken(); }

function logout() {
  removeToken();
  removeUser();
  window.location.href = '/index.html';
}

// ── API helper ────────────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = getToken();
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  let data;
  try { data = await res.json(); } catch { data = {}; }

  if (!res.ok) {
    const msg = data.detail || data.message || `Request failed (${res.status})`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

// ── Guard: redirect to login if not authenticated ─────────────────────────────
function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = '/index.html';
    return false;
  }
  return true;
}

// ── Toast notifications ───────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }

  const icons = { success: '✓', error: '✕', info: 'ℹ' };
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('out');
    toast.addEventListener('animationend', () => toast.remove());
  }, duration);
}

// ── Update navbar for logged-in state ─────────────────────────────────────────
function updateNavbar() {
  const user = getUser();
  const loginBtn = document.getElementById('nav-login-btn');
  const logoutBtn = document.getElementById('nav-logout-btn');
  const userGreeting = document.getElementById('nav-user');
  const dashLink = document.getElementById('nav-dashboard');
  const histLink = document.getElementById('nav-history');

  if (isLoggedIn() && user) {
    if (loginBtn) loginBtn.classList.add('hidden');
    if (logoutBtn) { logoutBtn.classList.remove('hidden'); logoutBtn.addEventListener('click', logout); }
    if (userGreeting) { userGreeting.classList.remove('hidden'); userGreeting.textContent = user.full_name || user.email.split('@')[0]; }
    if (dashLink) dashLink.classList.remove('hidden');
    if (histLink) histLink.classList.remove('hidden');
  } else {
    if (loginBtn) loginBtn.classList.remove('hidden');
    if (logoutBtn) logoutBtn.classList.add('hidden');
    if (userGreeting) userGreeting.classList.add('hidden');
    if (dashLink) dashLink.classList.add('hidden');
    if (histLink) histLink.classList.add('hidden');
  }
}

// ── Misc helpers ──────────────────────────────────────────────────────────────
function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
}

function statusBadge(status) {
  const map = {
    in_progress: ['⏳ In Progress', 'badge-amber'],
    submitted:   ['📨 Submitted',   'badge-blue'],
    evaluated:   ['✅ Evaluated',    'badge-green'],
    failed:      ['❌ Failed',       'badge-red'],
  };
  const [label, cls] = map[status] || [status, 'badge-gray'];
  return `<span class="badge ${cls}">${label}</span>`;
}

function modeBadge(mode) {
  const map = {
    text:  ['📝 Text',  'badge-purple'],
    voice: ['🎙️ Voice', 'badge-blue'],
    video: ['🎥 Video', 'badge-green'],
  };
  const [label, cls] = map[mode] || [mode, 'badge-gray'];
  return `<span class="badge ${cls}">${label}</span>`;
}

function scoreColor(score) {
  if (score >= 7.5) return '#10b981';
  if (score >= 5)   return '#f59e0b';
  return '#ef4444';
}
