// JavaScript principal para MTDL-PCM

// Função auxiliar para requisições HTTP usando fetch
async function apiRequest(url, options = {}) {
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        },
        ...options
    };
    const method = (defaultOptions.method || 'GET').toUpperCase();
    const isMutable = ['POST','PUT','PATCH','DELETE'].includes(method);
    const isApi = typeof url === 'string' && (url.startsWith('/api/') || url.includes('/api/'));

    // Se offline, enfileirar requisições mutáveis e retornar resposta 202
    if (!navigator.onLine && isMutable && isApi && typeof window.enqueueOfflineRequest === 'function') {
        const headers = defaultOptions.headers || {};
        let data = null;
        if (defaultOptions.body) {
            const ct = (headers['Content-Type'] || headers['content-type'] || '').toLowerCase();
            if (ct.includes('application/json') && typeof defaultOptions.body === 'string') {
                try { data = JSON.parse(defaultOptions.body); } catch { data = defaultOptions.body; }
            } else {
                data = defaultOptions.body;
            }
        }
        await window.enqueueOfflineRequest(method, url, data, headers);
        return new Response(JSON.stringify({ queued: true }), { status: 202, headers: { 'Content-Type': 'application/json' } });
    }
    
    try {
        const response = await fetch(url, defaultOptions);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const message = errorData.detail || errorData.message || 'Erro no servidor';
            
            switch (response.status) {
                case 400:
                    showAlert('Dados inválidos: ' + message, 'warning');
                    break;
                case 401:
                    showAlert('Acesso não autorizado', 'danger');
                    break;
                case 403:
                    showAlert('Acesso negado', 'danger');
                    break;
                case 404:
                    showAlert('Recurso não encontrado', 'warning');
                    break;
                case 422:
                    showAlert('Erro de validação: ' + message, 'warning');
                    break;
                case 500:
                    showAlert('Erro interno do servidor', 'danger');
                    break;
                default:
                    showAlert('Erro: ' + message, 'danger');
            }
            
            throw new Error(message);
        }
        
        return response;
        
    } catch (error) {
        console.error('Erro na requisição:', error);
        
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            // Erro de rede
            showAlert('Erro de conexão. Verifique sua internet.', 'danger');
        } else if (!error.message.includes('Dados inválidos') && 
                   !error.message.includes('Acesso') && 
                   !error.message.includes('Recurso não encontrado')) {
            // Outro erro não tratado
            showAlert('Erro inesperado: ' + error.message, 'danger');
        }
        
        throw error;
    }
}

// Sistema de notificações
function showAlert(message, type = 'info', duration = 5000) {
    // Remove alertas existentes
    const existingAlerts = document.querySelectorAll('.alert-notification');
    existingAlerts.forEach(alert => alert.remove());
    
    // Cria novo alerta
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show alert-notification`;
    alertDiv.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        max-width: 500px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `;
    
    alertDiv.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi ${getAlertIcon(type)} me-2"></i>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove após duração especificada
    if (duration > 0) {
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, duration);
    }
}

function getAlertIcon(type) {
    const icons = {
        'success': 'bi-check-circle-fill',
        'warning': 'bi-exclamation-triangle-fill',
        'danger': 'bi-x-circle-fill',
        'info': 'bi-info-circle-fill'
    };
    return icons[type] || 'bi-info-circle-fill';
}

// Confirmação de ações
function confirmAction(message, callback, title = 'Confirmar Ação') {
    if (confirm(`${title}\n\n${message}`)) {
        callback();
    }
}

// Formatação de números
function formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    }).format(value || 0);
}

function formatNumber(value, decimals = 2) {
    return new Intl.NumberFormat('pt-BR', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(value || 0);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('pt-BR');
}

function formatDateTime(dateString) {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString('pt-BR');
}

// Validação de formulários
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form) return false;
    
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}

// Limpar validação de formulário
function clearFormValidation(formId) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    const fields = form.querySelectorAll('.is-invalid');
    fields.forEach(field => field.classList.remove('is-invalid'));
}

// Controle do sidebar
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (sidebar && mainContent) {
        sidebar.classList.toggle('collapsed');
        
        // Salvar estado no localStorage
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    }
}

// Restaurar estado do sidebar
function restoreSidebarState() {
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    const sidebar = document.querySelector('.sidebar');
    
    if (sidebar && isCollapsed) {
        sidebar.classList.add('collapsed');
    }
}

// Marcar item ativo no menu
function setActiveMenuItem() {
    const currentPath = window.location.pathname;
    const menuItems = document.querySelectorAll('.sidebar-nav a');
    
    menuItems.forEach(item => {
        item.classList.remove('active');
        
        const href = item.getAttribute('href');
        if (href && (currentPath === href || currentPath.startsWith(href + '/'))) {
            item.classList.add('active');
        }
    });
}

// Loading state para botões
function setButtonLoading(buttonId, loading = true) {
    const button = document.getElementById(buttonId);
    if (!button) return;
    
    if (loading) {
        button.disabled = true;
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Carregando...';
    } else {
        button.disabled = false;
        button.innerHTML = button.dataset.originalText || button.innerHTML;
    }
}

// Loading state para elementos
function setElementLoading(elementId, loading = true) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (loading) {
        element.classList.add('loading');
    } else {
        element.classList.remove('loading');
    }
}

// Debounce para otimizar buscas
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Exportar dados para Excel
async function exportToExcel(data, filename, sheetName = 'Dados') {
    try {
        // Verificar se a biblioteca XLSX está disponível
        if (typeof XLSX === 'undefined') {
            showAlert('Biblioteca de exportação não carregada', 'warning');
            return;
        }
        
        const ws = XLSX.utils.json_to_sheet(data);
        const wb = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(wb, ws, sheetName);
        
        XLSX.writeFile(wb, `${filename}_${new Date().toISOString().split('T')[0]}.xlsx`);
        showAlert('Arquivo exportado com sucesso!', 'success');
    } catch (error) {
        console.error('Erro ao exportar:', error);
        showAlert('Erro ao exportar arquivo', 'danger');
    }
}

// Imprimir relatório
function printReport(elementId) {
    const element = document.getElementById(elementId);
    if (!element) {
        showAlert('Elemento não encontrado para impressão', 'warning');
        return;
    }
    
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>Relatório MTDL-PCM</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <style>
                body { font-size: 12px; }
                .no-print { display: none !important; }
                @media print {
                    .btn, .pagination { display: none !important; }
                }
            </style>
        </head>
        <body>
            <div class="container-fluid">
                <div class="text-center mb-4">
                    <h2>MTDL-PCM</h2>
                    <p>Relatório gerado em ${formatDateTime(new Date().toISOString())}</p>
                </div>
                ${element.innerHTML}
            </div>
            <script>
                window.onload = function() {
                    window.print();
                    window.close();
                };
            </script>
        </body>
        </html>
    `);
    printWindow.document.close();
}

// Copiar texto para clipboard
async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        showAlert('Texto copiado para a área de transferência', 'success', 2000);
    } catch (error) {
        console.error('Erro ao copiar:', error);
        showAlert('Erro ao copiar texto', 'warning');
    }
}

// Validação de CPF
function validateCPF(cpf) {
    cpf = cpf.replace(/[^\d]/g, '');
    
    if (cpf.length !== 11 || /^(\d)\1{10}$/.test(cpf)) {
        return false;
    }
    
    let sum = 0;
    for (let i = 0; i < 9; i++) {
        sum += parseInt(cpf.charAt(i)) * (10 - i);
    }
    
    let remainder = (sum * 10) % 11;
    if (remainder === 10 || remainder === 11) remainder = 0;
    if (remainder !== parseInt(cpf.charAt(9))) return false;
    
    sum = 0;
    for (let i = 0; i < 10; i++) {
        sum += parseInt(cpf.charAt(i)) * (11 - i);
    }
    
    remainder = (sum * 10) % 11;
    if (remainder === 10 || remainder === 11) remainder = 0;
    
    return remainder === parseInt(cpf.charAt(10));
}

// Validação de CNPJ
function validateCNPJ(cnpj) {
    cnpj = cnpj.replace(/[^\d]/g, '');
    
    if (cnpj.length !== 14) return false;
    
    if (/^(\d)\1{13}$/.test(cnpj)) return false;
    
    let length = cnpj.length - 2;
    let numbers = cnpj.substring(0, length);
    let digits = cnpj.substring(length);
    let sum = 0;
    let pos = length - 7;
    
    for (let i = length; i >= 1; i--) {
        sum += numbers.charAt(length - i) * pos--;
        if (pos < 2) pos = 9;
    }
    
    let result = sum % 11 < 2 ? 0 : 11 - sum % 11;
    if (result !== parseInt(digits.charAt(0))) return false;
    
    length = length + 1;
    numbers = cnpj.substring(0, length);
    sum = 0;
    pos = length - 7;
    
    for (let i = length; i >= 1; i--) {
        sum += numbers.charAt(length - i) * pos--;
        if (pos < 2) pos = 9;
    }
    
    result = sum % 11 < 2 ? 0 : 11 - sum % 11;
    
    return result === parseInt(digits.charAt(1));
}

// Máscaras para inputs
function applyMasks() {
    // Máscara para CPF
    document.querySelectorAll('[data-mask="cpf"]').forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            value = value.replace(/(\d{3})(\d)/, '$1.$2');
            value = value.replace(/(\d{3})(\d)/, '$1.$2');
            value = value.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
            e.target.value = value;
        });
    });
    
    // Máscara para CNPJ
    document.querySelectorAll('[data-mask="cnpj"]').forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            value = value.replace(/^(\d{2})(\d)/, '$1.$2');
            value = value.replace(/^(\d{2})\.(\d{3})(\d)/, '$1.$2.$3');
            value = value.replace(/\.(\d{3})(\d)/, '.$1/$2');
            value = value.replace(/(\d{4})(\d)/, '$1-$2');
            e.target.value = value;
        });
    });
    
    // Máscara para telefone
    document.querySelectorAll('[data-mask="phone"]').forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            if (value.length <= 10) {
                value = value.replace(/(\d{2})(\d)/, '($1) $2');
                value = value.replace(/(\d{4})(\d)/, '$1-$2');
            } else {
                value = value.replace(/(\d{2})(\d)/, '($1) $2');
                value = value.replace(/(\d{5})(\d)/, '$1-$2');
            }
            e.target.value = value;
        });
    });
    
    // Máscara para CEP
    document.querySelectorAll('[data-mask="cep"]').forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            value = value.replace(/(\d{5})(\d)/, '$1-$2');
            e.target.value = value;
        });
    });
    
    // Máscara para moeda
    document.querySelectorAll('[data-mask="currency"]').forEach(input => {
        input.addEventListener('input', function(e) {
            let value = e.target.value.replace(/\D/g, '');
            value = (value / 100).toFixed(2);
            value = value.replace('.', ',');
            value = value.replace(/(\d)(?=(\d{3})+(?!\d))/g, '$1.');
            e.target.value = 'R$ ' + value;
        });
    });
}

// Inicialização quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Restaurar estado do sidebar
    restoreSidebarState();
    
    // Marcar item ativo no menu
    setActiveMenuItem();
    
    // Aplicar máscaras
    applyMasks();
    
    // Event listener para toggle do sidebar
    const sidebarToggle = document.querySelector('.sidebar-toggle');
    if (sidebarToggle) {
        sidebarToggle.addEventListener('click', toggleSidebar);
    }
    
    // Inicializar tooltips do Bootstrap
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Inicializar popovers do Bootstrap
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-hide alerts após 5 segundos
    setTimeout(() => {
        const alerts = document.querySelectorAll('.alert:not(.alert-notification)');
        alerts.forEach(alert => {
            if (alert.classList.contains('alert-dismissible')) {
                const closeBtn = alert.querySelector('.btn-close');
                if (closeBtn) closeBtn.click();
            }
        });
    }, 5000);
    
    // Inicializar menu colapsável
    initCollapsibleMenu();
    
    // Remover expansão automática das subáreas ao abrir "Apropriação de Obra"
    const constructionMenu = document.getElementById('constructionMenu');
    if (constructionMenu) {
        // Não forçar subáreas a abrirem/fecharem automaticamente; o usuário controla cada grupo.
        constructionMenu.addEventListener('shown.bs.collapse', function(e) {
            // Garantir que apenas trate o próprio container (sem efeito colateral nos filhos)
            if (e.target !== constructionMenu) return;
        });
        constructionMenu.addEventListener('hidden.bs.collapse', function(e) {
            if (e.target !== constructionMenu) return;
        });
    }


});

// Função para inicializar o menu colapsável
function initCollapsibleMenu() {
    // Selecionar todos os cabeçalhos de menu colapsável
    const menuHeaders = document.querySelectorAll('.collapsible-menu-header');
    
    menuHeaders.forEach(header => {
        // Restaurar estado do localStorage primeiro
        const target = header.getAttribute('data-bs-target') || header.getAttribute('href');
        if (!target) return; // Pular se não há target
        const menuId = target.replace('#', '');
        const savedState = localStorage.getItem(`menu_${menuId}_expanded`);
        const collapseElement = document.querySelector(target);
        const chevronIcon = header.querySelector('.bi-chevron-down');
        
        // Se há estado salvo, aplicar ele
        if (savedState !== null) {
            const isExpanded = savedState === 'true';
            if (collapseElement) {
                const bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapseElement, { toggle: false });
                if (isExpanded) {
                    bsCollapse.show();
                    header.setAttribute('aria-expanded', 'true');
                    if (chevronIcon) {
                        chevronIcon.style.transform = 'rotate(0deg)';
                    }
                } else {
                    bsCollapse.hide();
                    header.setAttribute('aria-expanded', 'false');
                    if (chevronIcon) {
                        chevronIcon.style.transform = 'rotate(-90deg)';
                    }
                }
            }
        }
        
        // Sincronizar estado visual e localStorage quando Bootstrap controla o colapso
        if (collapseElement) {
            collapseElement.addEventListener('show.bs.collapse', function() {
                header.setAttribute('aria-expanded', 'true');
                if (chevronIcon) {
                    chevronIcon.style.transform = 'rotate(0deg)';
                }
                localStorage.setItem(`menu_${menuId}_expanded`, 'true');
            });
            collapseElement.addEventListener('hide.bs.collapse', function() {
                header.setAttribute('aria-expanded', 'false');
                if (chevronIcon) {
                    chevronIcon.style.transform = 'rotate(-90deg)';
                }
                localStorage.setItem(`menu_${menuId}_expanded`, 'false');
            });
        }
        
        // Adicionar evento de clique
        header.addEventListener('click', function(e) {
            const targetSel = this.getAttribute('data-bs-target') || this.getAttribute('href');
            if (!targetSel || targetSel === '#') return;
            const collapseElement = document.querySelector(targetSel);
            if (!collapseElement) return;

            // Prevenir navegação apenas para anchors
            if (this.tagName === 'A') {
                e.preventDefault();
            }

            // Toggle via Bootstrap
            const bsCollapse = bootstrap.Collapse.getOrCreateInstance(collapseElement, { toggle: false });
            bsCollapse.toggle();

            // Remover qualquer override de display para deixar o Bootstrap controlar
            collapseElement.style.removeProperty('display');
        });
    });
}

// Exportar funções globais
window.MTDL = {
    showAlert,
    confirmAction,
    formatCurrency,
    formatNumber,
    formatDate,
    formatDateTime,
    validateForm,
    clearFormValidation,
    toggleSidebar,
    setButtonLoading,
    setElementLoading,
    debounce,
    exportToExcel,
    printReport,
    copyToClipboard,
    validateCPF,
    validateCNPJ
};


// Verificação de atualização (semver) ao iniciar
(function(){
  async function getLocalVersion(){
    try {
      const res = await fetch('/api/admin/version', { cache: 'no-store' });
      if (!res.ok) throw new Error('Falha ao obter versão local');
      const data = await res.json();
      return String(data.version || '0.0.0');
    } catch (e) {
      console.warn('[update-check] Erro ao obter versão local:', e);
      return '0.0.0';
    }
  }

  async function fetchUpdateFeed(){
    const remoteCandidates = [
      'https://mtdl.com.br/version.json',
      'https://MTDL-Transporte.github.io/MTDL-PCM/version.json'
    ];
    const localUrl = '/static/version.json';
    const noCache = `?t=${Date.now()}`;

    async function tryFetch(url){
      const res = await fetch(url + noCache, { cache: 'no-store' });
      if (!res.ok) throw new Error(`Feed HTTP ${res.status}`);
      const data = await res.json();
      return {
        latest: String(data.latest_version || '0.0.0'),
        url: String(data.download_url || ''),
        changelog: String(data.changelog || '')
      };
    }

    // Tenta primeiro no domínio oficial, depois fallback para GitHub Pages
    for (const u of remoteCandidates){
      try {
        return await tryFetch(u);
      } catch (e) {
        console.warn('[update-check] Feed remoto indisponível:', u, e);
      }
    }

    // Fallback final: feed local do pacote
    try {
      return await tryFetch(localUrl);
    } catch (eLocal) {
      console.warn('[update-check] Feed local indisponível:', eLocal);
      return { latest: '0.0.0', url: '', changelog: '' };
    }
  }

  function compareVersions(a, b){
    // retorna 1 se a>b, -1 se a<b, 0 se igual
    const pa = String(a).split('.').map(x => parseInt(x, 10) || 0);
    const pb = String(b).split('.').map(x => parseInt(x, 10) || 0);
    for (let i=0;i<Math.max(pa.length, pb.length);i++){
      const va = pa[i] || 0;
      const vb = pb[i] || 0;
      if (va > vb) return 1;
      if (va < vb) return -1;
    }
    return 0;
  }

  async function checkForUpdates(){
    const [local, feed] = await Promise.all([getLocalVersion(), fetchUpdateFeed()]);
    if (compareVersions(feed.latest, local) > 0){
      const msg = `Uma nova versão (${feed.latest}) está disponível.\n\n` +
                  (feed.changelog ? `Novidades: ${feed.changelog}\n\n` : '') +
                  'Deseja baixar agora?';
      const ok = window.confirm(msg);
      if (ok && feed.url){
        try { window.open(feed.url, '_blank'); } catch(e){ console.warn('Falha ao abrir link de download:', e); }
      }
    } else {
      // opcional: log
      console.info(`[update-check] Versão atual (${local}) está em dia.`);
    }
  }

  document.addEventListener('DOMContentLoaded', function(){
    // pequena espera para não competir com outras inicializações
    setTimeout(checkForUpdates, 1500);
  });
})();