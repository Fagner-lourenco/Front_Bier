/**
 * API.JS
 * Chamadas HTTP para SaaS e EDGE
 */

const API = {
  config: null,
  baseUrlSaaS: 'http://localhost:3001',
  baseUrlEdge: 'http://localhost:5000',
  apiKey: null,
  machineId: null,
  timeout: 30000,

  /**
   * Inicializa API com configuração
   */
  init(config) {
    this.config = config;
    this.baseUrlSaaS = config.api.saas_url;
    this.baseUrlEdge = config.api.edge_url;
    
    // API Key para autenticação com SaaS
    if (config.machine) {
      this.apiKey = config.machine.api_key;
      this.machineId = config.machine.id;
    }
    
    this.log('API inicializado', { ...config.api, apiKey: this.apiKey ? '***' : null });
  },

  /**
   * Faz request HTTP genérico
   */
  async request(method, url, data = null) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => {
      console.warn(`[API] Timeout de ${this.timeout}ms para ${method} ${url}`);
      controller.abort();
    }, this.timeout);

    console.log(`[API] Iniciando ${method} ${url}`, data ? JSON.stringify(data).substring(0, 100) : '');

    try {
      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      };
      
      // Adiciona API Key se configurada (para SaaS)
      if (this.apiKey && url.includes(this.baseUrlSaaS)) {
        headers['X-API-Key'] = this.apiKey;
      }
      
      const options = {
        method,
        headers,
        signal: controller.signal
      };

      if (data) {
        options.body = JSON.stringify(data);
      }

      console.log(`[API] Enviando fetch ${method} ${url}...`);
      const response = await fetch(url, options);
      clearTimeout(timeoutId);
      console.log(`[API] Resposta recebida: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        const errorBody = await response.text().catch(() => 'Erro ao ler resposta');
        console.error(`[API] Erro HTTP: ${response.status}`, errorBody);
        return { ok: false, error: `HTTP ${response.status}: ${response.statusText}`, details: errorBody };
      }

      const responseData = await response.json();
      this.log(`${method} ${url}`, responseData);
      return { ok: true, data: responseData };
    } catch (error) {
      clearTimeout(timeoutId);
      console.error(`[API] Exceção em ${method} ${url}:`, error);
      
      // Tratamento específico para erros de rede
      let errorMessage = error.message;
      if (error.name === 'AbortError') {
        errorMessage = 'Tempo limite excedido (timeout)';
      } else if (error.name === 'TypeError' && error.message.includes('fetch')) {
        errorMessage = 'Sem conexão com o servidor';
      } else if (error.name === 'TypeError') {
        errorMessage = 'Erro de rede: ' + error.message;
      }
      
      this.log(`${method} ${url} ERROR`, errorMessage);
      return { ok: false, error: errorMessage };
    }
  },

  /**
   * GET /api/v1/beverages - Retorna cardápio
   */
  async getBeverages() {
    const url = `${this.baseUrlSaaS}/api/v1/beverages`;
    return this.request('GET', url);
  },

  /**
   * POST /api/v1/sales - Registra venda após pagamento aprovado pelo SDK
   */
  async registerSale(saleData) {
    const url = `${this.baseUrlSaaS}/api/v1/sales`;
    return this.request('POST', url, saleData);
  },

  /**
   * GET /api/v1/transactions/latest - Recupera transações pendentes
   */
  async getLatestTransactions(machineId) {
    const url = `${this.baseUrlSaaS}/api/v1/transactions/latest?machine_id=${machineId}`;
    return this.request('GET', url);
  },

  /**
   * POST /api/v1/consumptions - Registra consumo realizado (EDGE envia)
   */
  async reportConsume(tokenId, machineId, mlServed, mlAuthorized, saleId, status, startedAt, finishedAt) {
    const url = `${this.baseUrlSaaS}/api/v1/consumptions`;
    const data = {
      token_id: tokenId,
      machine_id: machineId,
      ml_served: mlServed,
      ml_authorized: mlAuthorized,
      sale_id: saleId,
      status: status,
      started_at: startedAt,
      finished_at: finishedAt
    };
    return this.request('POST', url, data);
  },

  /**
   * POST /edge/authorize - Autoriza dispensação com EDGE
   * Envia token HMAC no formato: base64(payload).base64(signature)
   * NOTA: Esta operação é BLOQUEANTE - pode demorar até 2 minutos para dispensar
   */
  async edgeAuthorize(token) {
    const url = `${this.baseUrlEdge}/edge/authorize`;
    const data = { token: token };
    // Timeout maior para dispensação (120s + margem)
    return this.requestWithTimeout('POST', url, data, 150000);
  },

  /**
   * Request com timeout customizado
   */
  async requestWithTimeout(method, url, data, customTimeout) {
    const originalTimeout = this.timeout;
    this.timeout = customTimeout;
    try {
      return await this.request(method, url, data);
    } finally {
      this.timeout = originalTimeout;
    }
  },

  /**
   * GET /edge/status - Obtém status atual do EDGE
   */
  async getEdgeStatus() {
    const url = `${this.baseUrlEdge}/edge/status`;
    return this.request('GET', url);
  },

  /**
   * POST /edge/maintenance - Ativa/desativa modo manutenção
   */
  async edgeMaintenance(action) {
    const url = `${this.baseUrlEdge}/edge/maintenance`;
    const data = { action: action };
    return this.request('POST', url, data);
  },

  /**
   * Testa conexão com SaaS
   */
  async testSaaSConnection() {
    const result = await this.getBeverages();
    return result.ok;
  },

  /**
   * Testa conexão com EDGE
   */
  async testEdgeConnection() {
    const result = await this.getEdgeStatus();
    return result.ok;
  },

  /**
   * Log interno
   */
  log(message, data = '') {
    if (window.APP && window.APP.debug) {
      console.log(`[API] ${message}`, data);
    }
  }
};

// Exportar para uso global
window.API = API;
