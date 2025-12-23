/**
 * MAIN.JS
 * Entry point e controllers
 */

// Configuração global do app
window.APP = {
  debug: false,
  version: '1.1.0',
  machineId: 'M001'
};

// Referência global da state machine
let StateMachineInstance = null;
let AppConfig = null;

/**
 * Inicializa a aplicação
 */
async function initApp() {
  try {
    console.log('%c🍺 BierPass Kiosk', 'font-size: 24px; font-weight: bold; color: #FF6B35;');
    console.log('Versão:', window.APP.version);

    // 1. Carrega configuração
    console.log('[1/10] Detectando caminho...');
    const basePath = window.location.pathname.includes('app-kiosk') 
      ? window.location.pathname.substring(0, window.location.pathname.indexOf('app-kiosk') + 9)
      : '/app-kiosk';
    console.log('  ✓ basePath:', basePath);
    
    console.log('[2/10] Carregando config.json...');
    const configResponse = await fetch(basePath + '/config.json');
    console.log('  ✓ Response status:', configResponse.status);
    
    if (!configResponse.ok) {
      throw new Error(`Erro ao carregar config.json: ${configResponse.status} ${configResponse.statusText}`);
    }
    AppConfig = await configResponse.json();
    window.APP.config = AppConfig;
    window.APP.basePath = basePath;
    // Usa flag de debug do config (fallback para true padrão)
    window.APP.debug = AppConfig.debug !== undefined ? !!AppConfig.debug : window.APP.debug;
    // Ativa hook de console apenas se debug habilitado
    setupDebugConsoleHook();
    console.log('  ✓ Config carregado:', AppConfig);

    // 2. Inicializa módulos
    console.log('[3/10] Inicializando MockAPIs...');
    try {
      if (AppConfig.api && AppConfig.api.use_mock && typeof MockAPIs !== 'undefined') {
        MockAPIs.init();
        console.log('  ✓ MockAPIs OK');
      } else {
        console.log('  ✓ MockAPIs desativado');
      }
    } catch (e) {
      console.warn('  ⚠️ MockAPIs não disponível, seguindo sem mock');
    }

    console.log('[4/10] Inicializando API...');
    try {
      API.init(AppConfig);
      console.log('  ✓ API OK');
    } catch (e) {
      console.error('  ✗ Erro API:', e);
      throw e;
    }

    console.log('[5/10] Inicializando PaymentSDK...');
    try {
      // Garante referência no window (const não se auto-anexa no browser)
      if (!window.PaymentSDK && typeof PaymentSDK !== 'undefined') {
        window.PaymentSDK = PaymentSDK;
      }
      const sdk = window.PaymentSDK;
      if (!sdk) throw new Error('PaymentSDK não disponível no window');

      sdk.init(AppConfig.payment_sdk);
      console.log('  ✓ PaymentSDK OK');
    } catch (e) {
      console.error('  ✗ Erro PaymentSDK:', e);
      throw e;
    }

    console.log('[6/10] Inicializando Polling...');
    try {
      Polling.init(AppConfig);
      console.log('  ✓ Polling OK');
    } catch (e) {
      console.error('  ✗ Erro Polling:', e);
      throw e;
    }

    console.log('[7/10] Inicializando UI...');
    try {
      UI.init(AppConfig);
      console.log('  ✓ UI OK');
    } catch (e) {
      console.error('  ✗ Erro UI:', e);
      throw e;
    }

    // 3. Cria state machine
    console.log('[8/10] Criando StateMachine...');
    StateMachineInstance = new StateMachine(AppConfig);
    window.StateMachineInstance = StateMachineInstance;
    console.log('  ✓ StateMachine criada');

    // 4. Registra listeners
    console.log('[9/10] Registrando listeners...');
    registerStateListeners();
    registerEventListeners();
    console.log('  ✓ Listeners registrados');

    // 5. Carrega dados iniciais
    console.log('[10/10] Carregando dados iniciais...');
    await loadInitialData();
    console.log('  ✓ Dados carregados');

    // 6. Verifica transações pendentes (recovery)
    await checkPendingTransactions();

    // 7. Inicia em BOOT
    console.log('[11/11] Iniciando em BOOT...');
    StateMachineInstance.setState('BOOT');
    UI.render('BOOT');

    console.log('%c🚀 Aplicação inicializada com sucesso!', 'font-size: 18px; color: #28A745; font-weight: bold;');
  } catch (error) {
    console.error('%c❌ ERRO CRÍTICO', 'font-size: 16px; color: #DC3545; font-weight: bold;');
    console.error('Erro:', error);
    console.error('Stack:', error.stack);
    document.getElementById('app').innerHTML = `
      <div style="padding: 40px; text-align: center; background: #fff; border: 3px solid #DC3545; color: #DC3545;">
        <h2>⚠️ Erro ao inicializar</h2>
        <p><strong>${error.message}</strong></p>
        <p style="font-size: 12px; margin-top: 20px; color: #888;">Abra o Console (F12) para ver detalhes</p>
      </div>
    `;
  }
}

/**
 * Carrega dados iniciais (cardápio)
 */
async function loadInitialData() {
  try {
    let result;

    if (AppConfig.api.use_mock) {
      result = await MockAPIs.getBeverages();
    } else {
      result = await API.getBeverages();
    }

    if (!result.ok) {
      throw new Error('Erro ao carregar beverages: ' + result.error);
    }

    window.APP.beverages = result.data.beverages;
    console.log('[App] Beverages carregados:', window.APP.beverages);
  } catch (error) {
    console.error('[App] Erro ao carregar dados iniciais:', error);
    throw error;
  }
}

/**
 * Verifica e reenvia transações pendentes (recovery)
 */
async function checkPendingTransactions() {
  try {
    const lastTransaction = Storage.getLastTransaction();
    
    if (!lastTransaction) {
      console.log('[Recovery] Nenhuma transação pendente');
      return;
    }
    
    // Se transação não foi sincronizada, tenta reenviar
    if (lastTransaction.synced === false) {
      console.log('[Recovery] Reenviando transação pendente:', lastTransaction);
      
      let result;
      // Arredondar ml_served para inteiro (API espera integer, não float)
      const mlServed = Math.round(lastTransaction.ml_served);
      const mlAuthorized = Math.round(lastTransaction.ml_authorized || lastTransaction.ml_served);
      
      if (AppConfig.api.use_mock) {
        result = await MockAPIs.reportConsume(
          lastTransaction.token,
          AppConfig.machine.id,
          mlServed,
          mlAuthorized,
          lastTransaction.sale_id || null,
          'OK',
          lastTransaction.startedAt || lastTransaction.finishedAt,
          lastTransaction.finishedAt
        );
      } else {
        result = await API.reportConsume(
          lastTransaction.token,
          AppConfig.machine.id,
          mlServed,
          mlAuthorized,
          lastTransaction.sale_id || null,
          'OK',
          lastTransaction.startedAt || lastTransaction.finishedAt,
          lastTransaction.finishedAt
        );
      }
      
      if (result.ok) {
        console.log('[Recovery] Transação reenviada com sucesso!');
        // Remove transação após sucesso para não reenviá-la novamente
        Storage.remove('last_transaction');
      } else {
        console.warn('[Recovery] Falha ao reenviar (será tentado novamente):', result.error);
      }
    }
    
    // Verifica token não utilizado (caso refresh durante AUTHORIZED/DISPENSING)
    const savedToken = Storage.getToken();
    if (savedToken) {
      console.log('[Recovery] Token encontrado, verificando status no EDGE...');
      // TODO: Verificar status do token no EDGE para recovery mid-dispense
      // const edgeStatus = await API.getEdgeStatus();
      // if (edgeStatus.data?.state === 'DISPENSING') { ... }
    }
    
  } catch (error) {
    console.warn('[Recovery] Erro ao verificar pendências:', error);
    // Não interrompe inicialização
  }
}

/**
 * Registra listeners de state change
 */
function registerStateListeners() {
  // Escuta o evento emitido pela StateMachine
  StateMachineInstance.on('state:change', async (event) => {
    console.log('[App] State mudou:', event.from, '→', event.to);
  });
}

/**
 * Registra event listeners do DOM
 */
function registerEventListeners() {
  // Dispensing status updates
  document.addEventListener('dispensingStatus', (event) => {
    const status = event.detail || {};
    const dispenser = status.dispenser || status;
    const dispStatus = (dispenser.status || status.state || '').toString().toUpperCase();

    // Quando concluir (COMPLETED/FINISHED), reporta consumo e garante transição para FINISHED
    if (dispStatus === 'COMPLETED' || dispStatus === 'FINISHED') {
      const stateData = StateMachineInstance.getStateData();
      const mlServed = dispenser.volume_dispensed_ml || dispenser.ml_served || 0;
      const mlAuthorized = stateData.volume || dispenser.ml_authorized || dispenser.volume_authorized_ml;

      // Reporta consumo ao SaaS (background)
      reportConsumeToSaaS(stateData, {
        ml_served: mlServed,
        ml_authorized: mlAuthorized,
        state: dispStatus
      }).catch(err => {
        console.warn('[App] Erro ao reportar consumo (será reenviado):', err);
      });

      // Garante estado FINISHED com os dados corretos
      StateMachineInstance.setState('FINISHED', {
        ...stateData,
        ml_served: mlServed,
        ml_authorized: mlAuthorized
      });
    }
  });

  // Dispensing errors
  document.addEventListener('dispensingError', (event) => {
    console.error('[App] Dispensing error:', event.detail.error);
    StateMachineInstance.setState('IDLE');
  });

  // Teclado ESC para debug
  if (window.APP.debug) {
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape') {
        toggleDebugPanel();
      }
    });
  }
}

/**
 * Reporta consumo ao SaaS após extração
 */
async function reportConsumeToSaaS(stateData, status) {
  try {
    const token = Storage.getToken();
    const startedAt = stateData.dispensingStartedAt || new Date().toISOString();
    const finishedAt = new Date().toISOString();
    const mlAuthorized = Math.round(stateData.volume || status.ml_authorized || 0);
    const mlServed = Math.round(status.ml_served || 0);
    const saleId = window.APP.lastSaleId || null;
    
    let result;
    if (AppConfig.api.use_mock) {
      result = await MockAPIs.reportConsume(
        token,
        AppConfig.machine.id,
        mlServed,
        mlAuthorized,
        saleId,
        'OK',
        startedAt,
        finishedAt
      );
    } else {
      result = await API.reportConsume(
        token,
        AppConfig.machine.id,
        mlServed,
        mlAuthorized,
        saleId,
        'OK',
        startedAt,
        finishedAt
      );
    }
    
    if (result.ok) {
      console.log('[App] Consumo reportado com sucesso');
      // Remove transação do storage para evitar acúmulo e reenvio desnecessário
      Storage.remove('last_transaction');
      // Limpa sale_id após consumo registrado
      window.APP.lastSaleId = null;
    } else {
      // Salva para retry posterior
      Storage.saveTransaction({
        token: token,
        ml_served: status.ml_served,
        ml_authorized: mlAuthorized,
        sale_id: saleId,
        beverage: stateData.beverage,
        finishedAt: finishedAt,
        synced: false,
        error: result.error
      });
      console.warn('[App] Consumo salvo para retry:', result.error);
    }
  } catch (error) {
    console.error('[App] Erro crítico ao reportar consumo:', error);
  }
}

/**
 * HANDLER: Seleciona bebida
 */
async function handleBeverageSelect(beverageId) {
  console.log('[Handler] Beverage selecionado:', beverageId);

  const beverage = window.APP.beverages.find(b => b.id === beverageId);
  if (!beverage) {
    console.error('Bebida não encontrada:', beverageId);
    return;
  }

  // NOVO: Verifica se tem álcool ANTES de escolher volume
  if (beverage.abv > 0) {
    // Bebida alcoólica: vai para CONFIRM_AGE primeiro
    StateMachineInstance.setState('CONFIRM_AGE', {
      beverage: beverage,
      step: 2
    });
  } else {
    // Sem álcool: vai direto para escolher volume
    StateMachineInstance.setState('SELECT_VOLUME', {
      beverage: beverage,
      step: 2
    });
  }
}

/**
 * HANDLER: Seleção visual de volume com delay
 */
function selectVolume(element, volumeMl) {
  // Remove seleção anterior
  document.querySelectorAll('.botao-volume').forEach(btn => 
    btn.classList.remove('selected')
  );
  // Marca como selecionado
  element.classList.add('selected');
  // Delay visual antes de avançar
  setTimeout(() => handleVolumeSelect(volumeMl), 400);
}

/**
 * HANDLER: Seleção visual de pagamento com delay
 */
function selectPayment(element, method) {
  // Remove seleção anterior
  document.querySelectorAll('.botao-payment').forEach(btn => 
    btn.classList.remove('selected')
  );
  // Marca como selecionado
  element.classList.add('selected');
  // Delay visual antes de avançar
  setTimeout(() => handlePaymentSelect(method), 400);
}

/**
 * HANDLER: Seleciona volume
 */
function handleVolumeSelect(volumeMl) {
  console.log('[Handler] Volume selecionado:', volumeMl);

  const stateData = StateMachineInstance.getStateData();
  
  // Para bebidas alcoólicas que já passaram por CONFIRM_AGE
  const currentStep = stateData.beverage.abv > 0 ? 4 : 3;

  // Vai para SELECT_PAYMENT
  StateMachineInstance.setState('SELECT_PAYMENT', {
    beverage: stateData.beverage,
    volume: volumeMl,
    step: currentStep
  });
}

/**
 * HANDLER: Confirma idade
 */
function handleConfirmAge(confirmed) {
  console.log('[Handler] Idade confirmada:', confirmed);

  const stateData = StateMachineInstance.getStateData();

  if (!confirmed) {
    // Volta para IDLE com mensagem
    StateMachineInstance.setState('IDLE', {
      beverages: window.APP.beverages,
      message: 'Por favor, escolha uma bebida sem álcool'
    });
    return;
  }

  // Confirmou idade: vai para SELECT_VOLUME
  StateMachineInstance.setState('SELECT_VOLUME', {
    beverage: stateData.beverage,
    step: 3
  });
}

/**
 * HANDLER: Seleciona método de pagamento
 */
async function handlePaymentSelect(paymentMethod) {
  console.log('[Handler] Pagamento selecionado:', paymentMethod);

  const stateData = StateMachineInstance.getStateData();
  const beverage = stateData.beverage;
  const volume = stateData.volume;
  const total = Validators.calculatePrice(volume, beverage.price_per_ml);

  // Vai para AWAITING_PAYMENT (aguardando maquininha/QR)
  StateMachineInstance.setState('AWAITING_PAYMENT', {
    beverage: beverage,
    volume: volume,
    total: total,
    paymentMethod: paymentMethod
  });

  // Inicia transação com SDK da maquininha
  await processPaymentWithSDK(beverage, volume, paymentMethod, total);
}

/**
 * Processa pagamento com SDK Mercado Pago via EDGE
 */
async function processPaymentWithSDK(beverage, volumeMl, paymentMethod, total) {
  try {
    const sdk = window.PaymentSDK;
    if (!sdk) {
      throw new Error('PaymentSDK não inicializado');
    }

    // Re-inicializa se config ausente (proteção contra race de carregamento)
    if (!sdk.config || !sdk.config.edge_payments_url) {
      sdk.init(AppConfig.payment_sdk || {});
    }
    
    // Configura callback de status
    sdk.onStatusChange = (status, data) => {
      console.log('[Payment] Status:', status, data);
      
      // Atualiza UI se estivermos em AWAITING_PAYMENT
      if (StateMachineInstance.getState() === 'AWAITING_PAYMENT') {
        UI.updatePaymentStatus(status, data);
      }
    };

    // Inicia transação com Mercado Pago via EDGE (valor em BRL)
    const result = await sdk.startTransaction({
      amount: total,
      paymentType: paymentMethod.toUpperCase(),
      volume_ml: volumeMl,
      beverage_id: beverage.id
    });

    console.log('[Payment] Resultado:', result);

    // Verifica resultado
    if (result.status !== 'APPROVED') {
      StateMachineInstance.setState('PAYMENT_DENIED', {
        reason: result.reason || 'Pagamento não aprovado'
      });
      return;
    }

    // === CORREÇÃO CRÍTICA ===
    // 1. PRIMEIRO registra venda no SaaS para obter o sale_id real
    // 2. DEPOIS gera o token com o sale_id correto
    // Isso garante que o consumo seja vinculado à venda correta
    
    let saleId = null;
    try {
      saleId = await registerSaleInSaaS(beverage, volumeMl, total, paymentMethod, result);
      console.log('[App] Venda registrada, sale_id:', saleId);
    } catch (err) {
      console.warn('[App] Erro ao registrar venda no SaaS (continuando com fallback):', err);
      // Fallback: usa transactionId do SDK (não ideal, mas permite operação)
      saleId = result.transactionId;
    }

    // Gera token HMAC para EDGE com o sale_id correto do SaaS
    const tokenData = await generateLocalToken(result, volumeMl, beverage.id, saleId);
    
    // Salva token
    Storage.saveToken(tokenData.token, tokenData.expires_at);

    // Autoriza no EDGE (envia token HMAC completo)
    // EDGE real: operação bloqueante que dispensa e retorna resultado
    // Autoriza com EDGE
    const edgeResult = await authorizeEdge(tokenData.token);

    // Define volume no mock para simulação correta
    if (AppConfig.api.use_mock) {
      MockAPIs.setAuthorizedVolume(volumeMl);
    }

    // Vai para AUTHORIZED (que vai automaticamente para DISPENSING)
    StateMachineInstance.setState('AUTHORIZED', {
      beverage: beverage,
      volume: volumeMl,
      token: tokenData.token,
      expiresAt: tokenData.expires_at,
      paymentResult: result,
      edgeResult: edgeResult // Resultado do EDGE (se não-mock)
    });
    
  } catch (error) {
    console.error('[App] Erro ao processar pagamento:', error);
    StateMachineInstance.setState('PAYMENT_DENIED', {
      reason: 'Erro ao processar pagamento'
    });
  }
}

/**
 * Gera token HMAC para autorização no EDGE
 * Formato: base64(payload).base64(hmac_signature)
 * 
 * O EDGE valida:
 * 1. Assinatura HMAC-SHA256 válida
 * 2. Token não expirado
 * 3. Token não reutilizado (single-use via nonce)
 * 
 * @param {Object} sdkResult - Resultado do SDK de pagamento
 * @param {number} volumeMl - Volume autorizado em ml
 * @param {string} beverageId - ID da bebida
 * @param {string} saleId - ID da venda no SaaS (UUID real)
 * @returns {Promise<Object>} Token data { token, payload, expires_at }
 */
async function generateLocalToken(sdkResult, volumeMl, beverageId, saleId) {
  // Payload no formato esperado pelo EDGE
  const payload = {
    sale_id: saleId, // Usa sale_id real do SaaS, não transactionId do SDK
    beverage_id: beverageId,
    volume_ml: volumeMl,
    tap_id: 1, // TODO: Mapear tap correto baseado na bebida
    timestamp: Date.now() / 1000,
    nonce: generateNonce()
  };
  
  // Codifica payload em JSON minificado
  const payloadJson = JSON.stringify(payload);
  
  // Base64 URL-safe do payload
  const payloadB64 = base64UrlEncode(payloadJson);
  
  // Calcula HMAC-SHA256 real usando Web Crypto API
  const hmacSecret = AppConfig.security?.hmac_secret || 'bierpass_edge_secret_key_2025_change_in_production';
  const signatureB64 = await computeHmacSha256(payloadJson, hmacSecret);
  
  // Token final: payload.signature
  const token = `${payloadB64}.${signatureB64}`;
  
  const expiresAt = new Date(Date.now() + (AppConfig.security?.token_validity_seconds || 90) * 1000).toISOString();
  
  console.log('[Token] Gerado para EDGE:', {
    sale_id: payload.sale_id,
    volume_ml: payload.volume_ml,
    beverage_id: payload.beverage_id,
    expires: expiresAt
  });
  
  return {
    token: token,
    payload: payload,
    expires_at: expiresAt
  };
}

/**
 * Gera nonce único para evitar replay attacks
 */
function generateNonce() {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Base64 URL-safe encoding
 */
function base64UrlEncode(str) {
  const base64 = btoa(unescape(encodeURIComponent(str)));
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/**
 * Base64 URL-safe encoding para ArrayBuffer
 */
function arrayBufferToBase64Url(buffer) {
  const bytes = new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/**
 * Converte string para ArrayBuffer (UTF-8)
 */
function stringToArrayBuffer(str) {
  const encoder = new TextEncoder();
  return encoder.encode(str);
}

/**
 * Computa HMAC-SHA256 real usando Web Crypto API
 * @param {string} message - Mensagem a assinar
 * @param {string} secret - Chave secreta
 * @returns {Promise<string>} Assinatura em base64 URL-safe
 */
async function computeHmacSha256(message, secret) {
  try {
    // Importa a chave secreta
    const keyData = stringToArrayBuffer(secret);
    const key = await crypto.subtle.importKey(
      'raw',
      keyData,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    
    // Assina a mensagem
    const messageData = stringToArrayBuffer(message);
    const signature = await crypto.subtle.sign('HMAC', key, messageData);
    
    // Retorna em base64 URL-safe
    return arrayBufferToBase64Url(signature);
  } catch (error) {
    console.error('[HMAC] Web Crypto não disponível ou falhou:', error);
    throw new Error('HMAC-SHA256 não suportado neste navegador. Use um browser moderno com Web Crypto.');
  }
}

/**
 * Registra venda no SaaS
 * @returns {Promise<string>} sale_id do SaaS (UUID)
 */
async function registerSaleInSaaS(beverage, volumeMl, total, paymentMethod, sdkResult) {
  const saleData = {
    machine_id: AppConfig.machine.id,
    beverage_id: beverage.id,
    volume_ml: volumeMl,
    total_value: total,
    payment_method: paymentMethod,
    payment_transaction_id: sdkResult.transactionId,
    payment_nsu: sdkResult.nsu,
    payment_auth_code: sdkResult.authCode,
    payment_card_brand: sdkResult.cardBrand,
    payment_card_last_digits: sdkResult.cardLastDigits,
    created_at: new Date().toISOString()
  };
  
  let result;
  if (AppConfig.api.use_mock) {
    // Mock: gera sale_id fake
    console.log('[Mock] Venda registrada:', saleData);
    result = { ok: true, data: { sale_id: 'MOCK_SALE_' + Date.now() } };
  } else {
    result = await API.registerSale(saleData);
  }
  
  if (!result.ok) {
    throw new Error(result.error || 'Falha ao registrar venda');
  }
  
  const saleId = result.data.sale_id;
  console.log('[App] Venda registrada no SaaS:', saleId);
  
  // Salva sale_id para referência
  window.APP.lastSaleId = saleId;
  
  return saleId;
}

/**
 * Autoriza token no EDGE
 * Envia token HMAC no formato: base64(payload).base64(signature)
 */
async function authorizeEdge(token) {
  try {
    let result;
    if (AppConfig.api.use_mock) {
      result = await MockAPIs.edgeAuthorize(token);
    } else {
      result = await API.edgeAuthorize(token);
    }

    if (!result.ok) {
      throw new Error('EDGE authorization failed: ' + result.error);
    }

    console.log('[App] EDGE autorizado:', result.data);
    return result.data;
  } catch (error) {
    console.error('[App] Erro ao autorizar EDGE:', error);
    throw error;
  }
}

/**
 * HANDLER: Voltar - navegação inteligente baseada no estado atual
 */
function handleBack() {
  const currentState = StateMachineInstance.getState();
  const stateData = StateMachineInstance.getStateData();
  
  console.log('[Handler] Voltando de:', currentState);

  switch (currentState) {
    case 'SELECT_PAYMENT':
      // Volta para escolha de volume
      StateMachineInstance.setState('SELECT_VOLUME', { 
        beverage: stateData.beverage 
      });
      break;
    case 'SELECT_VOLUME':
      // Se bebida alcoolica, volta para confirmação de idade? Não, volta para IDLE
      StateMachineInstance.setState('IDLE', {
        beverages: window.APP.beverages
      });
      break;
    case 'CONFIRM_AGE':
      // Volta para IDLE
      StateMachineInstance.setState('IDLE', {
        beverages: window.APP.beverages
      });
      break;
    default:
      // Fallback para IDLE
      StateMachineInstance.setState('IDLE', {
        beverages: window.APP.beverages
      });
  }
}

/**
 * HANDLER: Cancela pagamento em andamento
 */
async function cancelPayment() {
  console.log('[Handler] Cancelando pagamento');
  
  // Cancela transação no SDK
  if (window.PaymentSDK && window.PaymentSDK.currentTransaction) {
    await window.PaymentSDK.cancelPayment();
  }
  
  // Volta para IDLE
  StateMachineInstance.setState('IDLE', {
    beverages: window.APP.beverages
  });
}

/**
 * HANDLER: Toggle debug panel
 */
function toggleDebugPanel() {
  const panel = document.getElementById('debug-panel');
  if (panel) {
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
  }
}

/**
 * HANDLER: Log customizado para debug
 */
function debugLog(level, message, data = '') {
  if (!window.APP.debug) return;

  const logPanel = document.getElementById('debug-log');
  if (!logPanel) return;

  const entry = document.createElement('div');
  entry.className = `debug-log-entry ${level}`;
  
  const timestamp = new Date().toLocaleTimeString();
  const text = `[${timestamp}] ${message}${data ? ' ' + JSON.stringify(data) : ''}`;
  
  entry.textContent = text;
  logPanel.appendChild(entry);

  // Scroll para o final
  logPanel.scrollTop = logPanel.scrollHeight;

  // Limita a 100 entradas
  while (logPanel.children.length > 100) {
    logPanel.removeChild(logPanel.firstChild);
  }
}

// Configura override de console apenas quando debug estiver ativo
function setupDebugConsoleHook() {
  if (!window.APP || !window.APP.debug) return;
  if (window.APP.consoleHooked) return;

  const originalLog = console.log;
  const originalError = console.error;

  window.console.log = function(...args) {
    originalLog.apply(console, args);
    if (!window.APP || !window.APP.debug) return;
    try {
      const message = args.map(a => typeof a === 'string' ? a : JSON.stringify(a)).join(' ');
      debugLog('info', message);
    } catch (e) {
      // Ignora erros de serialização
    }
  };

  window.console.error = function(...args) {
    originalError.apply(console, args);
    if (!window.APP || !window.APP.debug) return;
    try {
      const message = args.map(a => typeof a === 'string' ? a : JSON.stringify(a)).join(' ');
      debugLog('error', message);
    } catch (e) {
      // Ignora erros de serialização
    }
  };

  window.APP.consoleHooked = true;
}

/**
 * Inicia aplicação quando DOM estiver pronto
 */
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initApp);
} else {
  // DOM já carregou
  initApp();
}
