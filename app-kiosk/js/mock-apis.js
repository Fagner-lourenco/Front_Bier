/**
 * MOCK-APIS.JS
 * APIs falsas para desenvolvimento sem backend
 */

const MockAPIs = {
  enabled: true,
  simulateLatency: true,
  latencyMs: 800, // ms de latência simulada
  beverages: null,
  currentDispenseProgress: 0,
  dispenseInterval: null,
  authorizedVolume: 300, // Volume autorizado pelo pagamento

  /**
   * Inicializa mock APIs
   */
  init() {
    // Carrega bebidas mock (sincronizado com SaaS)
    this.beverages = [
      {
        id: '03c91279-bb24-467c-9a42-fb707a4eaa9d',
        name: 'Chopp Pilsen',
        style: 'Pilsen',
        abv: 4.5,
        price_per_ml: 0.04,
        emoji: '🍺',
        image_url: 'assets/images/beverages/chopp.png',
        active: true
      },
      {
        id: 'f31ce553-5a02-4029-a100-1b689761f5fd',
        name: 'Chopp IPA',
        style: 'IPA',
        abv: 6.5,
        price_per_ml: 0.06,
        emoji: '🍻',
        image_url: 'assets/images/beverages/ipa.png',
        active: true
      },
      {
        id: 'e83b3c86-46a6-4eeb-8882-2a91eacf892f',
        name: 'Água de Coco',
        style: 'Natural',
        abv: 0,
        price_per_ml: 0.03,
        emoji: '🥥',
        image_url: 'assets/images/beverages/agua-coco.png',
        active: true
      },
      {
        id: 'd48c308a-b8e0-4bf6-ab17-eeca6b2f92ef',
        name: 'Suco de Laranja',
        style: 'Natural',
        abv: 0,
        price_per_ml: 0.035,
        emoji: '🧃',
        image_url: 'assets/images/beverages/suco-laranja.png',
        active: true
      }
    ];

    this.log('Mock APIs inicializadas com', this.beverages.length, 'bebidas');
  },

  /**
   * Simula latência de rede
   */
  async simulateDelay() {
    if (this.simulateLatency) {
      return new Promise(resolve => setTimeout(resolve, this.latencyMs));
    }
  },

  /**
   * GET /api/v1/beverages
   */
  async getBeverages() {
    await this.simulateDelay();
    
    return {
      ok: true,
      data: {
        beverages: this.beverages.map(b => ({
          id: b.id,
          name: b.name,
          style: b.style,
          abv: b.abv,
          price_per_ml: b.price_per_ml
        }))
      }
    };
  },

  /**
   * POST /api/v1/authorize
   */
  async authorize(machineId, beverageId, volumeMl, paymentMethod, totalValue) {
    await this.simulateDelay();

    // 10% de chance de falhar pagamento
    const shouldFail = Math.random() < 0.1;
    
    if (shouldFail) {
      return {
        ok: true,
        data: {
          status: 'DENIED',
          reason: 'Saldo insuficiente'
        }
      };
    }

    // Sucesso
    const expiresAt = new Date(Date.now() + 90000).toISOString(); // 90s
    
    return {
      ok: true,
      data: {
        status: 'AUTHORIZED',
        token: Validators.generateId('TKN'),
        signature: 'mock_hmac_sha256_' + Math.random().toString(36).substr(2, 9),
        expires_in: 90,
        expires_at: expiresAt
      }
    };
  },

  /**
   * GET /api/v1/transactions/latest
   */
  async getLatestTransactions(machineId) {
    await this.simulateDelay();
    
    return {
      ok: true,
      data: {
        transactions: []
      }
    };
  },

  /**
   * POST /api/v1/consume
   */
  async reportConsume(tokenId, machineId, mlServed, mlAuthorized, saleId, status, startedAt, finishedAt) {
    await this.simulateDelay();
    
    this.log('Consumo registrado:', { tokenId, machineId, mlServed, mlAuthorized, saleId, status });
    
    return {
      ok: true,
      data: {
        status: 'OK',
        message: 'Consumo registrado',
        consumption_id: 'MOCK_CONSUMPTION_' + Date.now()
      }
    };
  },

  /**
   * POST /edge/authorize - Mock para EDGE
   * Recebe token HMAC e simula autorização
   */
  async edgeAuthorize(token) {
    await this.simulateDelay();
    
    // Tenta decodificar payload do token para pegar volume
    let volumeMl = this.authorizedVolume || 300;
    try {
      const [payloadB64] = token.split('.');
      const payloadJson = atob(payloadB64.replace(/-/g, '+').replace(/_/g, '/'));
      const payload = JSON.parse(payloadJson);
      if (payload.volume_ml) {
        volumeMl = payload.volume_ml;
        this.setAuthorizedVolume(volumeMl);
      }
    } catch (e) {
      console.log('[MockAPIs] Não foi possível decodificar token, usando volume padrão');
    }
    
    return {
      ok: true,
      data: {
        authorized: true,
        result: {
          success: true,
          status: 'completed',
          sale_id: 'mock-sale-' + Date.now(),
          volume_authorized_ml: volumeMl,
          volume_dispensed_ml: volumeMl,
          duration_seconds: volumeMl / 100, // ~100ml/s
          pulse_count: Math.round(volumeMl * 0.45)
        }
      }
    };
  },

  /**
   * GET /edge/status - Simula progresso de extração
   */
  async getEdgeStatus() {
    // Incrementa progresso (entre 2% e 8% por chamada para simular fluxo realista)
    const increment = 2 + Math.random() * 6;
    this.currentDispenseProgress = Math.min(
      this.currentDispenseProgress + increment,
      100
    );

    // Garante que não passa de 100%
    if (this.currentDispenseProgress > 100) {
      this.currentDispenseProgress = 100;
    }

    const mlAuthorized = this.authorizedVolume; // Usa volume real autorizado
    const mlServed = Math.round((this.currentDispenseProgress / 100) * mlAuthorized);

    // Delay mínimo para simular polling
    await new Promise(resolve => setTimeout(resolve, 50));

    return {
      ok: true,
      data: {
        state: this.currentDispenseProgress >= 100 ? 'FINISHED' : 'DISPENSING',
        ml_served: Math.min(mlServed, mlAuthorized), // GARANTE que nunca passa do autorizado
        ml_authorized: mlAuthorized,
        percentage: Math.round(this.currentDispenseProgress),
        timestamp: new Date().toISOString()
      }
    };
  },

  /**
   * POST /edge/maintenance
   */
  async edgeMaintenance(action) {
    await this.simulateDelay();
    
    return {
      ok: true,
      data: {
        status: 'OK',
        mode: action === 'start' ? 'MAINTENANCE' : 'NORMAL'
      }
    };
  },

  /**
   * Retorna uma bebida mock por ID
   */
  getBeverageById(id) {
    return this.beverages.find(b => b.id === id);
  },

  /**
   * Reseta progresso de dispensing
   */
  resetDispenseProgress() {
    this.currentDispenseProgress = 0;
    // Não resetar authorizedVolume aqui - será definido pelo processPaymentWithSDK
  },

  /**
   * Define volume autorizado para esta extração
   */
  setAuthorizedVolume(volume) {
    this.authorizedVolume = volume;
    this.log('Volume autorizado definido:', volume, 'ml');
  },

  /**
   * Log interno
   */
  log(...args) {
    if (window.APP && window.APP.debug) {
      console.log('[MockAPIs]', ...args);
    }
  }
};

// Exportar para uso global
window.MockAPIs = MockAPIs;
