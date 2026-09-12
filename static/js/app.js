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
  const presetChips = document.querySelectorAll(".preset-chip");

  // Text elements
  const freeText = document.getElementById("freeText");
  const textSize = document.getElementById("textSize");
  const textAlign = document.getElementById("textAlign");
  const textBold = document.getElementById("textBold");

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

  chkShowDate.addEventListener("change", requestPreview);
  selDatePos.addEventListener("change", requestPreview);
  chkCutLine.addEventListener("change", requestPreview);

  // ─────────────────────────────────────────────────────────
  // Tab Navigation
  // ─────────────────────────────────────────────────────────
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tabPanes.forEach((p) => p.classList.remove("active"));
      tab.classList.add("active");
      currentTab = tab.dataset.tab;
      document.getElementById(`pane-${currentTab}`).classList.add("active");
      requestPreview();
    });
  });

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

  presetChips.forEach((chip) => {
    chip.addEventListener("click", () => {
      const itemText = chip.textContent.replace(/^\+\s*/, "");
      addTodoItem(itemText);
    });
  });

  todoTitle.addEventListener("input", requestPreview);

  // ─────────────────────────────────────────────────────────
  // Text & Image Controls Events
  // ─────────────────────────────────────────────────────────
  freeText.addEventListener("input", requestPreview);
  textSize.addEventListener("change", requestPreview);
  textAlign.addEventListener("change", requestPreview);
  textBold.addEventListener("change", requestPreview);

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
        const err = await res.json();
        alert("印刷エラー: " + (err.detail || "送信に失敗しました"));
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

