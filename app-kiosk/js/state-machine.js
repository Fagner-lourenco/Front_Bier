/**
 * STATE-MACHINE.JS
 * Máquina de estados do APP
 */

class StateMachine {
  constructor(config) {
    this.config = config;
    this.currentState = null; // Inicia como null, será configurado no initApp
    this.previousState = null;
    this.stateData = {};
    this.timeout = null;
    this.listeners = {};
    
    this.defineStates();
    this.log('State Machine inicializado');
  }

  /**
   * Define os states disponíveis e seus timeouts
   */
  defineStates() {
    this.states = {
      BOOT: {
        timeout: this.config.ui.boot_duration_ms,
        next: 'IDLE'
      },
      IDLE: {
        timeout: this.config.ui.idle_timeout_ms,
        next: 'IDLE' // volta para si mesmo
      },
      CONFIRM_AGE: {
        timeout: this.config.ui.confirm_age_timeout_ms,
        next: 'IDLE'
      },
      SELECT_VOLUME: {
        timeout: this.config.ui.select_volume_timeout_ms || 60000,
        next: 'IDLE'
      },
      SELECT_PAYMENT: {
        timeout: this.config.ui.select_payment_timeout_ms || 60000,
        next: 'IDLE'
      },
      AWAITING_PAYMENT: {
        timeout: this.config.ui.awaiting_payment_timeout_ms || 120000,
        next: 'IDLE' // timeout volta para IDLE
      },
      PAYMENT_DENIED: {
        timeout: 3000,
        next: 'IDLE'
      },
      AUTHORIZED: {
        timeout: 1000,
        next: 'DISPENSING'
      },
      DISPENSING: {
        timeout: this.config.ui.dispensing_timeout_ms || 60000,
        next: 'IDLE'
      },
      FINISHED: {
        timeout: this.config.ui.finished_timeout_ms,
        next: 'IDLE'
      }
    };
  }

  /**
   * Muda para um novo estado
   */
  setState(newState, data = {}) {
    if (!this.states[newState]) {
      this.log('ERRO: State inválido:', newState);
      return false;
    }

    if (this.currentState === newState && Object.keys(data).length === 0) {
      this.log('State já é', newState, 'ignorando');
      return false;
    }

    // Sai do state anterior
    this.onStateExit(this.currentState);

    // Muda state
    this.previousState = this.currentState;
    this.currentState = newState;
    // Preserva dados anteriores se não foram passados novos (ex: timeout automático)
    this.stateData = Object.keys(data).length > 0 ? data : this.stateData;

    // Entra no novo state
    this.onStateEnter(newState);

    this.log(`State change: ${this.previousState} → ${newState}`, this.stateData);
    this.emit('stateChange', { from: this.previousState, to: newState, data: this.stateData });

    return true;
  }

  /**
   * Roda ao sair de um state
   */
  onStateExit(state) {
    // Limpa timeout anterior
    if (this.timeout) {
      clearTimeout(this.timeout);
      this.timeout = null;
    }

    // Limpa listener de polling se houver
    if (state === 'DISPENSING' && window.Polling) {
      Polling.stop();
    }

    // Lógica específica ao sair de cada state
    switch (state) {
      case 'BOOT':
        break;
      case 'IDLE':
        // Limpa dados ao sair
        this.stateData = {};
        break;
      case 'DISPENSING':
        // Salva dados de consumo
        break;
      case 'FINISHED':
        // Reset dados
        this.stateData = {};
        break;
    }
  }

  /**
   * Roda ao entrar em um state
   */
  onStateEnter(state) {
    const stateConfig = this.states[state];

    // Salva no localStorage para recovery
    Storage.saveAppState(state, this.stateData);

    // Configura timeout do state
    if (stateConfig.timeout) {
      this.log(`⏱️ Timeout de ${stateConfig.timeout}ms configurado para ${state}`);
      this.timeout = setTimeout(() => {
        this.log(`⏱️ TIMEOUT DISPARADO! ${state} → ${stateConfig.next}`);
        this.setState(stateConfig.next);
      }, stateConfig.timeout);
    } else {
      this.log(`⏱️ Sem timeout para ${state}`);
    }

    // Lógica específica ao entrar em cada state
    switch (state) {
      case 'BOOT':
        this.log('🚀 APP booting...');
        break;

      case 'IDLE':
        this.log('Aguardando interação do usuário');
        // Reset do progresso apenas se mock ativo
        if (this.config.api.use_mock && window.MockAPIs) {
          MockAPIs.resetDispenseProgress();
        }
        break;

      case 'PAYMENT_PROCESSING':
        this.log('Processing payment...');
        break;

      case 'DISPENSING':
        this.log('Starting to dispense');
        // Registra timestamp de início para reportar ao SaaS
        this.stateData.dispensingStartedAt = new Date().toISOString();
        
        // Para MOCK: inicia polling para simular progresso
        // Para EDGE REAL: o listener em main.js cuida de emitir o evento final
        // Polling só é necessário se não temos resultado do EDGE ainda
        if (this.config.api.use_mock && window.Polling) {
          this.log('Modo mock - iniciando polling para simular progresso');
          Polling.start(this.config.ui.polling_ms);
        } else {
          this.log('Modo EDGE real - aguardando evento de conclusão');
        }
        break;

      case 'FINISHED':
        this.log('Finished, going back to IDLE');
        break;
    }
  }

  /**
   * Registra listener para eventos
   */
  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  /**
   * Remove listener
   */
  off(event, callback) {
    if (!this.listeners[event]) return;
    this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
  }

  /**
   * Emite evento
   */
  emit(event, data) {
    if (!this.listeners[event]) return;
    this.listeners[event].forEach(callback => callback(data));
  }

  /**
   * Retorna estado atual
   */
  getState() {
    return this.currentState;
  }

  /**
   * Retorna dados do estado atual
   */
  getStateData() {
    return this.stateData;
  }

  /**
   * Atualiza dados do estado atual
   */
  updateStateData(updates) {
    this.stateData = { ...this.stateData, ...updates };
    Storage.saveAppState(this.currentState, this.stateData);
  }

  /**
   * Recupera estado anterior
   */
  getPreviousState() {
    return this.previousState;
  }

  /**
   * Log interno
   */
  log(...args) {
    if (window.APP && window.APP.debug) {
      console.log('[StateMachine]', ...args);
    }
  }
}

// Exportar para uso global
window.StateMachine = StateMachine;
