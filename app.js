// Загрузка каталога
let catalog = {};
fetch('data/catalog.json').then(r => r.json()).then(data => catalog = data);

// Состояние сборки
const build = { cpu: null, motherboard: null, ram: null, gpu: null, psu: null, case: null, cooler: null, storage: null };

// Проверка совместимости
function checkCompatibility() {
  const errors = [];
  const warnings = [];
  const cpu = build.cpu, mb = build.motherboard, ram = build.ram;
  const gpu = build.gpu, psu = build.psu, case_ = build.case, cooler = build.cooler;

  // 1. Сокет CPU и MB
  if (cpu && mb && cpu.socket !== mb.socket) {
    errors.push(`Сокет CPU (${cpu.socket}) не совпадает с MB (${mb.socket})`);
  }

  // 2. Тип RAM и MB
  if (ram && mb && ram.type !== mb.ram_type) {
    errors.push(`RAM (${ram.type}) несовместима с MB (${mb.ram_type})`);
  }

  // 3. Длина GPU и корпус
  if (gpu && case_ && gpu.length > case_.max_gpu) {
    errors.push(`GPU (${gpu.length}мм) длиннее лимита корпуса (${case_.max_gpu}мм)`);
  }

  // 4. Высота кулера и корпус
  if (cooler && case_ && cooler.height > case_.max_cooler) {
    errors.push(`Кулер (${cooler.height}мм) выше лимита корпуса (${case_.max_cooler}мм)`);
  }

  // 5. Сокет кулера
  if (cooler && cpu && !cooler.sockets.includes(cpu.socket)) {
    errors.push(`Кулер не поддерживает сокет ${cpu.socket}`);
  }

  // 6. Блок питания
  if (psu && cpu && gpu) {
    const totalTdp = cpu.tdp + gpu.tdp + 100;
    if (totalTdp > psu.wattage * 0.8) {
      warnings.push(`Малый запас БП. TDP: ${totalTdp}W, БП: ${psu.wattage}W`);
    }
  }

  return { errors, warnings };
}

// Подсчет стоимости
function calcTotal() {
  return Object.values(build).reduce((sum, item) => sum + (item?.price || 0), 0);
}

// Обновление интерфейса
function render() {
  const { errors, warnings } = checkCompatibility();
  const total = calcTotal();

  document.getElementById('total-price').textContent = total.toLocaleString('ru-RU') + ' ₽';

  const statusEl = document.getElementById('status');
  statusEl.innerHTML = '';
  if (errors.length === 0 && Object.values(build).some(x => x)) {
    statusEl.innerHTML += '<div class="ok">[OK] Ошибок нет</div>';
  }
  errors.forEach(e => statusEl.innerHTML += `<div class="error">[✗] ${e}</div>`);
  warnings.forEach(w => statusEl.innerHTML += `<div class="warn">[!] ${w}</div>`);
}

// Выбор компонента
function selectItem(category, id) {
  const item = catalog[category].find(x => x.id === id);
  build[category] = item;
  render();
  updateSlotUI(category, item);
}

function updateSlotUI(category, item) {
  const slot = document.getElementById('slot-' + category);
  if (item) {
    slot.innerHTML = `<b>${item.name}</b><br><span class="muted">${item.price.toLocaleString('ru-RU')} ₽</span>`;
  } else {
    slot.innerHTML = '<span class="muted">не выбрано</span>';
  }
}

// Сохранение в localStorage
function saveBuild() {
  const name = prompt('Название сборки:');
  if (!name) return;
  const saved = JSON.parse(localStorage.getItem('builds') || '[]');
  saved.push({ name, build, date: new Date().toISOString() });
  localStorage.setItem('builds', JSON.stringify(saved));
  alert('Сохранено!');
}

// Копирование текста
function copyText() {
  let text = 'МОЯ СБОРКА ПК:\n\n';
  Object.entries(build).forEach(([slot, item]) => {
    if (item) text += `${slot.toUpperCase()}: ${item.name} — ${item.price.toLocaleString('ru-RU')} ₽\n`;
  });
  text += `\nИТОГО: ${calcTotal().toLocaleString('ru-RU')} ₽`;
  navigator.clipboard.writeText(text);
  alert('Скопировано в буфер обмена');
}