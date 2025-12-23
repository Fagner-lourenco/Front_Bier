/**
 * UI.JS
 * Renderização de todas as telas
 */

const UI = {
  config: null,
  appContainer: null,
  currentBeverage: null,
  countdownInterval: null,

  /**
   * Inicializa UI
   */
  init(config) {
    this.config = config;
    this.appContainer = document.getElementById('app');
    this.log('UI inicializado');
  },

  /**
   * Retorna emoji da bebida pelo ID
   */
  getBeverageEmoji(beverageId) {
    const emojis = this.config.beverageEmojis || ['🍺', '🍻', '🥥', '🧃', '🥤'];
    const beverages = window.APP?.beverages || [];
    const index = beverages.findIndex(b => b.id === beverageId);
    return index >= 0 ? (emojis[index] || '🥤') : '🥤';
  },

  /**
   * Inicia countdown visível
   */
  startCountdown(elementId, seconds) {
    this.stopCountdown();
    let remaining = seconds;
    const el = document.getElementById(elementId);
    if (!el) return;
    
    this.countdownInterval = setInterval(() => {
      remaining--;
      const strong = el.querySelector('strong');
      if (strong) strong.textContent = remaining;
      if (remaining <= 0) this.stopCountdown();
    }, 1000);
  },

  /**
   * Para countdown
   */
  stopCountdown() {
    if (this.countdownInterval) {
      clearInterval(this.countdownInterval);
      this.countdownInterval = null;
    }
  },

  /**
   * Renderiza tela baseada no state
   */
  render(state, data = {}) {
    if (!this.appContainer) {
      this.log('ERRO: app container não encontrado');
      return;
    }

    // Para countdown anterior
    this.stopCountdown();

    this.log(`Renderizando state: ${state}`, data);

    // Limpa container
    this.appContainer.innerHTML = '';
    this.appContainer.className = `app-container state-${state.toLowerCase()}`;

    // Chama função de render específica
    const renderMethod = `render_${state}`;
    if (typeof this[renderMethod] === 'function') {
      this[renderMethod](data);
    } else {
      this.log('ERRO: método de render não encontrado:', renderMethod);
      this.renderNotFound(state);
    }
  },

  /**
   * TELA: BOOT
   */
  render_BOOT(data) {
    const html = `
      <div class="screen">
        <div class="screen-content">
          <div style="text-align: center;">
            <div class="logo-text">🍺 BierPass</div>
            <div class="boot-text">Verificando conexão...</div>
            <div style="margin-top: 40px;">
              <div class="spinner spinner-large"></div>
            </div>
          </div>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
  },

  /**
   * TELA: IDLE / HOME
   */
  render_IDLE(data) {
    // Carrega bebidas
    const beverages = data.beverages || [];
    const message = data.message || '';

    let cardsHtml = '';
    
    // Tratar lista vazia
    if (beverages.length === 0) {
      cardsHtml = `
        <div class="no-beverages texto-centro">
          <div class="emoji-gigante">🙅</div>
          <p>Nenhuma bebida disponível no momento</p>
          <p class="texto-secundario">Tente novamente em alguns instantes</p>
        </div>
      `;
    } else {
      beverages.forEach((drink, index) => {
        const emoji = this.getBeverageEmoji(drink.id);
        const volumes = this.config.volumes || [200, 300, 400, 500];
        const minPrice = Validators.formatCurrency(Validators.calculatePrice(volumes[0], drink.price_per_ml));
        const maxPrice = Validators.formatCurrency(Validators.calculatePrice(volumes[volumes.length - 1], drink.price_per_ml));
        
        const alcoholBadge = drink.abv > 0 
          ? `<div class="alcohol-badge">🔞 ${drink.abv}% ABV</div>`
          : `<div class="non-alcohol-badge">✅ Sem Álcool</div>`;
        
        cardsHtml += `
          <div class="beverage-card" role="button" tabindex="0" 
               onclick="handleBeverageSelect('${drink.id}')" 
               onkeypress="if(event.key==='Enter')handleBeverageSelect('${drink.id}')">
            <div class="beverage-image">${emoji}</div>
            <div class="beverage-info">
              <div class="beverage-name">${drink.name}</div>
              <div class="beverage-style">${drink.style}</div>
              ${alcoholBadge}
              <div class="beverage-price-range">
                ${minPrice} - ${maxPrice}
                <span class="price-hint">${volumes[0]}ml a ${volumes[volumes.length - 1]}ml</span>
              </div>
            </div>
          </div>
        `;
      });
    }

    const html = `
      <div class="screen">
        <!-- Breadcrumb -->
        <div class="breadcrumb">
          <span class="breadcrumb-step active">① Bebida</span>
          <span class="breadcrumb-arrow">→</span>
          <span class="breadcrumb-step">② Volume</span>
          <span class="breadcrumb-arrow">→</span>
          <span class="breadcrumb-step">③ Pagamento</span>
        </div>

        <div class="screen-header">
          <h1 class="screen-title">Escolha sua Bebida</h1>
          <p class="screen-subtitle">Toque para começar</p>
          ${message ? `<p class="alert-message">⚠️ ${message}</p>` : ''}
        </div>
        
        <div class="screen-content">
          <div class="beverages-grid">
            ${cardsHtml}
          </div>
        </div>

        <div class="screen-footer">
          <p id="idle-countdown" style="color: var(--text-light); font-size: 12px;">
            Reinicia em <strong>90</strong>s
          </p>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
    
    // Inicia countdown
    const idleSeconds = Math.floor((this.config.ui?.idle_timeout_ms || 90000) / 1000);
    this.startCountdown('idle-countdown', idleSeconds);
  },

  /**
   * TELA: SELECT_VOLUME
   */
  render_SELECT_VOLUME(data) {
    const beverage = data.beverage || {};
    const emoji = this.getBeverageEmoji(beverage.id);
    const volumes = this.config.volumes || [200, 300, 400, 500];

    // Labels dos tamanhos
    const sizeLabels = ['Pequeno', 'Médio ⭐', 'Grande', 'Família'];

    let buttonsHtml = '';
    volumes.forEach((volume, index) => {
      const price = Validators.calculatePrice(volume, beverage.price_per_ml);
      buttonsHtml += `
        <button class="botao-volume" onclick="selectVolume(this, ${volume})">
          <div class="volume-size-label">${sizeLabels[index] || 'Extra'}</div>
          <div class="volume-ml">${volume}ml</div>
          <div class="volume-price-btn">${Validators.formatCurrency(price)}</div>
        </button>
      `;
    });

    const html = `
      <div class="screen">
        <!-- Breadcrumb -->
        <div class="breadcrumb">
          <span class="breadcrumb-step completed">✓ Bebida</span>
          <span class="breadcrumb-arrow">→</span>
          <span class="breadcrumb-step active">② Volume</span>
          <span class="breadcrumb-arrow">→</span>
          <span class="breadcrumb-step">③ Pagamento</span>
        </div>

        <div class="screen-header">
          <h1 class="screen-title">Escolha o Tamanho</h1>
          <p class="screen-subtitle">${beverage.name} - ${beverage.style}</p>
        </div>

        <div class="screen-content">
          <div class="volume-display">
            <div class="volume-image">${emoji}</div>
          </div>

          <div class="volumes-buttons">
            ${buttonsHtml}
          </div>
        </div>

        <div class="screen-footer">
          <button class="botao botao-small botao-secondary" onclick="handleBack()">← Voltar</button>
          <p id="volume-countdown" class="texto-secundario mt-16">
            Reinicia em <strong>60</strong>s
          </p>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
    
    // Inicia countdown
    const volumeSeconds = Math.floor((this.config.ui?.select_volume_timeout_ms || 60000) / 1000);
    this.startCountdown('volume-countdown', volumeSeconds);
  },

  /**
   * TELA: CONFIRM_AGE
   */
  render_CONFIRM_AGE(data) {
    const beverage = data.beverage || {};
    const emoji = this.getBeverageEmoji(beverage.id);

    const html = `
      <div class="screen">
        <div class="screen-content">
          <div class="confirm-age-container">
            <div class="confirm-age-icon">🎂</div>
            <h2 class="confirm-age-message">
              Ops! Esta bebida é alcoólica
            </h2>
            
            <div class="beverage-preview">
              <div class="preview-emoji">${emoji}</div>
              <div class="preview-name">${beverage.name}</div>
              <div class="preview-abv">🔞 ${beverage.abv}% ABV</div>
            </div>

            <div class="confirm-age-important">
              Você confirma que tem <strong>18 anos ou mais</strong>?
            </div>

            <div class="confirm-age-buttons">
              <button class="botao botao-confirm yes" onclick="handleConfirmAge(true)">
                ✅ Sim, tenho +18
              </button>
              <button class="botao botao-confirm no" onclick="handleConfirmAge(false)">
                ← Escolher outra bebida
              </button>
            </div>

            <p id="age-countdown" style="margin-top: 20px; font-size: 12px; color: var(--text-light);">
              Volta ao menu em <strong>20</strong>s
            </p>
          </div>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
    
    // Inicia countdown
    const ageSeconds = Math.floor((this.config.ui?.confirm_age_timeout_ms || 20000) / 1000);
    this.startCountdown('age-countdown', ageSeconds);
  },

  /**
   * TELA: SELECT_PAYMENT
   */
  render_SELECT_PAYMENT(data) {
    const volume = data.volume || 0;
    const beverage = data.beverage || {};
    const total = Validators.calculatePrice(volume, beverage.price_per_ml);

    const html = `
      <div class="screen">
        <!-- Breadcrumb -->
        <div class="breadcrumb">
          <span class="breadcrumb-step completed">✓ Bebida</span>
          <span class="breadcrumb-arrow">→</span>
          <span class="breadcrumb-step completed">✓ Volume</span>
          <span class="breadcrumb-arrow">→</span>
          <span class="breadcrumb-step active">③ Pagamento</span>
        </div>

        <div class="screen-header">
          <h1 class="screen-title">Como você quer pagar?</h1>
        </div>

        <div class="screen-content">
          <div class="payment-summary">
            <div class="payment-title">Resumo do Pedido</div>
            <div class="payment-amount">${Validators.formatCurrency(total)}</div>
            <div class="payment-title">${beverage.name} - ${volume}ml</div>
          </div>

          <div class="payment-options">
            <button class="botao-payment" onclick="selectPayment(this, 'PIX')">
              <span class="payment-icon">📱</span>
              <span class="payment-label">PIX</span>
              <span class="payment-hint">Escaneie o QR Code</span>
            </button>
            <button class="botao-payment" onclick="selectPayment(this, 'CREDIT')">
              <span class="payment-icon">💳</span>
              <span class="payment-label">Crédito</span>
              <span class="payment-hint">Aproxime ou insira o cartão</span>
            </button>
            <button class="botao-payment" onclick="selectPayment(this, 'DEBIT')">
              <span class="payment-icon">💳</span>
              <span class="payment-label">Débito</span>
              <span class="payment-hint">Aproxime ou insira o cartão</span>
            </button>
          </div>
        </div>

        <div class="screen-footer">
          <button class="botao botao-small botao-secondary" onclick="handleBack()">← Voltar</button>
          <p id="payment-countdown" class="texto-secundario mt-16">
            Reinicia em <strong>60</strong>s
          </p>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
    
    // Inicia countdown
    const paymentSeconds = Math.floor((this.config.ui?.select_payment_timeout_ms || 60000) / 1000);
    this.startCountdown('payment-countdown', paymentSeconds);
  },

  /**
   * TELA: AWAITING_PAYMENT (aguardando maquininha/PIX)
   */
  render_AWAITING_PAYMENT(data) {
    const paymentMethod = data.paymentMethod || 'CARD';
    const total = data.total || 0;
    const isPix = paymentMethod.toUpperCase() === 'PIX';
    
    const timeoutSeconds = isPix 
      ? Math.floor((this.config.ui?.pix_timeout_ms || 300000) / 1000)
      : Math.floor((this.config.ui?.awaiting_payment_timeout_ms || 120000) / 1000);
    
    let contentHTML = '';
    
    if (isPix) {
      // Tela PIX com QR Code
      contentHTML = `
        <div class="awaiting-payment-container pix-mode">
          <h2 class="screen-title">📱 Pague com PIX</h2>
          
          <div class="pix-qr-container" id="pix-qr-container">
            <div class="pix-loading">
              <div class="spinner"></div>
              <p>Gerando QR Code...</p>
            </div>
          </div>
          
          <div class="payment-amount-display">${Validators.formatCurrency(total)}</div>
          
          <p class="payment-instruction">
            Escaneie o QR Code com seu aplicativo de banco
          </p>
          
          <div class="pix-timer" id="pix-timer">
            Expira em <strong>${Math.floor(timeoutSeconds / 60)}:${(timeoutSeconds % 60).toString().padStart(2, '0')}</strong>
          </div>
          
          <button class="botao botao-secondary mt-24" onclick="cancelPayment()">
            ✕ Cancelar
          </button>
        </div>
      `;
    } else {
      // Tela Cartão (maquininha)
      contentHTML = `
        <div class="awaiting-payment-container card-mode">
          <h2 class="screen-title">💳 Pagamento com Cartão</h2>
          
          <div class="card-animation-container">
            <div class="card-icon-animated">💳</div>
            <div class="arrow-animation">➜</div>
            <div class="machine-icon">🔲</div>
          </div>
          
          <div class="payment-amount-display">${Validators.formatCurrency(total)}</div>
          
          <p class="payment-instruction" id="payment-instruction">
            Aproxime ou insira o cartão na maquininha
          </p>
          
          <div class="payment-status-display" id="payment-status">
            <div class="spinner spinner-small"></div>
            <span>Aguardando cartão...</span>
          </div>
          
          <button class="botao botao-secondary mt-24" onclick="cancelPayment()">
            ✕ Cancelar
          </button>
        </div>
      `;
    }
    
    const html = `<div class="screen">${contentHTML}</div>`;
    this.appContainer.innerHTML = html;
    
    // Inicia countdown (visual apenas para PIX)
    if (isPix) {
      this.startPixCountdown(timeoutSeconds);
    }
  },

  /**
   * Countdown especial para PIX (minutos:segundos)
   */
  startPixCountdown(totalSeconds) {
    let remaining = totalSeconds;
    const timerEl = document.getElementById('pix-timer');
    
    this.countdownInterval = setInterval(() => {
      remaining--;
      if (timerEl) {
        const mins = Math.floor(remaining / 60);
        const secs = remaining % 60;
        const strong = timerEl.querySelector('strong');
        if (strong) strong.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
      }
      if (remaining <= 0) this.stopCountdown();
    }, 1000);
  },

  /**
   * Atualiza status do pagamento (chamado pelo SDK)
   */
  updatePaymentStatus(status, data = {}) {
    const statusEl = document.getElementById('payment-status');
    const instructionEl = document.getElementById('payment-instruction');
    const qrContainer = document.getElementById('pix-qr-container');
    
    switch (status) {
      case 'GENERATING_PIX':
        if (qrContainer) {
          qrContainer.innerHTML = `
            <div class="pix-loading">
              <div class="spinner"></div>
              <p>Gerando QR Code...</p>
            </div>
          `;
        }
        break;
        
      case 'WAITING_CARD':
        if (statusEl) {
          statusEl.innerHTML = `
            <div class="spinner spinner-small"></div>
            <span>Aguardando cartão...</span>
          `;
        }
        break;
        
      case 'PROCESSING':
        if (statusEl) {
          statusEl.innerHTML = `
            <div class="spinner spinner-small"></div>
            <span>Processando...</span>
          `;
        }
        if (instructionEl) {
          instructionEl.textContent = 'Não remova o cartão';
        }
        break;
        
      case 'PIX_GENERATED':
        if (qrContainer && data.qrCodeBase64) {
          qrContainer.innerHTML = `
            <img src="${data.qrCodeBase64}" alt="QR Code PIX" class="pix-qr-image" />
          `;
        }
        break;
        
      case 'APPROVED':
        if (statusEl) {
          statusEl.innerHTML = `
            <div class="success-icon">✅</div>
            <span class="success-text">Pagamento Aprovado!</span>
          `;
        }
        if (instructionEl) {
          instructionEl.textContent = 'Pode retirar o cartão';
        }
        break;
        
      case 'DENIED':
        if (statusEl) {
          statusEl.innerHTML = `
            <div class="error-icon">❌</div>
            <span class="error-text">Pagamento Negado</span>
          `;
        }
        break;
        
      case 'CANCELLED':
        if (statusEl) {
          statusEl.innerHTML = `
            <span>Cancelado pelo usuário</span>
          `;
        }
        break;
    }
  },

  /**
   * TELA: PAYMENT_PROCESSING (legado - redireciona para AWAITING_PAYMENT)
   */
  render_PAYMENT_PROCESSING(data) {
    // Redireciona para novo render
    this.render_AWAITING_PAYMENT(data);
  },

  /**
   * TELA: PAYMENT_DENIED
   */
  render_PAYMENT_DENIED(data) {
    const deniedSeconds = 3;
    const html = `
      <div class="screen">
        <div class="screen-content">
          <div class="denied-container">
            <div class="denied-icon">❌</div>
            <h2 class="denied-message">Pagamento Não Aprovado</h2>
            <p class="denied-details">
              ${data.reason || 'Tente outro método de pagamento'}
            </p>
            <p class="texto-secundario mt-16">
              Voltando ao menu inicial em ${deniedSeconds} segundos...
            </p>
          </div>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
  },

  /**
   * TELA: AUTHORIZED (transição rápida antes do DISPENSING)
   */
  render_AUTHORIZED(data) {
    const beverage = data.beverage || {};
    const emoji = this.getBeverageEmoji(beverage.id);

    const html = `
      <div class="screen">
        <div class="screen-content texto-centro">
          <div class="emoji-grande">✅</div>
          <h2 class="screen-title">Pagamento Aprovado!</h2>
          <div class="spinner mt-30"></div>
          <p class="screen-subtitle">Iniciando ${beverage.name || 'bebida'}...</p>
          <div class="emoji-gigante mt-20">${emoji}</div>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
  },

  /**
   * TELA: DISPENSING (CRÍTICA!)
   */
  render_DISPENSING(data) {
    const volume = data.volume || 0;
    const beverage = data.beverage || {};
    const emoji = this.getBeverageEmoji(beverage.id);

    const html = `
      <div class="screen" style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
        <div class="screen-content">
          <div class="dispensing-container">
            <div class="dispensing-icon-container">
              <div class="dispensing-drink">${emoji}</div>
              <div class="dispensing-pulse"></div>
            </div>

            <h2 class="dispensing-title">Servindo ${beverage.name}</h2>
            <p class="dispensing-subtitle">${volume}ml - Aguarde enquanto preparamos</p>

            <!-- Informação de ML -->
            <div id="dispensing-ml" class="dispensing-ml-display">
              <div class="ml-counter">
                <span id="ml-served" class="ml-served-number">0</span>
                <span class="ml-separator">/</span>
                <span class="ml-total-number">${volume}</span>
                <span class="ml-unit">ml</span>
              </div>
            </div>

            <!-- Barra de Progresso -->
            <div class="barra-container">
              <div id="dispensing-barra" class="barra-fill" style="width: 0%;"></div>
            </div>

            <!-- Percentual Grande -->
            <div class="percentage-display">
              <span id="dispensing-percentage" class="percentage-number">0</span>
              <span class="percentage-symbol">%</span>
            </div>

            <!-- Status -->
            <div id="dispensing-status" class="dispensing-status">
              <span class="status-icon">⚙️</span>
              <span class="status-text">Iniciando extração...</span>
            </div>
          </div>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
  },

  /**
   * TELA: FINISHED
   */
  render_FINISHED(data) {
    const volume = data.ml_served || data.volume || 0;
    const beverage = data.beverage || {};
    const emoji = this.getBeverageEmoji(beverage.id);
    const finishedSeconds = Math.floor((this.config.ui?.finished_timeout_ms || 5000) / 1000);

    const html = `
      <div class="screen">
        <div class="screen-content">
          <div class="finished-container">
            <div class="finished-icon">✅</div>
            <h2 class="finished-message">Pronto! Aproveite!</h2>
            
            <div class="finished-details">
              <strong>${beverage.name}</strong><br>
              <strong>${volume}ml</strong>
            </div>

            <div class="emoji-gigante mt-30">
              ${emoji}
            </div>

            <p class="finished-footer">
              Voltando ao menu em ${finishedSeconds} segundos...
            </p>
          </div>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
  },

  /**
   * Atualiza progresso durante DISPENSING
   */
  updateDispensingProgress(status) {
    if (!window.StateMachineInstance || window.StateMachineInstance.getState() !== 'DISPENSING') {
      return;
    }

    // Extrai dados da estrutura do EDGE
    const dispenserData = status.dispenser || status || {};
    const stateData = window.StateMachineInstance.getData() || {};
    const volumeAuthorized = stateData.volume
      || dispenserData.ml_authorized
      || dispenserData.volume_authorized_ml
      || stateData.ml_authorized
      || 500;
    
    const ml_served = dispenserData.volume_dispensed_ml
      || dispenserData.ml_served
      || 0;
    const percentage = dispenserData.percentage != null
      ? dispenserData.percentage
      : (volumeAuthorized > 0 
        ? Math.round((ml_served / volumeAuthorized) * 100)
        : 0);

    const barra = document.getElementById('dispensing-barra');
    const mlServed = document.getElementById('ml-served');
    const percentageSpan = document.getElementById('dispensing-percentage');
    const statusText = document.querySelector('.status-text');

    if (barra) {
      barra.style.width = Math.min(percentage, 100) + '%';
    }
    
    if (mlServed) {
      mlServed.textContent = Math.round(ml_served);
    }
    
    if (percentageSpan) {
      percentageSpan.textContent = Math.min(percentage, 100);
    }

    // Atualiza mensagem de status baseado no progresso
    if (statusText) {
      if (percentage < 25) {
        statusText.innerHTML = '<span class="status-icon">🔄</span> Iniciando extração...';
      } else if (percentage < 50) {
        statusText.innerHTML = '<span class="status-icon">💧</span> Servindo bebida...';
      } else if (percentage < 75) {
        statusText.innerHTML = '<span class="status-icon">✨</span> Quase lá...';
      } else if (percentage < 100) {
        statusText.innerHTML = '<span class="status-icon">🎯</span> Finalizando...';
      } else {
        statusText.innerHTML = '<span class="status-icon">✅</span> Concluído!';
      }
    }

    this.log('Progress atualizado:', percentage + '%', Math.round(ml_served) + 'ml');
  },

  /**
   * Renderiza erro genérico
   */
  renderNotFound(state) {
    const html = `
      <div class="screen">
        <div class="screen-content" style="text-align: center;">
          <h2 class="screen-title">⚠️ Erro</h2>
          <p>State não encontrado: ${state}</p>
          <button class="botao botao-primary" onclick="location.reload()">
            Recarregar
          </button>
        </div>
      </div>
    `;
    this.appContainer.innerHTML = html;
  },

  /**
   * Mostra modal de erro
   */
  showError(message) {
    const html = `
      <div class="popup-overlay" onclick="this.parentElement.remove()">
        <div class="popup-content" onclick="event.stopPropagation()">
          <div class="emoji-grande">⚠️</div>
          <h3 class="popup-title">Erro</h3>
          <p class="popup-message">${message}</p>
          <div class="popup-buttons">
            <button class="botao botao-error botao-block" onclick="this.closest('.popup-overlay').parentElement.remove(); location.reload();">
              OK
            </button>
          </div>
        </div>
      </div>
    `;

    const overlay = document.createElement('div');
    overlay.innerHTML = html;
    document.body.appendChild(overlay);
    
    // Auto-remover após 10 segundos
    setTimeout(() => {
      if (overlay.parentElement) {
        overlay.remove();
      }
    }, 10000);
  },

  /**
   * Log interno
   */
  log(...args) {
    if (window.APP && window.APP.debug) {
      console.log('[UI]', ...args);
    }
  }
};

// Exportar para uso global
window.UI = UI;
