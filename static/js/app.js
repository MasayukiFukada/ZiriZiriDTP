// ZiriZiriDTP Client Application Logic

document.addEventListener("DOMContentLoaded", () => {
  // State
  let currentTab = "todo";
  let todoItems = JSON.parse(localStorage.getItem("ziriziri_todos") || "null") || [
    { text: "牛乳 1本", checked: false },
    { text: "食パン (6枚切り)", checked: false },
    { text: "たまご 1パック", checked: true },
    { text: "感熱ロール紙 予備", checked: false },
  ];
  let debounceTimer = null;
  let selectedImageFile = null;

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

  // TODO elements
  const todoTitle = document.getElementById("todoTitle");
  const todoInput = document.getElementById("todoInput");
  const btnAddTodo = document.getElementById("btnAddTodo");
  const todoList = document.getElementById("todoList");
  const btnClearCompletedTodos = document.getElementById("btnClearCompletedTodos");
  const btnClearAllTodos = document.getElementById("btnClearAllTodos");

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

  // ─────────────────────────────────────────────────────────
  // Restore State from LocalStorage
  // ─────────────────────────────────────────────────────────
  // TODO Title
  const savedTodoTitle = localStorage.getItem("ziriziri_todo_title");
  if (savedTodoTitle !== null) {
    todoTitle.value = savedTodoTitle;
  }

  // Free Text & Text Options
  const savedMemoText = localStorage.getItem("ziriziri_memo_text");
  if (savedMemoText !== null) {
    freeText.value = savedMemoText;
  }
  const savedMemoSize = localStorage.getItem("ziriziri_memo_size");
  if (savedMemoSize !== null) {
    textSize.value = savedMemoSize;
  }
  const savedMemoAlign = localStorage.getItem("ziriziri_memo_align");
  if (savedMemoAlign !== null) {
    textAlign.value = savedMemoAlign;
  }
  const savedMemoBold = localStorage.getItem("ziriziri_memo_bold");
  if (savedMemoBold !== null) {
    textBold.checked = savedMemoBold === "true";
  }

  // Print options
  const savedShowDate = localStorage.getItem("ziriziri_opt_show_date");
  if (savedShowDate !== null) chkShowDate.checked = savedShowDate === "true";
  const savedDatePos = localStorage.getItem("ziriziri_opt_date_pos");
  if (savedDatePos !== null) selDatePos.value = savedDatePos;
  const savedCutLine = localStorage.getItem("ziriziri_opt_cut_line");
  if (savedCutLine !== null) chkCutLine.checked = savedCutLine === "true";
  const savedDensity = localStorage.getItem("ziriziri_opt_density");
  if (savedDensity !== null) printDensity.value = savedDensity;
  const savedFeed = localStorage.getItem("ziriziri_opt_feed");
  if (savedFeed !== null) printFeed.value = savedFeed;

  // Active Tab
  const savedTab = localStorage.getItem("ziriziri_active_tab");
  if (savedTab && document.getElementById(`pane-${savedTab}`)) {
    currentTab = savedTab;
  }

  chkShowDate.addEventListener("change", () => {
    localStorage.setItem("ziriziri_opt_show_date", chkShowDate.checked);
    requestPreview();
  });
  selDatePos.addEventListener("change", () => {
    localStorage.setItem("ziriziri_opt_date_pos", selDatePos.value);
    requestPreview();
  });
  chkCutLine.addEventListener("change", () => {
    localStorage.setItem("ziriziri_opt_cut_line", chkCutLine.checked);
    requestPreview();
  });
  printDensity.addEventListener("change", () => {
    localStorage.setItem("ziriziri_opt_density", printDensity.value);
  });
  printFeed.addEventListener("change", () => {
    localStorage.setItem("ziriziri_opt_feed", printFeed.value);
  });

  // ─────────────────────────────────────────────────────────
  // Tab Navigation
  // ─────────────────────────────────────────────────────────
  function switchTab(tabName) {
    currentTab = tabName;
    localStorage.setItem("ziriziri_active_tab", tabName);
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
  // TODO Management
  // ─────────────────────────────────────────────────────────
  function saveTodos() {
    localStorage.setItem("ziriziri_todos", JSON.stringify(todoItems));
  }

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
    todoItems.push({ text: trimmed, checked: false });
    saveTodos();
    renderTodoList();
    requestPreview();
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

  todoTitle.addEventListener("input", () => {
    localStorage.setItem("ziriziri_todo_title", todoTitle.value);
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
    localStorage.setItem("ziriziri_memo_text", freeText.value);
    requestPreview();
  });

  textSize.addEventListener("change", () => {
    localStorage.setItem("ziriziri_memo_size", textSize.value);
    requestPreview();
  });

  textAlign.addEventListener("change", () => {
    localStorage.setItem("ziriziri_memo_align", textAlign.value);
    requestPreview();
  });

  textBold.addEventListener("change", () => {
    localStorage.setItem("ziriziri_memo_bold", textBold.checked);
    requestPreview();
  });

  let lastClearedText = null;
  let restoreTimeout = null;

  if (btnClearText) {
    btnClearText.addEventListener("click", (e) => {
      e.preventDefault();
      if (btnClearText.dataset.mode === "undo" && lastClearedText !== null) {
        freeText.value = lastClearedText;
        localStorage.setItem("ziriziri_memo_text", lastClearedText);
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
      localStorage.setItem("ziriziri_memo_text", "");
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

