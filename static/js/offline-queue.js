// Fila offline leve com IndexedDB + Axios interceptors
(function() {
  const DB_NAME = 'mtdl-offline';
  const STORE_NAME = 'requests';
  let dbPromise = null;

  function openDb() {
    if (dbPromise) return dbPromise;
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains(STORE_NAME)) {
          db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return dbPromise;
  }

  async function saveRequest(entry) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.objectStore(STORE_NAME).add(entry);
    });
  }

  async function getAllRequests() {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readonly');
      const store = tx.objectStore(STORE_NAME);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  }

  async function deleteRequest(id) {
    const db = await openDb();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_NAME, 'readwrite');
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
      tx.objectStore(STORE_NAME).delete(id);
    });
  }

  async function flushQueue() {
    if (!navigator.onLine) {
      if (typeof showAlert === 'function') {
        showAlert('Sem conexão. A fila será sincronizada quando voltar.', 'warning', 3000);
      }
      return { synced: 0 };
    }

    const queued = await getAllRequests();
    if (queued.length === 0) return { synced: 0 };

    // Tentar sincronização em lote primeiro
    try {
      const payload = { requests: queued.map(q => ({ method: q.method, url: q.url, data: q.data, headers: q.headers })) };
      const resp = await axios.post('/api/sync/bulk', payload);
      const results = (resp && resp.data && resp.data.results) ? resp.data.results : [];
      let synced = 0;
      for (let i = 0; i < results.length; i++) {
        const r = results[i];
        const item = queued[i];
        if (r && r.ok) {
          await deleteRequest(item.id);
          synced += 1;
        }
      }
      if (synced > 0 && typeof showAlert === 'function') {
        showAlert(`${synced} requisições sincronizadas com sucesso.`, 'success', 4000);
      }
      return { synced };
    } catch (bulkErr) {
      console.warn('Falha em /api/sync/bulk, executando sincronização individual...', bulkErr);
    }

    // Fallback: sincronização uma a uma
    let synced = 0;
    for (const item of queued) {
      try {
        await axios({ method: item.method, url: item.url, data: item.data, headers: item.headers || {} });
        await deleteRequest(item.id);
        synced += 1;
      } catch (err) {
        if (err && err.response) {
          console.warn('Falha ao sincronizar requisição (servidor):', item.url, err.response.status);
          if (typeof showAlert === 'function') {
            showAlert('Erro do servidor ao sincronizar. Tentará novamente mais tarde.', 'danger', 5000);
          }
        } else {
          console.warn('Falha de rede ao sincronizar, manter na fila:', item.url);
        }
      }
    }

    if (synced > 0 && typeof showAlert === 'function') {
      showAlert(`${synced} requisições sincronizadas com sucesso.`, 'success', 4000);
    }
    return { synced };
  }

  // Expor função pública para debug/manual
  window.flushOfflineQueue = flushQueue;

  // Adicionar API pública para enfileirar requisições (para uso com fetch)
  async function enqueueOfflineRequest(method, url, data, headers) {
    const key = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const entry = {
      method: (method || 'post').toUpperCase(),
      url,
      data,
      headers: Object.assign({}, headers || {}, { 'X-Idempotency-Key': key }),
      ts: Date.now()
    };
    await saveRequest(entry);
    if (typeof showAlert === 'function') {
      showAlert('Sem conexão: requisição armazenada e será sincronizada automaticamente.', 'warning', 4000);
    }
    return { queued: true };
  }
  window.enqueueOfflineRequest = enqueueOfflineRequest;

  // Interceptar respostas com erro de rede e enfileirar requisições mutáveis
  if (window.axios) {
    axios.interceptors.response.use(
      (response) => response,
      async (error) => {
        const cfg = error && error.config ? error.config : null;
        const hasNetworkError = !error.response;
        const isMutable = cfg && ['post', 'put', 'patch', 'delete'].includes((cfg.method || '').toLowerCase());
        const isApi = cfg && typeof cfg.url === 'string' && cfg.url.startsWith('/api/');

        if (hasNetworkError && isMutable && isApi) {
          const key = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
          const entry = {
            method: (cfg.method || 'post').toUpperCase(),
            url: cfg.url,
            data: cfg.data,
            headers: Object.assign({}, cfg.headers || {}, { 'X-Idempotency-Key': key }),
            ts: Date.now()
          };
          try {
            await saveRequest(entry);
            if (typeof showAlert === 'function') {
              showAlert('Sem conexão: requisição armazenada e será sincronizada automaticamente.', 'warning', 4000);
            }
            // Resolver com resposta "aceita" para não quebrar a UI
            return Promise.resolve({ data: { queued: true }, status: 202, headers: {}, config: cfg });
          } catch (e) {
            console.error('Falha ao armazenar requisição offline:', e);
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Ao voltar online, disparar sincronização
  window.addEventListener('online', () => {
    flushQueue();
  });
})();