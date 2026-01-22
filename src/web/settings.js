// Settings page logic

// Global variables (shared with category_automation.js)

// Auth-Check: User muss eingeloggt sein
requireAuth();

window.allCategories = [];
let currentSettings = [];  // Array of {category_id, type}

// Modal helper functions
function closeModal() {
  const modal = document.getElementById('formModal');
  if (modal) modal.style.display = 'none';
}

function showFormModal({ title, fields, onSubmit }) {
  const modal = document.getElementById('formModal');
  const modalTitle = document.getElementById('modalTitle');
  const modalBody = document.getElementById('modalBody');
  const modalSaveBtn = document.getElementById('modalSaveBtn');
  const modalCancelBtn = document.getElementById('modalCancelBtn');
  const modalCloseBtn = document.getElementById('modalCloseBtn');

  if (!modal || !modalTitle || !modalBody || !modalSaveBtn) {
    console.error('Modal elements missing');
    return;
  }

  modalTitle.textContent = title;
  modalBody.innerHTML = '';

  fields.forEach((field) => {
    const group = document.createElement('div');
    group.className = 'form-group';

    const label = document.createElement('label');
    label.textContent = field.label;
    label.setAttribute('for', `modal-input-${field.id}`);

    let control;
    if (field.type === 'select') {
      control = document.createElement('select');
      control.className = 'input-sm';
      control.id = `modal-input-${field.id}`;
      if (field.options && Array.isArray(field.options)) {
        field.options.forEach(opt => {
          const optionEl = document.createElement('option');
          optionEl.value = opt.value;
          optionEl.textContent = opt.label;
          if (String(opt.value) === String(field.value || '')) {
            optionEl.selected = true;
          }
          control.appendChild(optionEl);
        });
      }
    } else {
      control = document.createElement('input');
      control.id = `modal-input-${field.id}`;
      control.type = field.type || 'text';
      control.className = 'input-sm';
      if (field.value !== undefined && field.value !== null) {
        control.value = field.value;
      }
    }

    if (field.required) {
      control.required = true;
    }

    group.appendChild(label);
    group.appendChild(control);
    modalBody.appendChild(group);
  });

  modalSaveBtn.onclick = async () => {
    const values = {};
    for (const field of fields) {
      const input = document.getElementById(`modal-input-${field.id}`);
      if (!input) continue;
      values[field.id] = input.value.trim();
      if (field.required && !values[field.id]) {
        input.focus();
        return;
      }
    }

    const shouldClose = await onSubmit(values);
    if (shouldClose !== false) {
      closeModal();
    }
  };

  if (modalCancelBtn) modalCancelBtn.onclick = closeModal;
  if (modalCloseBtn) modalCloseBtn.onclick = closeModal;

  modal.onclick = (event) => {
    if (event.target === modal) closeModal();
  };

  modal.style.display = 'block';
}

// API functions
async function fetchCategories() {
  const res = await authenticatedFetch(`${API_BASE}/categories/list`);
  const data = await res.json();
  return data.categories || [];
}

async function fetchSettings() {
  const res = await authenticatedFetch(`${API_BASE}/settings/shares-tx-categories`);
  const data = await res.json();
  return data.categories || [];
}

async function addSetting(categoryId, type) {
  const res = await authenticatedFetch(`${API_BASE}/settings/shares-tx-categories`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category_id: categoryId, type: type })
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error: ${error}`);
  }
  return res.json();
}

async function deleteSetting(categoryId, type) {
  const res = await authenticatedFetch(`${API_BASE}/settings/shares-tx-categories`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ category_id: categoryId, type: type })
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error: ${error}`);
  }
  return res.json();
}

// UI functions
function showStatus(msg, isError = false) {
  const el = document.getElementById('settings-status');
  if (!el) return;
  el.textContent = msg;
  el.style.color = isError ? 'var(--color-danger)' : 'var(--color-text)';
}

function getCategoryName(catId) {
  const cat = allCategories.find(c => c.id === catId);
  return cat ? cat.fullname : `ID: ${catId}`;
}

function getTypeLabel(type) {
  const labels = { buy: 'Kauf', sell: 'Verkauf', dividend: 'Dividende' };
  return labels[type] || type;
}

function renderTable() {
  const tbody = document.getElementById('categories-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  if (currentSettings.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">Keine Kategorien konfiguriert.</td></tr>';
    return;
  }

  currentSettings.forEach(setting => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td style="text-align: left;">${getCategoryName(setting.category_id)}</td>
      <td style="text-align: center;">${getTypeLabel(setting.type)}</td>
      <td style="text-align: center;">
        <button class="action-btn delete" data-id="${setting.category_id}" data-type="${setting.type}">Löschen</button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll('.action-btn.delete').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.getAttribute('data-id'), 10);
      const type = btn.getAttribute('data-type');
      removeCategory(id, type);
    });
  });
}

async function removeCategory(catId, type) {
  if (!confirm(`Kategorie "${getCategoryName(catId)}" (${getTypeLabel(type)}) wirklich entfernen?`)) return;
  
  try {
    await deleteSetting(catId, type);
    currentSettings = currentSettings.filter(s => !(s.category_id === catId && s.type === type));
    showStatus('Kategorie entfernt.');
    renderTable();
  } catch (err) {
    console.error('Remove failed:', err);
    showStatus(`Fehler beim Entfernen: ${err.message}`, true);
  }
}

function showAddCategoryDialog() {
  const usedCombinations = currentSettings.map(s => `${s.category_id}_${s.type}`);
  const availableCategories = allCategories.filter(cat => {
    return ['buy', 'sell', 'dividend'].some(type => 
      !usedCombinations.includes(`${cat.id}_${type}`)
    );
  });

  if (availableCategories.length === 0) {
    alert('Alle Kategorien sind bereits für alle Typen zugewiesen.');
    return;
  }

  const categoryOptions = availableCategories.map(cat => ({
    value: cat.id,
    label: cat.fullname
  }));

  const typeOptions = [
    { value: 'buy', label: 'Kauf' },
    { value: 'sell', label: 'Verkauf' },
    { value: 'dividend', label: 'Dividende' }
  ];

  showFormModal({
    title: 'Kategorie hinzufügen',
    fields: [
      { id: 'category', label: 'Kategorie', type: 'select', required: true, options: categoryOptions },
      { id: 'type', label: 'Typ', type: 'select', required: true, options: typeOptions }
    ],
    onSubmit: async (values) => {
      const catId = parseInt(values.category, 10);
      const type = values.type;

      if (currentSettings.some(s => s.category_id === catId && s.type === type)) {
        showStatus('Diese Kombination existiert bereits.', true);
        return false;
      }

      try {
        await addSetting(catId, type);
        currentSettings.push({ category_id: catId, type: type });
        showStatus('Kategorie hinzugefügt.');
        renderTable();
        return true;
      } catch (err) {
        console.error('Add failed:', err);
        showStatus(`Fehler beim Hinzufügen: ${err.message}`, true);
        return false;
      }
    }
  });
}

// Init
async function initSettingsPage() {
  loadTopNav('settings');

  try {
    [allCategories, currentSettings] = await Promise.all([
      fetchCategories(),
      fetchSettings()
    ]);

    renderTable();

    const addBtn = document.getElementById('add-category-btn');
    if (addBtn) {
      addBtn.addEventListener('click', showAddCategoryDialog);
    }

  } catch (error) {
    console.error('Settings init failed', error);
    showStatus(`Fehler beim Laden: ${error.message}`, true);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  initSettingsPage();
});
