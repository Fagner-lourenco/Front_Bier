/**
 * payment-sdk.js
 * Interface unificada para integração com maquininhas de cartão
 * Suporta: Stone, Cielo, PagSeguro, Mock (desenvolvimento)
 * 
 * @version 1.0.0
 * @date 2025-12-22
 */

const PaymentSDK = {
  // Provider atual: 'mock', 'stone', 'cielo', 'pagseguro'
  provider: 'mock',
  
  // Configurações
  config: {
    timeout_ms: 120000,      // 2 min para cartão
    pix_timeout_ms: 300000,  // 5 min para PIX
    device_id: null,
    connection: 'usb'        // 'usb', 'bluetooth', 'wifi'
  },
  
  // Estado atual da transação
  currentTransaction: null,
  
  // Callback para atualização de status
  onStatusChange: null,
  
  /**
   * Inicializa o SDK com configurações
   * @param {Object} sdkConfig - Configurações do SDK
   */
  init(sdkConfig) {
    this.provider = sdkConfig.provider || 'mock';
    this.config = { ...this.config, ...sdkConfig };
    
    console.log(`[PaymentSDK] Inicializado com provider: ${this.provider}`);
    
    // Inicializa provider específico se não for mock
    if (this.provider !== 'mock') {
      this._initProvider();
    }
  },
  
  /**
   * Inicializa provider específico (Stone, Cielo, etc)
   * @private
   */
  _initProvider() {
    switch (this.provider) {
      case 'stone':
        // TODO: Inicializar Stone SDK
        console.log('[PaymentSDK] Stone SDK - implementar quando disponível');
        break;
      case 'cielo':
        // TODO: Inicializar Cielo LIO SDK
        console.log('[PaymentSDK] Cielo SDK - implementar quando disponível');
        break;
      case 'pagseguro':
        // TODO: Inicializar PagSeguro PlugPag
        console.log('[PaymentSDK] PagSeguro SDK - implementar quando disponível');
        break;
    }
  },
  
  /**
   * Inicia uma transação de pagamento
   * @param {Object} options - Opções da transação
   * @param {number} options.amount - Valor em centavos (ex: 1200 = R$ 12,00)
   * @param {string} options.paymentType - 'PIX', 'CREDIT', 'DEBIT'
   * @param {number} [options.installments=1] - Número de parcelas (apenas crédito)
   * @returns {Promise<Object>} Resultado da transação
   */
  async startTransaction(options) {
    const { amount, paymentType, installments = 1 } = options;
    
    console.log(`[PaymentSDK] Iniciando transação: ${paymentType} - R$ ${(amount / 100).toFixed(2)}`);
    
    // Cria objeto da transação
    this.currentTransaction = {
      id: this._generateTransactionId(),
      amount,
      paymentType,
      installments,
      status: 'PENDING',
      startedAt: new Date().toISOString()
    };
    
    // Emite evento de status inicial (específico por tipo)
    if (paymentType === 'PIX') {
      this._emitStatus('GENERATING_PIX');
    } else {
      this._emitStatus('WAITING_CARD');
    }
    
    try {
      let result;
      
      if (this.provider === 'mock') {
        result = await this._mockTransaction(options);
      } else {
        result = await this._realTransaction(options);
      }
      
      this.currentTransaction.status = result.status;
      this.currentTransaction.finishedAt = new Date().toISOString();
      
      return result;
      
    } catch (error) {
      console.error('[PaymentSDK] Erro na transação:', error);
      
      return {
        status: 'ERROR',
        error: error.message,
        transactionId: this.currentTransaction.id
      };
    }
  },
  
  /**
   * Transação mock para desenvolvimento
   * @private
   */
  async _mockTransaction(options) {
    const { amount, paymentType } = options;
    
    // Se for PIX, gera QR Code
    if (paymentType === 'PIX') {
      return await this._mockPixTransaction(amount);
    }
    
    // Cartão: simula delay de inserir cartão
    this._emitStatus('WAITING_CARD');
    await this._sleep(2000);
    
    // Simula processamento
    this._emitStatus('PROCESSING');
    await this._sleep(1500);
    
    // 90% aprovado, 10% negado (para testes)
    const approved = Math.random() > 0.1;
    
    if (approved) {
      this._emitStatus('APPROVED');
      
      return {
        status: 'APPROVED',
        transactionId: this.currentTransaction.id,
        nsu: this._generateNSU(),
        authCode: this._generateAuthCode(),
        cardBrand: this._randomCardBrand(),
        lastDigits: this._randomLastDigits(),
        paymentType: paymentType
      };
    } else {
      this._emitStatus('DENIED');
      
      return {
        status: 'DENIED',
        transactionId: this.currentTransaction.id,
        reason: 'Cartão recusado pela operadora',
        errorCode: 'INSUFFICIENT_FUNDS'
      };
    }
  },
  
  /**
   * Transação PIX mock
   * @private
   */
  async _mockPixTransaction(amount) {
    // Gera QR Code fake (em produção seria da maquininha/gateway)
    const pixPayload = this._generatePixPayload(amount);
    
    this._emitStatus('PIX_GENERATED', {
      qrCode: pixPayload.qrCode,
      qrCodeBase64: pixPayload.qrCodeBase64,
      expiresAt: pixPayload.expiresAt
    });
    
    // Simula cliente escaneando e pagando (3-8 segundos)
    const waitTime = 3000 + Math.random() * 5000;
    await this._sleep(waitTime);
    
    // 95% aprovado para PIX (menos falhas)
    const approved = Math.random() > 0.05;
    
    if (approved) {
      this._emitStatus('APPROVED');
      
      return {
        status: 'APPROVED',
        transactionId: this.currentTransaction.id,
        nsu: this._generateNSU(),
        paymentType: 'PIX',
        pixEndToEnd: this._generatePixE2E()
      };
    } else {
      this._emitStatus('DENIED');
      
      return {
        status: 'DENIED',
        transactionId: this.currentTransaction.id,
        reason: 'PIX expirado ou cancelado',
        errorCode: 'PIX_EXPIRED'
      };
    }
  },
  
  /**
   * Transação real com provider
   * @private
   */
  async _realTransaction(options) {
    // TODO: Implementar para cada provider
    switch (this.provider) {
      case 'stone':
        return await this._stoneTransaction(options);
      case 'cielo':
        return await this._cieloTransaction(options);
      case 'pagseguro':
        return await this._pagseguroTransaction(options);
      default:
        throw new Error(`Provider não suportado: ${this.provider}`);
    }
  },
  
  /**
   * Cancela a transação atual
   * @returns {Promise<Object>}
   */
  async cancelTransaction() {
    if (!this.currentTransaction) {
      return { status: 'NO_TRANSACTION' };
    }
    
    console.log(`[PaymentSDK] Cancelando transação: ${this.currentTransaction.id}`);
    
    this._emitStatus('CANCELLED');
    
    const transactionId = this.currentTransaction.id;
    this.currentTransaction = null;
    
    return {
      status: 'CANCELLED',
      transactionId
    };
  },
  
  /**
   * Consulta status de uma transação
   * @param {string} transactionId
   * @returns {Promise<Object>}
   */
  async getTransactionStatus(transactionId) {
    if (this.currentTransaction && this.currentTransaction.id === transactionId) {
      return {
        status: this.currentTransaction.status,
        transactionId
      };
    }
    
    return {
      status: 'NOT_FOUND',
      transactionId
    };
  },
  
  /**
   * Gera payload PIX mock
   * @private
   */
  _generatePixPayload(amount) {
    const txId = this._generateTransactionId();
    
    // Payload EMV simplificado (em produção viria da maquininha)
    const emvPayload = `00020126580014br.gov.bcb.pix0136${txId}520400005303986540${(amount/100).toFixed(2)}5802BR5913BIERPASS6008SAOPAULO62070503***6304`;
    
    return {
      qrCode: emvPayload,
      // Base64 de um QR Code placeholder (em produção seria gerado dinamicamente)
      qrCodeBase64: this._generateQRCodePlaceholder(),
      expiresAt: new Date(Date.now() + this.config.pix_timeout_ms).toISOString(),
      txId
    };
  },
  
  /**
   * Gera placeholder de QR Code (SVG base64)
   * @private
   */
  _generateQRCodePlaceholder() {
    // SVG simples representando QR Code (em produção usar biblioteca real)
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">
      <rect fill="#fff" width="200" height="200"/>
      <rect fill="#000" x="20" y="20" width="60" height="60"/>
      <rect fill="#fff" x="30" y="30" width="40" height="40"/>
      <rect fill="#000" x="40" y="40" width="20" height="20"/>
      <rect fill="#000" x="120" y="20" width="60" height="60"/>
      <rect fill="#fff" x="130" y="30" width="40" height="40"/>
      <rect fill="#000" x="140" y="40" width="20" height="20"/>
      <rect fill="#000" x="20" y="120" width="60" height="60"/>
      <rect fill="#fff" x="30" y="130" width="40" height="40"/>
      <rect fill="#000" x="40" y="140" width="20" height="20"/>
      <text x="100" y="105" text-anchor="middle" font-size="12" fill="#000">PIX MOCK</text>
    </svg>`;
    
    return 'data:image/svg+xml;base64,' + btoa(svg);
  },
  
  /**
   * Emite evento de mudança de status
   * @private
   */
  _emitStatus(status, data = {}) {
    console.log(`[PaymentSDK] Status: ${status}`, data);
    
    if (this.onStatusChange) {
      this.onStatusChange(status, data);
    }
    
    // Dispara evento customizado
    window.dispatchEvent(new CustomEvent('paymentStatus', {
      detail: { status, ...data }
    }));
  },
  
  // Helpers
  _generateTransactionId() {
    return 'TXN_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6).toUpperCase();
  },
  
  _generateNSU() {
    return Math.floor(Math.random() * 900000000 + 100000000).toString();
  },
  
  _generateAuthCode() {
    return Math.random().toString(36).substr(2, 6).toUpperCase();
  },
  
  _generatePixE2E() {
    return 'E' + Math.random().toString(36).substr(2, 32).toUpperCase();
  },
  
  _randomCardBrand() {
    const brands = ['VISA', 'MASTERCARD', 'ELO', 'AMEX', 'HIPERCARD'];
    return brands[Math.floor(Math.random() * brands.length)];
  },
  
  _randomLastDigits() {
    return Math.floor(Math.random() * 9000 + 1000).toString();
  },
  
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },
  
  // Placeholders para providers reais
  async _stoneTransaction(options) {
    // TODO: Implementar Stone SDK
    throw new Error('Stone SDK não implementado. Use provider: "mock" para desenvolvimento.');
  },
  
  async _cieloTransaction(options) {
    // TODO: Implementar Cielo LIO SDK
    throw new Error('Cielo SDK não implementado. Use provider: "mock" para desenvolvimento.');
  },
  
  async _pagseguroTransaction(options) {
    // TODO: Implementar PagSeguro PlugPag
    throw new Error('PagSeguro SDK não implementado. Use provider: "mock" para desenvolvimento.');
  }
};

// Exporta para uso global
window.PaymentSDK = PaymentSDK;
