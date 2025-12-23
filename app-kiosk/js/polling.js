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
      
      // Atualiza o state data do StateMachine com os valores atuais
      if (window.StateMachineInstance && status.dispenser) {
        window.StateMachineInstance.updateStateData({
          dispensing_status: status.dispenser.status,
          volume_dispensed: status.dispenser.volume_dispensed_ml || 0
        });
      }
      
      this.emitStatus(status);

      // Se a dispensa foi completada, para o polling e transiciona
      if (status.dispenser && status.dispenser.status) {
        const dispenserStatus = status.dispenser.status.toUpperCase();
        
        if (dispenserStatus === 'COMPLETED') {
          this.log(`✅ Dispensing COMPLETED! Volume: ${status.dispenser.volume_dispensed_ml}ml`);
          this.stop();
          
          // Transiciona para FINISHED
          if (window.StateMachineInstance) {
            window.StateMachineInstance.setState('FINISHED', status.dispenser);
          }
        } else if (dispenserStatus === 'INTERRUPTED' || dispenserStatus === 'ERROR') {
          this.log(`⚠️ Dispensing ${dispenserStatus}! Error: ${status.dispenser.error_message}`);
          this.stop();
          
          // Volta para IDLE em caso de erro
          if (window.StateMachineInstance) {
            window.StateMachineInstance.setState('IDLE', { error: status.dispenser.error_message });
          }
        }
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

    // Atualiza state data com os campos corretos do EDGE
    if (window.StateMachineInstance && status.dispenser) {
      const dispenserData = status.dispenser;
      
      // Calcula percentual (se temos volume_authorized_ml do payload)
      const volumeAuthorized = window.StateMachineInstance.getData().volume || 500;
      const percentage = volumeAuthorized > 0 
        ? Math.round((dispenserData.volume_dispensed_ml / volumeAuthorized) * 100)
        : 0;
      
      window.StateMachineInstance.updateStateData({
        ml_served: dispenserData.volume_dispensed_ml,
        ml_authorized: volumeAuthorized,
        percentage: Math.min(percentage, 100),
        state: dispenserData.status
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
