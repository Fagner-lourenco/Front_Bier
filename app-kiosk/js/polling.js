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
  errorCount: 0,

  /**
   * Inicializa polling
   */
  init(config) {
    this.config = config;
    this.intervalMs = config.ui?.polling_ms || this.intervalMs;
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

  startMock(intervalMs = null) {
    this.start(intervalMs);
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

    // Se não estamos em DISPENSING, não precisa continuar polling
    if (!window.StateMachineInstance || window.StateMachineInstance.getState() !== 'DISPENSING') {
      this.stop();
      return;
    }
    
    this.isFetching = true;
    this.errorCount = 0; // reset a cada ciclo iniciado
    
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
      
      // Atualiza o state data do StateMachine com os valores atuais
      if (window.StateMachineInstance) {
        const dispenserData = status.dispenser || status;
        window.StateMachineInstance.updateStateData({
          dispensing_status: dispenserData.status,
          volume_dispensed: dispenserData.volume_dispensed_ml || dispenserData.ml_served || 0
        });
      }
      
      this.emitStatus(status);

      // Reset erro se sucesso
      this.errorCount = 0;

      // Se a dispensa foi completada/erro, para o polling e transiciona
      const dispenserData = status.dispenser || status;
      const dispenserStatus = (dispenserData.status || status.state || '').toString().toUpperCase();
      
      if (dispenserStatus === 'COMPLETED' || dispenserStatus === 'FINISHED') {
        const stateData = (window.StateMachineInstance && window.StateMachineInstance.getData()) || {};
        const volFinal = dispenserData.volume_dispensed_ml ?? dispenserData.ml_served ?? stateData.ml_served ?? 0;
        this.log(`✅ Dispensing ${dispenserStatus}! Volume: ${volFinal}ml`);
        this.stop();
        
        // NÃO transiciona aqui - o main.js vai fazer isso ao processar o evento 'dispensingStatus'
        // Apenas emite o evento para que o handler no main.js possa processar corretamente
      } else if (dispenserStatus === 'INTERRUPTED' || dispenserStatus === 'ERROR') {
        this.log(`⚠️ Dispensing ${dispenserStatus}! Error: ${dispenserData.error_message || dispenserData.error}`);
        this.stop();
        
        // Volta para IDLE em caso de erro
        if (window.StateMachineInstance) {
          window.StateMachineInstance.setState('IDLE', { error: dispenserData.error_message || dispenserData.error });
        }
      }
    } catch (error) {
      this.log('ERRO no fetchStatus:', error.message);
      this.emitError(error.message);
      this.errorCount += 1;
      // Para evitar flood, interrompe após 3 erros seguidos
      if (this.errorCount >= 3) {
        this.log('Parando polling após erros consecutivos');
        this.stop();
      }
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

    // Atualiza state data com os campos corretos do EDGE
    if (window.StateMachineInstance) {
      const stateData = window.StateMachineInstance.getData() || {};
      const dispenserData = status.dispenser || status;

      const volumeAuthorized = stateData.volume
        || dispenserData.ml_authorized
        || dispenserData.volume_authorized_ml
        || 500;

      const mlServed = dispenserData.volume_dispensed_ml
        || dispenserData.ml_served
        || 0;

      const percentage = dispenserData.percentage != null
        ? dispenserData.percentage
        : (volumeAuthorized > 0
          ? Math.round((mlServed / volumeAuthorized) * 100)
          : 0);

      window.StateMachineInstance.updateStateData({
        ml_served: mlServed,
        ml_authorized: volumeAuthorized,
        percentage: Math.min(percentage, 100),
        state: dispenserData.status || status.state
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
