// ZiriZiriDTP Client Application Logic

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Migrate legacy data from localStorage if existing
  await migrateFromLocalStorage();

  // State
  let currentTab = "todo";
  let debounceTimer = null;
  let selectedImageFile = null;

  const defaultTodos = [
    { text: "牛乳 1本", checked: false },
    { text: "食パン (6枚切り)", checked: false },
    { text: "たまご 1パック", checked: true },
    { text: "感熱ロール紙 予備", checked: false },
  ];

  const defaultRoutes = [
    {
      name: "海老名SA",
      location: "海老名SA 下り",
      note: "09:30 集合・朝食・給油",
      checked: false,
      action: "navigate",
    },
    {
      name: "大観山展望台",
      location: "アネスト岩田 スカイラウンジ",
      note: "絶景フォトスポット＆休憩",
      checked: false,
      action: "navigate",
    },
    {
      name: "修善寺温泉 街歩き",
      location: "修善寺温泉 竹林の小径",
      note: "温泉街散策とお昼ご飯",
      checked: false,
      action: "search",
    },
  ];

  let todoItems = (await dbGet("ziriziri_todos")) || defaultTodos;
  let routeMode = (await dbGet("ziriziri_route_mode")) || "driving";
  let routeItems = (await dbGet("ziriziri_route_items")) || defaultRoutes;

  // DOM Elements
  const tabs = document.querySelectorAll(".tab-btn");
  const tabPanes = document.querySelectorAll(".tab-pane");
  const previewImg = document.getElementById("previewImg");
  const btnPrint = document.getElementById("btnPrint");
  const printModal = document.getElementById("printModal");
  const modalText = document.getElementById("modalText");
  const statusBadge = document.getElementById("statusBadge");
  const statusText = document.getElementById("statusText");
  const statusDot = document.getElementById("statusDot");

  // Route Elements
  const routeTitle = document.getElementById("routeTitle");
  const btnLoadRouteSample = document.getElementById("btnLoadRouteSample");
  const routeModeChips = document.querySelectorAll(".route-mode-chip");
  const routeSpotName = document.getElementById("routeSpotName");
  const routeSpotLocation = document.getElementById("routeSpotLocation");
  const routeSpotNote = document.getElementById("routeSpotNote");
  const btnAddRouteSpot = document.getElementById("btnAddRouteSpot");
  const btnClearCompletedRoutes = document.getElementById("btnClearCompletedRoutes");
  const btnClearAllRoutes = document.getElementById("btnClearAllRoutes");
  const routeList = document.getElementById("routeList");

  // TODO elements
  const todoTitle = document.getElementById("todoTitle");
  const todoInput = document.getElementById("todoInput");
  const btnAddTodo = document.getElementById("btnAddTodo");
  const todoList = document.getElementById("todoList");
  const btnClearCompletedTodos = document.getElementById("btnClearCompletedTodos");
  const btnClearAllTodos = document.getElementById("btnClearAllTodos");

  // QR Attachment elements
  const btnToggleQrInput = document.getElementById("btnToggleQrInput");
  const qrToggleIcon = document.getElementById("qrToggleIcon");
  const qrAttachPanel = document.getElementById("qrAttachPanel");
  const qrPresetChips = document.querySelectorAll(".qr-preset-chip");
  const todoQrData = document.getElementById("todoQrData");
  const qrGuideTooltip = document.getElementById("qrGuideTooltip");

  let activeQrType = "url";
  const qrPresets = {
    url: {
      placeholder: "https://...（商品ページ・クラファン・レシピ等）",
      tooltip: "💡 商品詳細やレシピ動画のURLを入れておくと、売り場でスマホから即開けます",
      badge: "🔗 URL",
    },
    map: {
      placeholder: "https://maps.app.goo.gl/... または 住所・店名",
      tooltip: "💡 Googleマップの共有URLや住所を入れると、スキャンしてすぐルート案内が始まります",
      badge: "📍 地図",
    },
    memo: {
      placeholder: "例: E26口金・60W形相当、カーテン幅100丈198cm、足24.5cm",
      tooltip: "💡 長文の型番やサイズ控えを入れておくと、紙面を圧迫せずスマホで正確にコピーできます",
      badge: "📝 メモ",
    },
  };

  // Text elements
  const freeText = document.getElementById("freeText");
  const textSize = document.getElementById("textSize");
  const textAlign = document.getElementById("textAlign");
  const textBold = document.getElementById("textBold");
  const btnClearText = document.getElementById("btnClearText");

  // Image elements
  const imageInput = document.getElementById("imageInput");
  const imageDither = document.getElementById("imageDither");
  const imageContrast = document.getElementById("imageContrast");
  const contrastVal = document.getElementById("contrastVal");

  // Common print settings
  const printDensity = document.getElementById("printDensity");
  const printFeed = document.getElementById("printFeed");
  const chkShowDate = document.getElementById("chkShowDate");
  const selDatePos = document.getElementById("selDatePos");
  const chkCutLine = document.getElementById("chkCutLine");

  // Backup / Restore elements
  const btnExportJson = document.getElementById("btnExportJson");
  const btnImportJson = document.getElementById("btnImportJson");
  const fileImportJson = document.getElementById("fileImportJson");

  // ─────────────────────────────────────────────────────────
  // Restore State from IndexedDB
  // ─────────────────────────────────────────────────────────
  // TODO Title
  const savedTodoTitle = await dbGet("ziriziri_todo_title");
  if (savedTodoTitle !== null && todoTitle) {
    todoTitle.value = savedTodoTitle;
  }

  // Route Title & Mode
  const savedRouteTitle = await dbGet("ziriziri_route_title");
  if (savedRouteTitle !== null && routeTitle) {
    routeTitle.value = savedRouteTitle;
  }
  if (routeModeChips && routeModeChips.length > 0) {
    routeModeChips.forEach((chip) => {
      chip.classList.toggle("active", chip.dataset.mode === routeMode);
    });
  }

  // Free Text & Text Options
  const savedMemoText = await dbGet("ziriziri_memo_text");
  if (savedMemoText !== null && freeText) {
    freeText.value = savedMemoText;
  }
  const savedMemoSize = await dbGet("ziriziri_memo_size");
  if (savedMemoSize !== null && textSize) {
    textSize.value = savedMemoSize;
  }
  const savedMemoAlign = await dbGet("ziriziri_memo_align");
  if (savedMemoAlign !== null && textAlign) {
    textAlign.value = savedMemoAlign;
  }
  const savedMemoBold = await dbGet("ziriziri_memo_bold");
  if (savedMemoBold !== null && textBold) {
    textBold.checked = savedMemoBold === true || savedMemoBold === "true";
  }

  // Print options
  const savedShowDate = await dbGet("ziriziri_opt_show_date");
  if (savedShowDate !== null && chkShowDate) chkShowDate.checked = savedShowDate === true || savedShowDate === "true";
  const savedDatePos = await dbGet("ziriziri_opt_date_pos");
  if (savedDatePos !== null && selDatePos) selDatePos.value = savedDatePos;
  const savedCutLine = await dbGet("ziriziri_opt_cut_line");
  if (savedCutLine !== null && chkCutLine) chkCutLine.checked = savedCutLine === true || savedCutLine === "true";
  const savedDensity = await dbGet("ziriziri_opt_density");
  if (savedDensity !== null && printDensity) printDensity.value = savedDensity;
  const savedFeed = await dbGet("ziriziri_opt_feed");
  if (savedFeed !== null && printFeed) printFeed.value = savedFeed;

  // Active Tab
  const savedTab = await dbGet("ziriziri_active_tab");
  if (savedTab && document.getElementById(`pane-${savedTab}`)) {
    currentTab = savedTab;
  }

  if (chkShowDate) {
    chkShowDate.addEventListener("change", () => {
      dbSet("ziriziri_opt_show_date", chkShowDate.checked);
      requestPreview();
    });
  }
  if (selDatePos) {
    selDatePos.addEventListener("change", () => {
      dbSet("ziriziri_opt_date_pos", selDatePos.value);
      requestPreview();
    });
  }
  if (chkCutLine) {
    chkCutLine.addEventListener("change", () => {
      dbSet("ziriziri_opt_cut_line", chkCutLine.checked);
      requestPreview();
    });
  }
  if (printDensity) {
    printDensity.addEventListener("change", () => {
      dbSet("ziriziri_opt_density", printDensity.value);
    });
  }
  if (printFeed) {
    printFeed.addEventListener("change", () => {
      dbSet("ziriziri_opt_feed", printFeed.value);
    });
  }

  // ─────────────────────────────────────────────────────────
  // Backup & Restore Events
  // ─────────────────────────────────────────────────────────
  if (btnExportJson) {
    btnExportJson.addEventListener("click", () => {
      exportBackupFile();
    });
  }
  if (btnImportJson && fileImportJson) {
    btnImportJson.addEventListener("click", () => {
      fileImportJson.click();
    });
    fileImportJson.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async (evt) => {
        try {
          const data = JSON.parse(evt.target.result);
          await importBackupData(data);
          alert("データを復元しました。画面を再読み込みします。");
          window.location.reload();
        } catch (err) {
          alert("バックアップファイルの復元に失敗しました: " + err.message);
        }
      };
      reader.readAsText(file);
      fileImportJson.value = "";
    });
  }

  // ─────────────────────────────────────────────────────────
  // Tab Navigation
  // ─────────────────────────────────────────────────────────
  function switchTab(tabName) {
    currentTab = tabName;
    dbSet("ziriziri_active_tab", tabName);
    tabs.forEach((t) => t.classList.toggle("active", t.dataset.tab === tabName));
    tabPanes.forEach((p) => p.classList.toggle("active", p.id === `pane-${tabName}`));
    requestPreview();
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      switchTab(tab.dataset.tab);
    });
  });

  // Apply initial active tab
  switchTab(currentTab);

  // ─────────────────────────────────────────────────────────
  // Route Management & Navigation Actions
  // ─────────────────────────────────────────────────────────
  function saveRoutes() {
    dbSet("ziriziri_route_items", routeItems);
  }

  function renderRouteList() {
    if (!routeList) return;
    routeList.innerHTML = "";

    if (routeItems.length === 0) {
      const emptyDiv = document.createElement("div");
      emptyDiv.className = "todo-empty-state";
      emptyDiv.textContent = "📍 経由地・目的地がまだありません。「スポット追加」から登録してください。";
      routeList.appendChild(emptyDiv);
      return;
    }

    routeItems.forEach((itm, idx) => {
      const card = document.createElement("div");
      card.className = `route-item-card ${itm.checked ? "checked" : ""}`;

      // Step Number
      const stepBadge = document.createElement("div");
      stepBadge.className = "route-step-num";
      stepBadge.textContent = `[${String(idx + 1).padStart(2, "0")}]`;

      // Checkbox
      const chk = document.createElement("input");
      chk.type = "checkbox";
      chk.className = "route-item-checkbox";
      chk.checked = !!itm.checked;
      chk.addEventListener("change", () => {
        itm.checked = chk.checked;
        saveRoutes();
        card.classList.toggle("checked", chk.checked);
        requestPreview();
      });

      // Body (name, note, tag)
      const body = document.createElement("div");
      body.className = "route-item-body";

      const nameDiv = document.createElement("div");
      nameDiv.className = "route-item-name";
      nameDiv.textContent = itm.name;
      body.appendChild(nameDiv);

      if (itm.note) {
        const noteDiv = document.createElement("div");
        noteDiv.className = "route-item-note";
        noteDiv.textContent = itm.note;
        body.appendChild(noteDiv);
      }

      const metaDiv = document.createElement("div");
      metaDiv.className = "route-item-meta";

      const tag = document.createElement("span");
      tag.className = `route-item-tag ${itm.action === "navigate" ? "nav" : "search"}`;
      tag.textContent = itm.action === "navigate" ? "🚀 ナビ直通" : "📍 地図詳細";
      metaDiv.appendChild(tag);

      if (itm.location && itm.location !== itm.name) {
        const locSpan = document.createElement("span");
        locSpan.className = "route-item-note";
        locSpan.textContent = `(${itm.location})`;
        metaDiv.appendChild(locSpan);
      }

      body.appendChild(metaDiv);

      // Actions (Move Up, Move Down, Delete)
      const actions = document.createElement("div");
      actions.className = "route-item-actions";

      if (idx > 0) {
        const btnUp = document.createElement("button");
        btnUp.type = "button";
        btnUp.className = "btn-icon-sm";
        btnUp.title = "上へ移動";
        btnUp.textContent = "▲";
        btnUp.addEventListener("click", () => {
          const temp = routeItems[idx - 1];
          routeItems[idx - 1] = routeItems[idx];
          routeItems[idx] = temp;
          saveRoutes();
          renderRouteList();
          requestPreview();
        });
        actions.appendChild(btnUp);
      }

      if (idx < routeItems.length - 1) {
        const btnDown = document.createElement("button");
        btnDown.type = "button";
        btnDown.className = "btn-icon-sm";
        btnDown.title = "下へ移動";
        btnDown.textContent = "▼";
        btnDown.addEventListener("click", () => {
          const temp = routeItems[idx + 1];
          routeItems[idx + 1] = routeItems[idx];
          routeItems[idx] = temp;
          saveRoutes();
          renderRouteList();
          requestPreview();
        });
        actions.appendChild(btnDown);
      }

      const btnDel = document.createElement("button");
      btnDel.type = "button";
      btnDel.className = "btn-icon-sm danger";
      btnDel.title = "削除";
      btnDel.textContent = "✕";
      btnDel.addEventListener("click", () => {
        routeItems.splice(idx, 1);
        saveRoutes();
        renderRouteList();
        requestPreview();
      });
      actions.appendChild(btnDel);

      card.appendChild(stepBadge);
      card.appendChild(chk);
      card.appendChild(body);
      card.appendChild(actions);

      routeList.appendChild(card);
    });
  }

  // Route Title input
  if (routeTitle) {
    routeTitle.addEventListener("input", () => {
      dbSet("ziriziri_route_title", routeTitle.value);
      requestPreview();
    });
  }

  // Route Mode selection
  if (routeModeChips && routeModeChips.length > 0) {
    routeModeChips.forEach((chip) => {
      chip.addEventListener("click", () => {
        routeMode = chip.dataset.mode;
        dbSet("ziriziri_route_mode", routeMode);
        routeModeChips.forEach((c) => c.classList.toggle("active", c === chip));
        requestPreview();
      });
    });
  }

  // Add Route Spot
  function addRouteSpot() {
    const name = routeSpotName ? routeSpotName.value.trim() : "";
    if (!name) {
      if (routeSpotName) routeSpotName.focus();
      return;
    }
    const location = (routeSpotLocation && routeSpotLocation.value.trim()) || name;
    const note = routeSpotNote ? routeSpotNote.value.trim() : "";
    const actionRadio = document.querySelector('input[name="routeActionType"]:checked');
    const action = actionRadio ? actionRadio.value : "navigate";

    routeItems.push({
      name,
      location,
      note,
      checked: false,
      action,
    });

    saveRoutes();
    renderRouteList();
    requestPreview();

    if (routeSpotName) routeSpotName.value = "";
    if (routeSpotLocation) routeSpotLocation.value = "";
    if (routeSpotNote) routeSpotNote.value = "";
    if (routeSpotName) routeSpotName.focus();
  }

  if (btnAddRouteSpot) {
    btnAddRouteSpot.addEventListener("click", addRouteSpot);
  }
  if (routeSpotName) {
    routeSpotName.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        addRouteSpot();
      }
    });
  }

  // Clear completed / all
  if (btnClearCompletedRoutes) {
    btnClearCompletedRoutes.addEventListener("click", () => {
      routeItems = routeItems.filter((itm) => !itm.checked);
      saveRoutes();
      renderRouteList();
      requestPreview();
    });
  }
  if (btnClearAllRoutes) {
    btnClearAllRoutes.addEventListener("click", () => {
      if (confirm("ルート上のすべてのスポットを削除しますか？")) {
        routeItems = [];
        saveRoutes();
        renderRouteList();
        requestPreview();
      }
    });
  }

  // Load sample itinerary
  if (btnLoadRouteSample) {
    btnLoadRouteSample.addEventListener("click", () => {
      routeTitle.value = "🚗 伊豆スカイライン ドライブ";
      dbSet("ziriziri_route_title", routeTitle.value);
      routeMode = "driving";
      dbSet("ziriziri_route_mode", routeMode);
      routeModeChips.forEach((c) => c.classList.toggle("active", c.dataset.mode === "driving"));

      routeItems = [
        {
          name: "海老名SA 下り",
          location: "海老名SA 下り",
          note: "09:00 集合・給油・朝食",
          checked: false,
          action: "navigate",
        },
        {
          name: "アネスト岩田 スカイラウンジ",
          location: "アネスト岩田スカイラウンジ 大観山",
          note: "富士山と芦ノ湖の絶景休憩",
          checked: false,
          action: "navigate",
        },
        {
          name: "修善寺温泉 街歩き",
          location: "修善寺温泉",
          note: "温泉街散策・お昼ごはん",
          checked: false,
          action: "search",
        },
        {
          name: "熱海サンビーチ",
          location: "熱海サンビーチ",
          note: "海沿いドライブ＆おみやげ",
          checked: false,
          action: "navigate",
        },
      ];
      saveRoutes();
      renderRouteList();
      requestPreview();
    });
  }

  renderRouteList();

  // ─────────────────────────────────────────────────────────
  // TODO Management & QR Attachment
  // ─────────────────────────────────────────────────────────
  function saveTodos() {
    dbSet("ziriziri_todos", todoItems);
  }

  // QR Panel toggle & preset events
  if (btnToggleQrInput && qrAttachPanel) {
    btnToggleQrInput.addEventListener("click", () => {
      const isHidden = qrAttachPanel.style.display === "none";
      qrAttachPanel.style.display = isHidden ? "flex" : "none";
      qrToggleIcon.textContent = isHidden ? "✕" : "＋";
      if (isHidden && todoQrData) {
        todoQrData.focus();
      }
    });
  }

  qrPresetChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      qrPresetChips.forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      activeQrType = chip.dataset.type;
      const preset = qrPresets[activeQrType];
      if (preset && todoQrData) {
        todoQrData.placeholder = preset.placeholder;
        if (qrGuideTooltip) qrGuideTooltip.textContent = preset.tooltip;
        todoQrData.focus();
      }
    });
  });

  function renderTodoList() {
    todoList.innerHTML = "";
    todoItems.forEach((itm, idx) => {
      const row = document.createElement("div");
      row.className = "todo-item";

      const left = document.createElement("div");
      left.className = "todo-item-left";

      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.className = "todo-checkbox";
      cb.checked = itm.checked;
      cb.addEventListener("change", () => {
        itm.checked = cb.checked;
        saveTodos();
        renderTodoList();
        requestPreview();
      });

      const span = document.createElement("span");
      span.className = `todo-text ${itm.checked ? "checked" : ""}`;
      span.textContent = itm.text;

      left.appendChild(cb);
      left.appendChild(span);

      // QR Badge if attached
      if (itm.qr_data) {
        const badge = document.createElement("span");
        badge.className = "todo-qr-badge";
        const preset = qrPresets[itm.qr_type] || { badge: "QR" };
        badge.textContent = preset.badge;
        badge.title = `QR内容: ${itm.qr_data}\n（タップでQRを解除）`;
        badge.addEventListener("click", (e) => {
          e.stopPropagation();
          if (confirm(`この項目のQRコード情報を削除しますか？\n\n種別: ${preset.badge}\n内容: ${itm.qr_data}`)) {
            delete itm.qr_type;
            delete itm.qr_data;
            saveTodos();
            renderTodoList();
            requestPreview();
          }
        });
        left.appendChild(badge);
      }

      const btnDel = document.createElement("button");
      btnDel.className = "btn-delete";
      btnDel.innerHTML = "✕";
      btnDel.title = "削除";
      btnDel.addEventListener("click", () => {
        todoItems.splice(idx, 1);
        saveTodos();
        renderTodoList();
        requestPreview();
      });

      row.appendChild(left);
      row.appendChild(btnDel);
      todoList.appendChild(row);
    });
  }

  function addTodoItem(text) {
    const trimmed = text.trim();
    if (!trimmed) return;

    let qr_type = null;
    let qr_data = null;
    if (qrAttachPanel && qrAttachPanel.style.display !== "none" && todoQrData) {
      const qd = todoQrData.value.trim();
      if (qd) {
        qr_type = activeQrType;
        qr_data = qd;
      }
    }

    todoItems.push({
      text: trimmed,
      checked: false,
      qr_type: qr_type,
      qr_data: qr_data,
    });

    saveTodos();
    renderTodoList();
    requestPreview();

    // Clear QR data input after adding
    if (todoQrData) {
      todoQrData.value = "";
    }
  }

  btnAddTodo.addEventListener("click", () => {
    addTodoItem(todoInput.value);
    todoInput.value = "";
    todoInput.focus();
  });

  todoInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      addTodoItem(todoInput.value);
      todoInput.value = "";
    }
  });

  if (todoQrData) {
    todoQrData.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        addTodoItem(todoInput.value);
        todoInput.value = "";
      }
    });
  }

  todoTitle.addEventListener("input", () => {
    dbSet("ziriziri_todo_title", todoTitle.value);
    requestPreview();
  });

  if (btnClearCompletedTodos) {
    btnClearCompletedTodos.addEventListener("click", () => {
      const hasChecked = todoItems.some((itm) => itm.checked);
      if (!hasChecked) return;
      todoItems = todoItems.filter((itm) => !itm.checked);
      saveTodos();
      renderTodoList();
      requestPreview();
    });
  }

  if (btnClearAllTodos) {
    btnClearAllTodos.addEventListener("click", () => {
      if (todoItems.length === 0) return;
      if (confirm("TODOリストの全項目を削除しますか？")) {
        todoItems = [];
        saveTodos();
        renderTodoList();
        requestPreview();
      }
    });
  }

  // ─────────────────────────────────────────────────────────
  // Text & Image Controls Events
  // ─────────────────────────────────────────────────────────
  freeText.addEventListener("input", () => {
    dbSet("ziriziri_memo_text", freeText.value);
    requestPreview();
  });

  textSize.addEventListener("change", () => {
    dbSet("ziriziri_memo_size", textSize.value);
    requestPreview();
  });

  textAlign.addEventListener("change", () => {
    dbSet("ziriziri_memo_align", textAlign.value);
    requestPreview();
  });

  textBold.addEventListener("change", () => {
    dbSet("ziriziri_memo_bold", textBold.checked);
    requestPreview();
  });

  let lastClearedText = null;
  let restoreTimeout = null;

  if (btnClearText) {
    btnClearText.addEventListener("click", (e) => {
      e.preventDefault();
      if (btnClearText.dataset.mode === "undo" && lastClearedText !== null) {
        freeText.value = lastClearedText;
        dbSet("ziriziri_memo_text", lastClearedText);
        btnClearText.textContent = "🗑️ クリア";
        btnClearText.classList.add("danger");
        delete btnClearText.dataset.mode;
        lastClearedText = null;
        if (restoreTimeout) clearTimeout(restoreTimeout);
        requestPreview();
        freeText.focus();
        return;
      }

      if (!freeText.value) {
        freeText.focus();
        return;
      }

      lastClearedText = freeText.value;
      freeText.value = "";
      dbSet("ziriziri_memo_text", "");
      requestPreview();
      freeText.focus();

      btnClearText.textContent = "↩️ 元に戻す";
      btnClearText.classList.remove("danger");
      btnClearText.dataset.mode = "undo";

      if (restoreTimeout) clearTimeout(restoreTimeout);
      restoreTimeout = setTimeout(() => {
        btnClearText.textContent = "🗑️ クリア";
        btnClearText.classList.add("danger");
        delete btnClearText.dataset.mode;
        lastClearedText = null;
      }, 5000);
    });

    freeText.addEventListener("input", () => {
      if (btnClearText.dataset.mode === "undo") {
        btnClearText.textContent = "🗑️ クリア";
        btnClearText.classList.add("danger");
        delete btnClearText.dataset.mode;
        lastClearedText = null;
        if (restoreTimeout) clearTimeout(restoreTimeout);
      }
    });
  }

  imageInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      selectedImageFile = e.target.files[0];
      requestPreview();
    }
  });

  imageDither.addEventListener("change", requestPreview);
  imageContrast.addEventListener("input", (e) => {
    contrastVal.textContent = e.target.value;
    requestPreview();
  });

  // ─────────────────────────────────────────────────────────
  // Preview Rendering (Debounced)
  // ─────────────────────────────────────────────────────────
  function requestPreview() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(updatePreview, 150);
  }

  async function updatePreview() {
    try {
      const showDate = chkShowDate.checked;
      const datePos = selDatePos.value;
      const showCut = chkCutLine.checked;

      if (currentTab === "todo") {
        const payload = {
          title: todoTitle.value || "TODO LIST",
          items: todoItems,
          show_datetime: showDate,
          datetime_position: datePos,
          show_cut_line: showCut,
        };
        const res = await fetch("/api/preview/todo", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (data.preview) previewImg.src = data.preview;

      } else if (currentTab === "route") {
        const payload = {
          title: routeTitle ? (routeTitle.value || "🚗 ドライブルート") : "🚗 ドライブルート",
          items: routeItems,
          travel_mode: routeMode,
          show_datetime: showDate,
          datetime_position: datePos,
          show_cut_line: showCut,
        };
        const res = await fetch("/api/preview/route", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (data.preview) previewImg.src = data.preview;

      } else if (currentTab === "text") {
        const payload = {
          text: freeText.value || " ",
          font_size: parseInt(textSize.value, 10),
          align: textAlign.value,
          is_bold: textBold.checked,
          show_datetime: showDate,
          datetime_position: datePos,
          show_cut_line: showCut,
        };
        const res = await fetch("/api/preview/text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (data.preview) previewImg.src = data.preview;

      } else if (currentTab === "image") {
        if (!selectedImageFile) {
          previewImg.src = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='384' height='120'><rect width='384' height='120' fill='%23faf8f5'/><text x='192' y='65' font-family='sans-serif' font-size='14' fill='%23999' text-anchor='middle'>画像ファイルを選択してください</text></svg>";
          return;
        }
        const formData = new FormData();
        formData.append("file", selectedImageFile);
        formData.append("dither", imageDither.value);
        formData.append("contrast", imageContrast.value);
        formData.append("show_datetime", showDate);
        formData.append("datetime_position", datePos);
        formData.append("show_cut_line", showCut);

        const res = await fetch("/api/preview/image", {
          method: "POST",
          body: formData,
        });
        const data = await res.json();
        if (data.preview) previewImg.src = data.preview;

      } else if (currentTab === "test") {
        const res = await fetch("/api/preview/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            show_datetime: showDate,
            datetime_position: datePos,
            show_cut_line: showCut,
          }),
        });
        const data = await res.json();
        if (data.preview) previewImg.src = data.preview;
      }
    } catch (err) {
      console.error("Preview error:", err);
    }
  }

  // ─────────────────────────────────────────────────────────
  // Print Execution
  // ─────────────────────────────────────────────────────────
  btnPrint.addEventListener("click", async () => {
    btnPrint.disabled = true;
    printModal.classList.add("active");
    modalText.textContent = "プリンタへ送信中… ジジジ";

    const density = parseInt(printDensity.value, 10);
    const feed = parseInt(printFeed.value, 10);
    const showDate = chkShowDate.checked;
    const datePos = selDatePos.value;
    const showCut = chkCutLine.checked;

    try {
      let res;
      if (currentTab === "todo") {
        res = await fetch("/api/print/todo", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: todoTitle.value || "TODO LIST",
            items: todoItems,
            show_datetime: showDate,
            datetime_position: datePos,
            show_cut_line: showCut,
            density,
            feed,
          }),
        });
      } else if (currentTab === "route") {
        res = await fetch("/api/print/route", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: routeTitle ? (routeTitle.value || "🚗 ドライブルート") : "🚗 ドライブルート",
            items: routeItems,
            travel_mode: routeMode,
            show_datetime: showDate,
            datetime_position: datePos,
            show_cut_line: showCut,
            density,
            feed,
          }),
        });
      } else if (currentTab === "text") {
        res = await fetch("/api/print/text", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            text: freeText.value || " ",
            font_size: parseInt(textSize.value, 10),
            align: textAlign.value,
            is_bold: textBold.checked,
            show_datetime: showDate,
            datetime_position: datePos,
            show_cut_line: showCut,
            density,
            feed,
          }),
        });
      } else if (currentTab === "image") {
        if (!selectedImageFile) {
          alert("画像を選択してください");
          return;
        }
        const formData = new FormData();
        formData.append("file", selectedImageFile);
        formData.append("dither", imageDither.value);
        formData.append("contrast", imageContrast.value);
        formData.append("show_datetime", showDate);
        formData.append("datetime_position", datePos);
        formData.append("show_cut_line", showCut);
        formData.append("density", density);
        formData.append("feed", feed);

        res = await fetch("/api/print/image", {
          method: "POST",
          body: formData,
        });
      } else if (currentTab === "test") {
        res = await fetch("/api/print/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            density,
            feed,
            show_datetime: showDate,
            datetime_position: datePos,
            show_cut_line: showCut,
          }),
        });
      }


      if (res && res.ok) {
        const resData = await res.json();
        if (resData.battery !== undefined && resData.battery !== null) {
          updateBatteryUI(resData.battery);
        }
        modalText.textContent = "✨ 印刷が完了しました！";
        setTimeout(() => {
          printModal.classList.remove("active");
          btnPrint.disabled = false;
        }, 1200);
      } else {
        let errDetail = "送信に失敗しました";
        if (res) {
          try {
            const contentType = res.headers.get("content-type") || "";
            if (contentType.includes("application/json")) {
              const data = await res.json();
              errDetail = data.detail || JSON.stringify(data);
            } else {
              const text = await res.text();
              errDetail = text || `HTTP ${res.status}`;
            }
          } catch (_) {
            errDetail = `HTTP ${res.status}`;
          }
        }
        alert("印刷エラー: " + errDetail);
        printModal.classList.remove("active");
        btnPrint.disabled = false;
      }
    } catch (err) {
      alert("通信エラーが発生しました: " + err.message);
      printModal.classList.remove("active");
      btnPrint.disabled = false;
    }
  });

  // ─────────────────────────────────────────────────────────
  // Printer Status & Battery Display
  // ─────────────────────────────────────────────────────────
  function updateBatteryUI(bat) {
    if (bat === null || bat === undefined) return;
    let icon = "🔋";
    let color = "#10b981"; // green
    if (bat <= 20) {
      icon = "🪫";
      color = "#ef4444"; // red
    } else if (bat <= 50) {
      color = "#f59e0b"; // orange
    }
    statusDot.style.background = color;
    statusText.innerHTML = `SWS-PT1 <b style="color:${color}; margin-left:4px;">${icon} ${bat}%</b>`;
  }

  async function checkStatus(isManual = false) {
    if (isManual) {
      statusText.textContent = "残量を確認中…";
    }
    try {
      const res = await fetch("/api/status");
      const data = await res.json();
      if (data.battery !== null && data.battery !== undefined) {
        updateBatteryUI(data.battery);
      } else if (data.connected) {
        statusDot.style.background = "#10b981";
        statusText.textContent = `${data.name || "SWS-PT1"} 接続中`;
      } else {
        statusDot.style.background = "#9499ad";
        statusText.textContent = "プリンタ待機中 (タップで更新)";
      }
    } catch (e) {
      statusDot.style.background = "#ef4444";
      statusText.textContent = "オフライン";
    }
  }

  // Allow manual battery check by tapping status badge
  statusBadge.style.cursor = "pointer";
  statusBadge.title = "タップしてバッテリー残量を更新";
  statusBadge.addEventListener("click", () => {
    checkStatus(true);
  });

  // Init
  renderTodoList();
  requestPreview();
  checkStatus();
});

