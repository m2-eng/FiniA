// Shared app utilities
const API_BASE = '/api';

// Theme Management
function initTheme() {
  // Load saved theme or default to light
  const savedTheme = localStorage.getItem('theme') || 'light';
  applyTheme(savedTheme);
  updateThemeIcon(savedTheme);
}

function applyTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
  localStorage.setItem('theme', theme);
}

function toggleTheme() {
  const currentTheme = localStorage.getItem('theme') || 'light';
  const newTheme = currentTheme === 'light' ? 'dark' : 'light';
  applyTheme(newTheme);
  updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
  const icon = document.getElementById('theme-icon');
  if (icon) {
    icon.textContent = theme === 'light' ? '🌙' : '☀️';
  }
}

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
});

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

// Load year dropdown options
async function loadYearDropdown() {
  try {
    const response = await fetch(`${API_BASE}/years/`);
    const data = await response.json();
    const yearSelector = document.getElementById('year-selector');
    
    if (!yearSelector || !data.years || data.years.length === 0) return;
    
    // Clear existing options
    yearSelector.innerHTML = '';
    
    // Get currently selected year from localStorage or use first year (newest)
    const savedYear = localStorage.getItem('selectedYear');
    const defaultYear = savedYear || data.years[0].toString();
    
    // Add year options
    data.years.forEach(year => {
      const option = document.createElement('option');
      option.value = year;
      option.textContent = year;
      if (year.toString() === defaultYear) {
        option.selected = true;
      }
      yearSelector.appendChild(option);
    });
    
    // Save default year if none was saved before
    if (!savedYear && data.years.length > 0) {
      localStorage.setItem('selectedYear', data.years[0].toString());
    }
    
    // Add change event listener
    yearSelector.addEventListener('change', (e) => {
      const selectedYear = e.target.value;
      if (selectedYear) {
        localStorage.setItem('selectedYear', selectedYear);
        // Trigger custom event for year change
        window.dispatchEvent(new CustomEvent('yearChanged', { detail: { year: selectedYear } }));
      }
    });
    
  } catch (error) {
    console.error('Failed to load years:', error);
  }
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
    
    // Add event listener to theme toggle button after nav is loaded
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', toggleTheme);
    }
  } catch (e) {
    console.error('Failed to load top nav:', e);
  }
}

// Initialize theme on all pages
document.addEventListener('DOMContentLoaded', () => { loadTheme(); });
