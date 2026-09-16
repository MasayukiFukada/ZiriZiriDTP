// ZiriZiriDTP IndexedDB Storage Module
// Provides robust, persistent client-side storage replacing localStorage.

const DB_NAME = "ZiriZiriDTP_DB";
const DB_VERSION = 1;
const STORE_NAME = "keyval";

let _dbInstance = null;

/**
 * Open or return existing IndexedDB database connection.
 */
function openDB() {
  if (_dbInstance) {
    return Promise.resolve(_dbInstance);
  }
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "key" });
      }
    };

    request.onsuccess = (event) => {
      _dbInstance = event.target.result;
      resolve(_dbInstance);
    };

    request.onerror = (event) => {
      console.error("IndexedDB open error:", event.target.error);
      reject(event.target.error);
    };
  });
}

/**
 * Retrieve value by key from IndexedDB.
 */
async function dbGet(key, defaultValue = null) {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_NAME], "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.get(key);

      req.onsuccess = () => {
        if (req.result !== undefined && req.result !== null) {
          resolve(req.result.value);
        } else {
          resolve(defaultValue);
        }
      };

      req.onerror = () => {
        reject(req.error);
      };
    });
  } catch (err) {
    console.warn(`dbGet error for ${key}:`, err);
    return defaultValue;
  }
}

/**
 * Store value for key in IndexedDB.
 */
async function dbSet(key, value) {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_NAME], "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.put({ key, value });

      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.error(`dbSet error for ${key}:`, err);
  }
}

/**
 * Delete key from IndexedDB.
 */
async function dbDelete(key) {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_NAME], "readwrite");
      const store = tx.objectStore(STORE_NAME);
      const req = store.delete(key);

      req.onsuccess = () => resolve();
      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.error(`dbDelete error for ${key}:`, err);
  }
}

/**
 * Get all key-value pairs stored in IndexedDB.
 */
async function dbGetAll() {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction([STORE_NAME], "readonly");
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();

      req.onsuccess = () => {
        const resultObj = {};
        if (req.result && Array.isArray(req.result)) {
          req.result.forEach((item) => {
            if (item && item.key) {
              resultObj[item.key] = item.value;
            }
          });
        }
        resolve(resultObj);
      };

      req.onerror = () => reject(req.error);
    });
  } catch (err) {
    console.error("dbGetAll error:", err);
    return {};
  }
}

/**
 * Migrate legacy data from localStorage to IndexedDB if not done yet.
 */
async function migrateFromLocalStorage() {
  try {
    const migrated = await dbGet("_migrated_from_ls", false);
    if (migrated) return;

    const keysToMigrate = [
      "ziriziri_todos",
      "ziriziri_todo_title",
      "ziriziri_route_items",
      "ziriziri_route_title",
      "ziriziri_route_mode",
      "ziriziri_memo_text",
      "ziriziri_memo_size",
      "ziriziri_memo_align",
      "ziriziri_memo_bold",
      "ziriziri_opt_show_date",
      "ziriziri_opt_date_pos",
      "ziriziri_opt_cut_line",
      "ziriziri_opt_density",
      "ziriziri_opt_feed",
      "ziriziri_active_tab",
    ];

    for (const key of keysToMigrate) {
      const raw = localStorage.getItem(key);
      if (raw !== null) {
        let val = raw;
        if (key === "ziriziri_todos" || key === "ziriziri_route_items") {
          try {
            val = JSON.parse(raw);
          } catch (_) {
            val = raw;
          }
        } else if (key === "ziriziri_memo_bold" || key === "ziriziri_opt_show_date" || key === "ziriziri_opt_cut_line") {
          val = raw === "true";
        }
        await dbSet(key, val);
      }
    }

    await dbSet("_migrated_from_ls", true);
    console.log("Migration from localStorage to IndexedDB completed successfully.");
  } catch (err) {
    console.warn("Migration from localStorage failed:", err);
  }
}

/**
 * Export all IndexedDB data as a downloaded JSON file.
 */
async function exportBackupFile() {
  const data = await dbGetAll();
  // Filter out internal migration flags
  delete data["_migrated_from_ls"];

  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const now = new Date();
  const dateStr = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, "0")}${String(now.getDate()).padStart(2, "0")}`;
  a.href = url;
  a.download = `ziriziri_backup_${dateStr}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Import data from a JSON object and write into IndexedDB.
 */
async function importBackupData(dataObj) {
  if (!dataObj || typeof dataObj !== "object") {
    throw new Error("Invalid backup data format");
  }
  for (const [key, value] of Object.entries(dataObj)) {
    await dbSet(key, value);
  }
  await dbSet("_migrated_from_ls", true);
}
