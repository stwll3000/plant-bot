const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

const AUTH = "tma " + tg.initData;

let state = null;        // ответ GET /api/state
let currentTab = "all";  // "all" | property_id | "log"

// ---------- API ----------

async function api(path, options = {}) {
  const headers = { "Authorization": AUTH, ...(options.headers || {}) };
  // Для FormData браузер сам выставит multipart-заголовок с boundary
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch("/api" + path, { ...options, headers });
  if (res.status === 403) {
    showError("Ты пока не состоишь в семье.\nОткрой чат с ботом и нажми /start, чтобы создать семью или присоединиться по коду.");
    throw new Error("no_family");
  }
  if (res.status === 401) {
    showError("Не удалось подтвердить, что это ты. Открой приложение из чата с ботом.");
    throw new Error("unauthorized");
  }
  if (!res.ok) throw new Error("api_error_" + res.status);
  return res.json();
}

function askConfirm(message) {
  return new Promise((resolve) => {
    if (tg.showConfirm) tg.showConfirm(message, resolve);
    else resolve(window.confirm(message));
  });
}

function showError(text) {
  document.getElementById("tabs").classList.add("hidden");
  document.getElementById("content").classList.add("hidden");
  const screen = document.getElementById("error-screen");
  screen.classList.remove("hidden");
  document.getElementById("error-text").innerText = text;
}

// ---------- Загрузка и рендер ----------

async function load() {
  state = await api("/state");
  document.getElementById("family-name").innerText = "🏡 " + state.family.name;
  document.getElementById("family-code").innerText = "Код: " + state.family.invite_code;
  renderTabs();
  await renderContent();
}

function renderTabs() {
  const tabs = document.getElementById("tabs");
  tabs.innerHTML = "";
  addTab(tabs, "all", "🪴 Все растения");
  for (const prop of state.properties) {
    addTab(tabs, String(prop.id), prop.name);
  }
  addTab(tabs, "add-property", "+ Дом");
  addTab(tabs, "log", "📖 Журнал");
}

function addTab(container, id, label) {
  const btn = document.createElement("button");
  btn.className = "tab" + (currentTab === id ? " active" : "");
  btn.innerText = label;
  btn.onclick = async () => {
    if (id === "add-property") {
      openModal("Новый дом / квартира", [
        { key: "name", placeholder: "Например: Дача" },
      ], async (values) => {
        await api("/properties", { method: "POST", body: JSON.stringify(values) });
        await load();
      });
      return;
    }
    currentTab = id;
    renderTabs();
    await renderContent();
  };
  container.appendChild(btn);
}

async function renderContent() {
  const content = document.getElementById("content");
  content.innerHTML = "";

  if (currentTab === "log") return renderLog(content);

  const props = currentTab === "all"
    ? state.properties
    : state.properties.filter((p) => String(p.id) === currentTab);

  if (state.properties.length === 0) {
    content.innerHTML = `<div class="empty-hint">Начни с добавления дома или квартиры — кнопка «+ Дом» сверху 🏡</div>`;
    return;
  }

  for (const prop of props) {
    if (currentTab === "all") {
      const h = document.createElement("div");
      h.className = "section-header";
      h.innerHTML = `<h2>🏠 ${esc(prop.name)}</h2>`;
      content.appendChild(h);
    }

    for (const room of prop.rooms) {
      const header = document.createElement("div");
      header.className = "section-header";
      header.innerHTML = `<h2>${esc(room.name)}</h2>`;
      const roomActions = document.createElement("div");
      roomActions.className = "row-actions";
      const addPlantBtn = document.createElement("button");
      addPlantBtn.className = "btn secondary small";
      addPlantBtn.innerText = "+ растение";
      addPlantBtn.onclick = () => openAddPlant(room.id);
      roomActions.appendChild(addPlantBtn);
      const delRoomBtn = document.createElement("button");
      delRoomBtn.className = "btn secondary small danger";
      delRoomBtn.innerText = "🗑";
      delRoomBtn.onclick = async () => {
        const ok = await askConfirm(
          `Удалить комнату «${room.name}»? Все растения в ней тоже удалятся.`
        );
        if (!ok) return;
        await api(`/rooms/${room.id}`, { method: "DELETE" });
        await load();
      };
      roomActions.appendChild(delRoomBtn);
      header.appendChild(roomActions);
      content.appendChild(header);

      if (room.plants.length === 0) {
        const hint = document.createElement("div");
        hint.className = "muted";
        hint.style.marginBottom = "10px";
        hint.innerText = "Пока пусто";
        content.appendChild(hint);
      }
      for (const plant of room.plants) {
        content.appendChild(plantCard(plant));
      }
    }

    // Добавление комнаты — только в режиме конкретного property
    if (currentTab !== "all") {
      const addRoom = document.createElement("button");
      addRoom.className = "add-row";
      addRoom.innerText = "+ Добавить комнату";
      addRoom.onclick = () => openModal("Новая комната", [
        { key: "name", placeholder: "Например: Кухня" },
      ], async (values) => {
        await api("/rooms", {
          method: "POST",
          body: JSON.stringify({ ...values, property_id: Number(currentTab) }),
        });
        await load();
      });
      content.appendChild(addRoom);

      const delProp = document.createElement("button");
      delProp.className = "add-row danger";
      delProp.innerText = "🗑 Удалить этот дом";
      delProp.onclick = async () => {
        const ok = await askConfirm(
          `Удалить «${prop.name}» со всеми комнатами и растениями?`
        );
        if (!ok) return;
        await api(`/properties/${prop.id}`, { method: "DELETE" });
        currentTab = "all";
        await load();
      };
      content.appendChild(delProp);
    }
  }
}

const CARE_UI = {
  watering: { emoji: "💧", due: "Пора полить!", label: "Полив" },
  spraying: { emoji: "💦", due: "Пора опрыскать!", label: "Опрыскивание" },
};

function careUi(code, name) {
  return CARE_UI[code] || {
    emoji: "🪴",
    due: `Пора: ${(name || "").toLowerCase()}!`,
    label: name || "",
  };
}

function plantCard(plant) {
  const card = document.createElement("div");
  card.className = "plant-card";

  const photo = plant.photo_file_id
    ? `<img class="plant-photo" src="/api/photo/${plant.photo_file_id}?a=${encodeURIComponent(tg.initData)}" alt="">`
    : `<div class="plant-photo">🪴</div>`;

  const care = plant.care || [];
  const statusLines = care
    .map((c) => {
      const ui = careUi(c.code, c.name);
      if (c.due) return `<div class="plant-status due">${ui.due}</div>`;
      if (c.due_in_days === null) return "";
      const text =
        c.due_in_days === 0
          ? `${ui.label} сегодня`
          : `${ui.label} через ${c.due_in_days} ${plural(c.due_in_days, "день", "дня", "дней")}`;
      return `<div class="plant-status ok">${text}</div>`;
    })
    .join("");

  const last = plant.last_care
    ? `${careUi(plant.last_care.code, "").emoji} ${esc(plant.last_care.by)}, ${ago(plant.last_care.at)}`
    : "🕐 ухода ещё не было";

  card.innerHTML = `
    ${photo}
    <div class="plant-info" title="Настроить уход">
      <div class="plant-name">${esc(plant.name)}${plant.species ? ` <span class="muted">· ${esc(plant.species)}</span>` : ""}</div>
      ${statusLines}
      <div class="plant-last">${last}</div>
    </div>
  `;

  // Тап по фото (или заглушке) — загрузка нового фото
  const photoEl = card.querySelector(".plant-photo");
  photoEl.style.cursor = "pointer";
  photoEl.title = "Изменить фото";
  photoEl.onclick = () => uploadPhoto(plant.id);

  // Тап по названию — настройка интервалов ухода
  const infoEl = card.querySelector(".plant-info");
  infoEl.style.cursor = "pointer";
  infoEl.onclick = () => openEditSchedules(plant);

  const actions = document.createElement("div");
  actions.className = "card-actions";

  for (const c of care) {
    const ui = careUi(c.code, c.name);
    const btn = document.createElement("button");
    btn.className = "water-btn" + (c.due ? " due" : "");
    btn.innerText = ui.emoji;
    btn.title = c.name;
    btn.onclick = async () => {
      btn.disabled = true;
      await api(`/plants/${plant.id}/care/${c.code}`, { method: "POST" });
      if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
      await load();
    };
    actions.appendChild(btn);
  }

  const delBtn = document.createElement("button");
  delBtn.className = "water-btn danger";
  delBtn.innerText = "🗑";
  delBtn.title = "Удалить растение";
  delBtn.onclick = async () => {
    const ok = await askConfirm(`Удалить «${plant.name}»? История ухода тоже удалится.`);
    if (!ok) return;
    await api(`/plants/${plant.id}`, { method: "DELETE" });
    await load();
  };
  actions.appendChild(delBtn);

  card.appendChild(actions);
  return card;
}

function openEditSchedules(plant) {
  const care = plant.care || [];
  const watering = care.find((c) => c.code === "watering");
  const spraying = care.find((c) => c.code === "spraying");
  openModal(`Уход: ${plant.name}`, [
    {
      key: "watering_days",
      placeholder: "Полив раз в … дней",
      type: "number",
      value: watering ? watering.interval_days : "",
    },
    {
      key: "spraying_days",
      placeholder: "Опрыскивание раз в … дней (пусто — не нужно)",
      type: "number",
      value: spraying ? spraying.interval_days : "",
    },
  ], async (values) => {
    await api(`/plants/${plant.id}/schedules`, {
      method: "PUT",
      body: JSON.stringify({
        watering_days: Number(values.watering_days) || 7,
        spraying_days: Number(values.spraying_days) || null,
      }),
    });
    await load();
  });
}

function uploadPhoto(plantId) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.onchange = async () => {
    const file = input.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append("file", file);
    try {
      await api(`/plants/${plantId}/photo`, { method: "POST", body: formData });
      if (tg.HapticFeedback) tg.HapticFeedback.notificationOccurred("success");
    } catch (e) {
      if (tg.showAlert) tg.showAlert("Не удалось загрузить фото 😕");
    }
    await load();
  };
  input.click();
}

async function renderLog(content) {
  const data = await api("/logs");
  if (data.logs.length === 0) {
    content.innerHTML = `<div class="empty-hint">Журнал пока пуст 🌵</div>`;
    return;
  }
  for (const entry of data.logs) {
    const div = document.createElement("div");
    div.className = "log-entry";
    const emoji = careUi(entry.care_code, entry.care_type).emoji;
    div.innerHTML = `
      ${emoji} <b>${esc(entry.user)}</b> — ${esc(entry.plant)}
      <div class="muted">${esc(entry.property)} · ${esc(entry.room)} · ${fmtDate(entry.at)}</div>
    `;
    content.appendChild(div);
  }
}

function openAddPlant(roomId) {
  openModal("Новое растение", [
    { key: "name", placeholder: "Название, например: Монстера" },
    { key: "species", placeholder: "Вид (необязательно)" },
    { key: "interval_days", placeholder: "Полив раз в … дней (например: 7)", type: "number" },
    { key: "spraying_days", placeholder: "Опрыскивание раз в … дней (необязательно)", type: "number" },
  ], async (values) => {
    await api("/plants", {
      method: "POST",
      body: JSON.stringify({
        room_id: roomId,
        name: values.name,
        species: values.species || null,
        interval_days: Number(values.interval_days) || 7,
        spraying_days: Number(values.spraying_days) || null,
      }),
    });
    await load();
  });
}

// ---------- Модальное окно ----------

let modalSubmit = null;

function openModal(title, fields, onSubmit) {
  document.getElementById("modal-title").innerText = title;
  const box = document.getElementById("modal-fields");
  box.innerHTML = "";
  for (const f of fields) {
    const input = document.createElement("input");
    input.id = "field-" + f.key;
    input.placeholder = f.placeholder;
    if (f.type) input.type = f.type;
    if (f.value !== undefined && f.value !== "") input.value = f.value;
    box.appendChild(input);
  }
  modalSubmit = async () => {
    const values = {};
    for (const f of fields) {
      values[f.key] = document.getElementById("field-" + f.key).value.trim();
    }
    if (!values[fields[0].key]) return; // первое поле обязательно
    closeModal();
    await onSubmit(values);
  };
  document.getElementById("modal-backdrop").classList.remove("hidden");
  box.querySelector("input").focus();
}

function closeModal() {
  document.getElementById("modal-backdrop").classList.add("hidden");
}

document.getElementById("modal-save").onclick = () => modalSubmit && modalSubmit();
document.getElementById("modal-backdrop").onclick = (e) => {
  if (e.target.id === "modal-backdrop") closeModal();
};

// ---------- Хелперы ----------

function esc(s) {
  const div = document.createElement("div");
  div.innerText = s ?? "";
  return div.innerHTML;
}

function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

function ago(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 60) return "только что";
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} ${plural(hours, "час", "часа", "часов")} назад`;
  const days = Math.floor(hours / 24);
  return `${days} ${plural(days, "день", "дня", "дней")} назад`;
}

function fmtDate(iso) {
  return new Date(iso).toLocaleString("ru-RU", {
    day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  });
}

// ---------- Старт ----------

load().catch((e) => {
  if (!["no_family", "unauthorized"].includes(e.message)) {
    showError("Что-то пошло не так. Попробуй открыть приложение заново.");
  }
});
