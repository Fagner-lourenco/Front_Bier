/**
 * POLLING.JS
 * Polling contínuo para obter status do EDGE durante DISPENSING
 */

const Polling = {
  active: false,
  intervalId: null,
  intervalMs: 300,
  config: null,
  isFetching: false, // Flag anti-race condition

  /**
   * Inicializa polling
   */
  init(config) {
    this.config = config;
    this.intervalMs = config.ui.polling_ms;
    this.log('Polling inicializado com intervalo de', this.intervalMs, 'ms');
  },

  /**
   * Inicia polling
   */
  start(intervalMs = null) {
    if (this.active) {
      this.log('Polling já está ativo');
      return;
    }

    if (intervalMs) {
      this.intervalMs = intervalMs;
    }

    this.active = true;
    this.log('Iniciando polling a cada', this.intervalMs, 'ms');

    // Faz primeira requisição imediatamente
    this.fetchStatus();

    // Depois faz polling
    this.intervalId = setInterval(() => {
      this.fetchStatus();
    }, this.intervalMs);
  },

  /**
   * Para polling
   */
  stop() {
    if (!this.active) return;

    this.active = false;
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }

    this.log('Polling parado');
  },

  /**
   * Busca status do EDGE (com proteção anti-race condition)
   */
  async fetchStatus() {
    // Evita chamadas simultâneas
    if (this.isFetching) {
      this.log('fetchStatus já em andamento, ignorando');
      return;
    }
    
    this.isFetching = true;
    
    try {
      let result;

      // Usa mock APIs se habilitado
      if (this.config && this.config.api.use_mock) {
        result = await MockAPIs.getEdgeStatus();
      } else {
        result = await API.getEdgeStatus();
      }

      if (!result.ok) {
        this.log('ERRO ao obter status:', result.error);
        this.emitError(result.error);
        return;
      }

      const status = result.data;
      this.emitStatus(status);

      // Se chegou em FINISHED, para o polling
      if (status.state === 'FINISHED') {
        this.log('Dispensing finalizado, parando polling');
        this.stop();
      }
    } catch (error) {
      this.log('ERRO no fetchStatus:', error.message);
      this.emitError(error.message);
    } finally {
      this.isFetching = false;
    }
  },

  /**
   * Emite evento de status
   */
  emitStatus(status) {
    if (!window.APP) return;
    
    // Dispara evento customizado
    const event = new CustomEvent('dispensingStatus', {
      detail: status
    });
    document.dispatchEvent(event);

    // Atualiza state data
    if (window.StateMachineInstance) {
      window.StateMachineInstance.updateStateData({
        ml_served: status.ml_served,
        ml_authorized: status.ml_authorized,
        percentage: status.percentage,
        state: status.state
      });
    }

    this.log('Status emitido:', status);
  },

  /**
   * Emite evento de erro
   */
  emitError(error) {
    if (!window.APP) return;
    
    const event = new CustomEvent('dispensingError', {
      detail: { error }
    });
    document.dispatchEvent(event);

    this.log('Erro emitido:', error);
  },

  /**
   * Retorna se está ativo
   */
  isActive() {
    return this.active;
  },

  /**
   * Log interno
   */
  log(...args) {
    if (window.APP && window.APP.debug) {
      console.log('[Polling]', ...args);
    }
  }
};

// Exportar para uso global
window.Polling = Polling;

// Listeners para eventos de dispensing
document.addEventListener('dispensingStatus', (event) => {
  if (window.UI) {
    UI.updateDispensingProgress(event.detail);
  }
});

document.addEventListener('dispensingError', (event) => {
  if (window.StateMachineInstance) {
    window.StateMachineInstance.setState('IDLE');
  }
});
