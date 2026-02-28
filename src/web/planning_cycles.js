// Planning cycle page logics

// ========================================
// Planning Cycles Management
// ========================================

async function fetchPlanningCycles() {
  try {
    const response = await authenticatedFetch('/api/settings/planning-cycles');
    const data = await response.json();
    planningCycles = data.planning_cycles || [];
    return planningCycles;
  } catch (error) {
    console.error('Error fetching planning cycles:', error);
    showPlanningCyclesStatus(`Fehler beim Laden: ${error.message}`, true);
    return [];
  }
}

function renderPlanningCyclesTable() {
  const tbody = document.getElementById('planning-cycles-tbody');
  if (!tbody) return;

  if (planningCycles.length === 0) {
    tbody.innerHTML = '<tr><td colspan="3" style="text-align: center;">Keine Zyklen vorhanden</td></tr>';
    return;
  }

  // Map for readable units
  const unitLabels = {
    'd': 'Tag(e)',
    'm': 'Monat(e)',
    'y': 'Jahr(e)'
  };

  tbody.innerHTML = planningCycles.map(pc => {
    const unitLabel = unitLabels[pc.periodUnit] || pc.periodUnit;
    const valueDisplay = pc.periodValue === 0 ? '-' : `${pc.periodValue} ${unitLabel}`;
    
    return `
    <tr data-cycle-id="${pc.id}">
      <td style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(pc.cycle)}</td>
      <td>${escapeHtml(valueDisplay)}</td>
      <td style="text-align: center;">
        <div style="display: inline-flex; gap: 4px; justify-content: center;">
          <button class="btn btn-sm" onclick="editPlanningCycle(${pc.id})">Bearbeiten</button>
          <button class="btn btn-sm btn-danger" onclick="deletePlanningCycle(${pc.id}, '${escapeHtml(pc.cycle)}')">Löschen</button>
        </div>
      </td>
    </tr>
    `;
  }).join('');
}

function showPlanningCyclesStatus(message, isError = false) {
  const status = document.getElementById('planning-cycles-status');
  if (!status) return;

  status.textContent = message;
  status.style.color = isError ? 'var(--color-red)' : 'var(--color-text)';

  setTimeout(() => {
    status.textContent = '';
  }, 5000);
}

async function addPlanningCycle(cycleName, periodValue, periodUnit) {
  const response = await authenticatedFetch('/api/settings/planning-cycles', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cycle: cycleName, periodValue, periodUnit })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

async function updatePlanningCycle(cycleId, cycleName, periodValue, periodUnit) {
  const response = await authenticatedFetch(`/api/settings/planning-cycles/${cycleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cycle: cycleName, periodValue, periodUnit })
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

async function deletePlanningCycleAPI(cycleId) {
  const response = await authenticatedFetch(`/api/settings/planning-cycles/${cycleId}`, {
    method: 'DELETE'
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || `HTTP ${response.status}`);
  }

  return response.json();
}

function showAddPlanningCycleDialog() {
  showFormModal({
    title: 'Zyklus hinzufügen',
    fields: [
      { id: 'cycle', label: 'Zyklus-Name', type: 'text', required: true, value: '' },
      { id: 'periodValue', label: 'Periodenwert', type: 'number', required: true, value: '1' },
      { id: 'periodUnit', label: 'Einheit', type: 'select', required: true, value: 'm', options: [
        { value: 'd', label: 'Tag(e)' },
        { value: 'm', label: 'Monat(e)' },
        { value: 'y', label: 'Jahr(e)' }
      ]}
    ],
    onSubmit: async (values) => {
      const cycleName = values.cycle;
      const periodValue = parseFloat(values.periodValue);
      const periodUnit = values.periodUnit;

      if (planningCycles.some(pc => pc.cycle.toLowerCase() === cycleName.toLowerCase())) {
        showPlanningCyclesStatus('Dieser Zyklus existiert bereits.', true);
        return false;
      }

      try {
        const result = await addPlanningCycle(cycleName, periodValue, periodUnit);
        planningCycles.push({
          id: result.id,
          cycle: result.cycle,
          periodValue: result.periodValue,
          periodUnit: result.periodUnit,
          dateImport: new Date().toISOString()
        });
        showPlanningCyclesStatus('Zyklus hinzugefügt.');
        renderPlanningCyclesTable();
        return true;
      } catch (err) {
        console.error('Add failed:', err);
        showPlanningCyclesStatus(`Fehler beim Hinzufügen: ${err.message}`, true);
        return false;
      }
    }
  });
}

function editPlanningCycle(cycleId) {
  const cycle = planningCycles.find(pc => pc.id === cycleId);
  if (!cycle) {
    showPlanningCyclesStatus('Zyklus nicht gefunden.', true);
    return;
  }

  showFormModal({
    title: 'Zyklus bearbeiten',
    fields: [
      { id: 'cycle', label: 'Zyklus-Name', type: 'text', required: true, value: cycle.cycle },
      { id: 'periodValue', label: 'Periodenwert', type: 'number', required: true, value: String(cycle.periodValue) },
      { id: 'periodUnit', label: 'Einheit', type: 'select', required: true, value: cycle.periodUnit, options: [
        { value: 'd', label: 'Tag(e)' },
        { value: 'm', label: 'Monat(e)' },
        { value: 'y', label: 'Jahr(e)' }
      ]}
    ],
    onSubmit: async (values) => {
      const newName = values.cycle;
      const periodValue = parseFloat(values.periodValue);
      const periodUnit = values.periodUnit;

      const duplicate = planningCycles.find(pc => pc.id !== cycleId && pc.cycle.toLowerCase() === newName.toLowerCase());
      if (duplicate) {
        showPlanningCyclesStatus('Ein anderer Zyklus mit diesem Namen existiert bereits.', true);
        return false;
      }

      try {
        await updatePlanningCycle(cycleId, newName, periodValue, periodUnit);
        cycle.cycle = newName;
        cycle.periodValue = periodValue;
        cycle.periodUnit = periodUnit;
        showPlanningCyclesStatus('Zyklus aktualisiert.');
        renderPlanningCyclesTable();
        return true;
      } catch (err) {
        console.error('Update failed:', err);
        showPlanningCyclesStatus(`Fehler beim Aktualisieren: ${err.message}`, true);
        return false;
      }
    }
  });
}

async function deletePlanningCycle(cycleId, cycleName) {
  if (!confirm(`Möchten Sie den Zyklus "${cycleName}" wirklich löschen?`)) {
    return;
  }

  try {
    await deletePlanningCycleAPI(cycleId);
    planningCycles = planningCycles.filter(pc => pc.id !== cycleId);
    showPlanningCyclesStatus('Zyklus gelöscht.');
    renderPlanningCyclesTable();
  } catch (err) {
    console.error('Delete failed:', err);
    showPlanningCyclesStatus(`Fehler beim Löschen: ${err.message}`, true);
  }
}

async function handlePlanningCycleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await authenticatedFetch(`${API_BASE}/settings/planning-cycles/import-yaml`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    const result = await response.json();
    alert(result.message || 'Zyklus erfolgreich importiert.');
    await fetchPlanningCycles();
    renderPlanningCyclesTable();
  } catch (error) {
    console.error('YAML import failed:', error);
    alert(`Fehler beim YAML-Import: ${error.message}`);
  } finally {
    event.target.value = '';
  }
}

async function initializePlanningCycles() {
  try {
    await fetchPlanningCycles();
    renderPlanningCyclesTable();

    const addBtn = document.getElementById('add-planning-cycle-btn');
    const reloadBtn = document.getElementById('reload-planning-cycles-btn');
    const fileInput = document.getElementById('planning-cycle-file-input');

    if (addBtn) {
      addBtn.addEventListener('click', showAddPlanningCycleDialog);
    }

    if (reloadBtn) {
      reloadBtn.addEventListener('click', async () => {
        await fetchPlanningCycles();
        renderPlanningCyclesTable();
        showPlanningCyclesStatus('Zyklen neu geladen.');
      });
    }

    if (fileInput) {
      fileInput.addEventListener('change', handlePlanningCycleFileUpload);
    }
  } catch (error) {
    console.error('Planning cycles init failed:', error);
    showPlanningCyclesStatus(`Initialisierungsfehler: ${error.message}`, true);
  }
}