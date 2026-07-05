// Загрузка каталога
let catalog = {};
fetch('data/catalog.json')
  .then(r => r.json())
  .then(data => {
    catalog = data;
    console.log('Каталог загружен:', Object.keys(catalog));
  })
  .catch(e => console.error('Ошибка загрузки каталога:', e));

// Состояние сборки
const build = { cpu: null, motherboard: null, ram: null, gpu: null, psu: null, case: null, cooler: null, storage: null };

// Проверка совместимости
function checkCompatibility() {
  const errors = [];
  const warnings = [];
  const cpu = build.cpu, mb = build.motherboard, ram = build.ram;
  const gpu = build.gpu, psu = build.psu, case_ = build.case, cooler = build.cooler;

  if (cpu && mb && cpu.socket !== mb.socket)
    errors.push(`Сокет CPU (${cpu.socket}) не совпадает с MB (${mb.socket})`);
  if (ram && mb && ram.type !== mb.ram_type)
    errors.push(`RAM (${ram.type}) несовместима с MB (${mb.ram_type})`);
  if (gpu && case_ && gpu.length > case_.max_gpu)
    errors.push(`GPU (${gpu.length}мм) длиннее лимита корпуса (${case_.max_gpu}мм)`);
  if (cooler && case_ && cooler.height > case_.max_cooler)
    errors.push(`Кулер (${cooler.height}мм) выше лимита корпуса (${case_.max_cooler}мм)`);
  if (cooler && cpu && !cooler.sockets.includes(cpu.socket))
    errors.push(`Кулер не поддерживает сокет ${cpu.socket}`);
  if (psu && cpu && gpu) {
    const totalTdp = cpu.tdp + gpu.tdp + 100;
    if (totalTdp > psu.wattage * 0.8)
      warnings.push(`Малый запас БП. TDP: ${totalTdp}W, БП: ${psu.wattage}W`);
  }
  return { errors, warnings };
}

function calcTotal() {
  return Object.values(build).reduce((sum, item) => sum + (item?.price || 0), 0);
}

function render() {
  const { errors, warnings } = checkCompatibility();
  const total = calcTotal();
  const priceEl = document.getElementById('total-price');
  const statusEl = document.getElementById('status');
  if (priceEl) priceEl.textContent = total.toLocaleString('ru-RU') + ' ₽';
  if (statusEl) {
    statusEl.innerHTML = '';
    if (errors.length === 0 && Object.values(build).some(x => x))
      statusEl.innerHTML += '<div class="ok">[OK] Ошибок нет</div>';
    errors.forEach(e => statusEl.innerHTML += `<div class="error">[✗] ${e}</div>`);
    warnings.forEach(w => statusEl.innerHTML += `<div class="warn">[!] ${w}</div>`);
  }
}

function selectItem(category, id) {
  if (!catalog[category]) return;
  const item = catalog[category].find(x => x.id === id);
  build[category] = item;
  render();
  updateSlotUI(category, item);
}

function updateSlotUI(category, item) {
  const slot = document.getElementById('slot-' + category);
  if (!slot) return;
  if (item)
    slot.innerHTML = `<b>${item.name}</b><br><span class="muted">${item.price.toLocaleString('ru-RU')} ₽</span>`;
  else
    slot.innerHTML = '<span class="muted">не выбрано</span>';
}

function saveBuild() {
  const name = prompt('Название сборки:');
  if (!name) return;
  const saved = JSON.parse(localStorage.getItem('builds') || '[]');
  saved.push({ name, build: { ...build }, date: new Date().toISOString() });
  localStorage.setItem('builds', JSON.stringify(saved));
  alert('Сохранено!');
  renderHistory();
}

function copyText() {
  let text = 'МОЯ СБОРКА ПК:\n\n';
  Object.entries(build).forEach(([slot, item]) => {
    if (item) text += `${slot.toUpperCase()}: ${item.name} — ${item.price.toLocaleString('ru-RU')} ₽\n`;
  });
  text += `\nИТОГО: ${calcTotal().toLocaleString('ru-RU')} ₽`;
  navigator.clipboard.writeText(text);
  alert('Скопировано в буфер обмена');
}

// История сборок
function renderHistory() {
  console.log('[renderHistory] вызван');
  const list = document.getElementById('builds-list');
  if (!list) {
    console.error('[renderHistory] builds-list не найден в DOM');
    return;
  }

  const saved = JSON.parse(localStorage.getItem('builds') || '[]');
  console.log('[renderHistory] сборок в памяти:', saved.length);

  if (saved.length === 0) {
    list.innerHTML = '<div class="empty-history">Пока нет сохранённых сборок</div>';
    return;
  }

  saved.sort((a, b) => new Date(b.date) - new Date(a.date));
  list.innerHTML = '';

  saved.forEach((item, index) => {
    const total = Object.values(item.build).reduce((sum, x) => sum + (x?.price || 0), 0);
    const itemsCount = Object.values(item.build).filter(x => x).length;
    const date = new Date(item.date).toLocaleDateString('ru-RU');

    const card = document.createElement('div');
    card.className = 'build-card';
    card.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:start">
        <h4 style="flex:1; margin:0">${item.name}</h4>
        <button class="delete-btn" onclick="event.stopPropagation(); deleteBuild(${index})" title="Удалить">[✗]</button>
      </div>
      <div class="muted">${date} • ${itemsCount} компонентов</div>
      <div class="price">${total.toLocaleString('ru-RU')} ₽</div>
    `;
    card.onclick = () => loadBuild(index);
    list.appendChild(card);
  });
  console.log('[renderHistory] отрисовано карточек:', saved.length);
}

function loadBuild(index) {
  const saved = JSON.parse(localStorage.getItem('builds') || '[]');
  const item = saved[index];
  if (!item || !confirm(`Загрузить сборку "${item.name}"?`)) return;
  Object.keys(build).forEach(slot => {
    build[slot] = item.build[slot] || null;
    updateSlotUI(slot, build[slot]);
  });
  render();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function deleteBuild(index) {
  const saved = JSON.parse(localStorage.getItem('builds') || '[]');
  const name = saved[index]?.name;
  if (!confirm(`Удалить сборку "${name}"?`)) return;
  saved.splice(index, 1);
  localStorage.setItem('builds', JSON.stringify(saved));
  renderHistory();
}

// Пресеты
let presets = {};
fetch('data/presets.json')
  .then(r => r.json())
  .then(data => { presets = data; renderPresets(); })
  .catch(() => console.log('presets.json не найден — это нормально'));

function renderPresets() {
  const container = document.getElementById('presets-buttons');
  if (!container) return;
  container.innerHTML = '';
  Object.entries(presets).forEach(([key, preset]) => {
    const btn = document.createElement('button');
    btn.textContent = `[ ${preset.name} ]`;
    btn.title = preset.description;
    btn.onclick = () => applyPreset(key);
    container.appendChild(btn);
  });
}

function applyPreset(key) {
  const preset = presets[key];
  if (!preset) return;
  if (!confirm(`Применить пресет "${preset.name}"?`)) return;
  Object.keys(build).forEach(slot => {
    const id = preset.items[slot];
    build[slot] = (id && catalog[slot]) ? catalog[slot].find(x => x.id === id) || null : null;
    updateSlotUI(slot, build[slot]);
  });
  render();
}

// === ГЛАВНОЕ: запускаем всё после полной загрузки DOM ===
document.addEventListener('DOMContentLoaded', () => {
  console.log('DOM готов');
  renderHistory();
  render();
});