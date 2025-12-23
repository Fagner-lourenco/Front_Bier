/**
 * STATE-MACHINE.JS
 * Máquina de estados central da aplicação
 * Transições, timeouts, eventos
 */

class StateMachine {
  constructor(config) {
    this.config = config;
    this.state = null;
    this.previousState = null;
    this.data = {};
    this.timeout = null;
    this.listeners = [];

    console.log('[StateMachine] State Machine inicializado');
  }

  /**
   * Define estados válidos e suas transições
   */
  defineStates() {
    return {
      BOOT: {
        next: 'IDLE',
        timeout: this.config.ui.boot_duration_ms,
        onEnter: () => {},
        onExit: () => {},
      },
      IDLE: {
        next: null,
        timeout: this.config.ui.idle_timeout_ms,
        onEnter: () => {
          // Renderiza cardápio
          UI.render('IDLE', { beverages: window.APP.beverages || [] });
        },
        onExit: () => {},
      },
      CONFIRM_AGE: {
        next: 'SELECT_VOLUME',
        timeout: this.config.ui.confirm_age_timeout_ms,
        onEnter: () => {
          UI.render('CONFIRM_AGE', this.data);
        },
        onExit: () => {},
      },
      SELECT_VOLUME: {
        next: 'SELECT_PAYMENT',
        timeout: this.config.ui.select_volume_timeout_ms,
        onEnter: () => {
          UI.render('SELECT_VOLUME', this.data);
        },
        onExit: () => {},
      },
      SELECT_PAYMENT: {
        next: 'AWAITING_PAYMENT',
        timeout: this.config.ui.select_payment_timeout_ms,
        onEnter: () => {
          UI.render('SELECT_PAYMENT', this.data);
        },
        onExit: () => {},
      },
      AWAITING_PAYMENT: {
        next: null,
        timeout: this.config.ui.awaiting_payment_timeout_ms,
        onEnter: () => {
          UI.render('AWAITING_PAYMENT', this.data);
        },
        onExit: () => {},
      },
      PAYMENT_DENIED: {
        next: 'IDLE',
        timeout: 3000,
        onEnter: () => {
          UI.render('PAYMENT_DENIED', this.data);
        },
        onExit: () => {
          this.data = {};
        },
      },
      AUTHORIZED: {
        next: 'DISPENSING',
        timeout: 1000,
        onEnter: () => {
          UI.render('AUTHORIZED', this.data);
        },
        onExit: () => {},
      },
      DISPENSING: {
        next: null,
        timeout: this.config.ui.dispensing_timeout_ms,
        onEnter: () => {
          UI.render('DISPENSING', this.data);
          // Inicia polling no EDGE
          if (this.config.api.use_mock) {
            Polling.startMock();
          } else {
            Polling.start();
          }
        },
        onExit: () => {
          Polling.stop();
        },
      },
      FINISHED: {
        next: 'IDLE',
        timeout: this.config.ui.finished_timeout_ms,
        onEnter: () => {
          UI.render('FINISHED', this.data);
        },
        onExit: () => {
          this.data = {};
        },
      },
    };
  }

  /**
   * Muda para novo estado
   */
  setState(newState, data = {}) {
    const states = this.defineStates();

    // Valida estado
    if (!states[newState]) {
      console.error(`[StateMachine] Estado inválido: ${newState}`);
      return false;
    }

    const stateConfig = states[newState];

    // Limpa timeout anterior
    if (this.timeout) {
      clearTimeout(this.timeout);
      this.timeout = null;
    }

    // Executa callback de saída do estado anterior
    if (this.state && states[this.state]) {
      this.onStateExit(this.state);
    }

    // Armazena dados do novo estado
    this.previousState = this.state;
    this.state = newState;
    this.data = { ...this.data, ...data };

    // Emite evento de mudança de estado
    this.emit('state:change', { from: this.previousState, to: newState, data: this.data });

    // Executa callback de entrada do novo estado
    this.onStateEnter(newState);

    // Define timeout para transição automática
    if (stateConfig.timeout) {
      console.log(`[StateMachine] ⏱️ Timeout de ${stateConfig.timeout}ms configurado para ${newState}`);
      this.timeout = setTimeout(() => {
        console.log(`[StateMachine] ⏱️ TIMEOUT DISPARADO! ${newState} → ${stateConfig.next || 'TIMEOUT'}`);
        if (stateConfig.next) {
          this.setState(stateConfig.next);
        }
      }, stateConfig.timeout);
    }

    return true;
  }

  /**
   * Callback executado ao entrar em um estado
   */
  onStateEnter(state) {
    const states = this.defineStates();
    if (states[state] && states[state].onEnter) {
      console.log(`[StateMachine] State change: ${this.previousState} → ${state}`, this.data);
      states[state].onEnter();
    }
  }

  /**
   * Callback executado ao sair de um estado
   */
  onStateExit(state) {
    const states = this.defineStates();
    if (states[state] && states[state].onExit) {
      states[state].onExit();
    }
  }

  /**
   * Obtém estado atual
   */
  getState() {
    return this.state;
  }

  /**
   * Obtém dados do estado
   */
  getData() {
    return this.data;
  }

  /**
   * Alias para getData()
   */
  getStateData() {
    return this.data;
  }

  /**
   * Atualiza dados do estado atual
   */
  updateStateData(newData) {
    this.data = { ...this.data, ...newData };
    this.emit('state:data-updated', this.data);
    return this.data;
  }

  /**
   * Força transição imediata
   */
  forceTransition(toState, data = {}) {
    console.log(`[StateMachine] Transição forçada: ${this.state} → ${toState}`);
    this.setState(toState, data);
  }

  /**
   * Registra listener para eventos
   */
  on(event, callback) {
    this.listeners.push({ event, callback });
  }

  /**
   * Remove listener
   */
  off(event, callback) {
    this.listeners = this.listeners.filter(l => l.event !== event || l.callback !== callback);
  }

  /**
   * Emite evento
   */
  emit(event, data) {
    this.listeners.forEach(l => {
      if (l.event === event) {
        l.callback(data);
      }
    });
  }
}
