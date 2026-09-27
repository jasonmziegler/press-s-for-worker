let modelRequestPending = false;
let modelRefreshTimer;
let modelRefreshPending = false;
const switchButton = document.getElementById('model-switch');
switchButton.style.cssText = 'padding:9px 16px;margin-top:8px;border:1px solid #336078;border-radius:4px;background:#183c50;color:#66ccff;font:inherit;cursor:pointer';
const refreshButton = document.createElement('button');
refreshButton.type = 'button';
refreshButton.textContent = 'Refresh models';
refreshButton.style.cssText = switchButton.style.cssText + ';margin-left:8px';
refreshButton.title = 'Check for models downloaded or changed in LM Studio';
switchButton.after(refreshButton);
refreshButton.addEventListener('click', () => refreshModels());
async function refreshModels() {
  if (modelRefreshPending) return;
  clearTimeout(modelRefreshTimer);
  modelRefreshPending = true;
  refreshButton.disabled = true;
  const status = document.getElementById('model-status');
  try {
    const response = await fetch('/api/models');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'LM Studio unavailable');
    const select = document.getElementById('model-select');
    const selected = select.value || data.state.model;
    const entries = data.models.filter(m => m.type === 'llm');
    const signature = JSON.stringify(entries);
    if (select.dataset.signature !== signature) {
      select.replaceChildren(...entries.map(m => {
        const quant = m.quantization ? m.quantization.name : '';
        return new Option(`${m.display_name} ${quant || ''}${m.loaded_instances.length ? ' (loaded)' : ''}`, m.key);
      }));
      select.value = selected;
      if (!select.value && entries.length) select.value = entries[0].key;
      select.dataset.signature = signature;
    }
    document.getElementById('active-model').textContent = data.state.model;
    const interrupted = data.state.paused && !data.state.switching;
    status.textContent = [data.state.phase, data.state.error,
      interrupted ? 'Select a model and switch to recover and resume.' : ''].filter(Boolean).join(' — ');
    document.getElementById('model-switch').disabled = modelRequestPending || data.state.switching;
    select.disabled = data.state.switching;
    document.getElementById('model-context').disabled = data.state.switching;
    // Idle dashboards make no recurring model requests. Also resume monitoring
    // when the page is opened while another tab is already switching.
    if (data.state.switching) modelRefreshTimer = setTimeout(refreshModels, 3000);
  } catch (error) {
    status.textContent = `LM Studio connection error: ${error.message}`;
    document.getElementById('model-switch').disabled = true;
  } finally {
    modelRefreshPending = false;
    refreshButton.disabled = false;
  }
}
document.getElementById('model-switch').addEventListener('click', async () => {
  modelRequestPending = true;
  document.getElementById('model-switch').disabled = true;
  try {
    const response = await fetch('/api/models/switch', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({model: document.getElementById('model-select').value,
        context_length: Number(document.getElementById('model-context').value)})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Switch failed');
    modelRequestPending = false;
    await refreshModels();
  } catch (error) {
    document.getElementById('model-status').textContent = error.message;
  } finally {
    modelRequestPending = false;
  }
});
refreshModels();
