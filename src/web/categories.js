// Categories page logics

// ========================================
// Category Management
// ========================================

async function initializeCategories() {
  try {
    const fileInput = document.getElementById('category-file-input');
    
    if (fileInput) {
      fileInput.addEventListener('change', handleCategoryFileUpload);
    }
  } catch (error) {
    console.error('Categories init failed', error);
    showStatus(`Initialization error: ${error.message}`, true);
  }
}

async function handleCategoryFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await authenticatedFetch(`${API_BASE}/categories/import-yaml`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    alert(result.message || 'Kategorien erfolgreich importiert.');
    await loadCategoriesPage(1);
  } catch (error) {
    console.error('YAML import failed:', error);
    alert(`Fehler beim YAML-Import: ${error.message}`);
  } finally {
    event.target.value = '';
  }
}

async function fetchCategories() {
  const res = await authenticatedFetch(`${API_BASE}/categories/list`);
  const data = await res.json();
  return data.categories || [];
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

function getCategoryName(catId) {
  const cat = allCategories.find(c => c.id === catId);
  return cat ? cat.fullname : `ID: ${catId}`;
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
