// Shared app utilities
const API_BASE = '/api';

async function loadTheme() {
  try {
    const response = await fetch(`${API_BASE}/theme/css`);
    const data = await response.json();
    const el = document.getElementById('dynamic-theme');
    if (el) el.textContent = data.css;
  } catch (error) {
    console.error('Failed to load theme:', error);
  }
}

function setActiveNav(currentRoute) {
  document.querySelectorAll('.top-nav .nav-item').forEach(item => {
    item.classList.toggle('active', item.dataset.route === currentRoute);
  });
}

// Load shared top nav into placeholder
async function loadTopNav(currentRoute) {
  const placeholder = document.getElementById('top-nav');
  if (!placeholder) return;
  try {
    const res = await fetch('top_nav.html', { cache: 'no-cache' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const html = await res.text();
    placeholder.innerHTML = html;
    setActiveNav(currentRoute);
  } catch (e) {
    console.error('Failed to load top nav:', e);
  }
}

// Initialize theme on all pages
document.addEventListener('DOMContentLoaded', () => { loadTheme(); });
