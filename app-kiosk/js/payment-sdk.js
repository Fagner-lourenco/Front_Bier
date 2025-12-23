/**
 * payment-sdk.js
 * Integração com Mercado Pago via EDGE local
 * Suporta: PIX, Débito, Crédito, QR Code
 * 
 * @version 2.1.0 - Multi-payment Integration
 * @date 2025-12-23
 */

const PaymentSDK = {
  // Configurações
  config: {
    edge_payments_url: 'http://localhost:5000/edge/payments',
    payment_types: ['PIX', 'DEBIT', 'CREDIT', 'QR'],  // Tipos disponíveis
    polling_interval_ms: 1000,
    pix_timeout_ms: 300000,     // 5 min para PIX
    debit_timeout_ms: 120000,   // 2 min para débito
    credit_timeout_ms: 120000,  // 2 min para crédito
    qr_timeout_ms: 300000,      // 5 min para QR
    retry_attempts: 3
  },

  // Estado atual da transação
  currentTransaction: null,
  currentPaymentId: null,
  
  // Callback para atualização de status
  onStatusChange: null,

  /**
   * Inicializa o SDK com configurações
   * @param {Object} sdkConfig - Configurações do SDK
   */
  init(sdkConfig) {
    this.config = { ...this.config, ...sdkConfig };
    console.log('[PaymentSDK] Inicializado com Mercado Pago (EDGE local)');
    console.log('[PaymentSDK] Tipos disponíveis:', this.config.payment_types.join(', '));
    console.log('[PaymentSDK] Payments URL:', this.config.edge_payments_url);
  },

  /**
   * Inicia uma transação de pagamento
   * @param {Object} options - Opções da transação
   * @param {number} options.amount - Valor em BRL (ex: 12.50)
   * @param {string} options.paymentType - 'PIX' | 'DEBIT' | 'CREDIT' | 'QR'
   * @param {number} options.volume_ml - Volume em ml
   * @param {string} options.beverage_id - ID da bebida
   * @param {number} options.installments - Parcelamento (apenas CREDIT)
   * @returns {Promise<Object>} Resultado da transação
   */
  async startTransaction(options) {
    const { amount, paymentType, volume_ml, beverage_id, installments = 1 } = options;

    console.log(`[PaymentSDK] Iniciando transação: ${paymentType} - R$ ${amount.toFixed(2)}`);

    this.currentTransaction = {
      id: this._generateTransactionId(),
      amount,
      paymentType,
      volume_ml,
      beverage_id,
      installments,
      status: 'PENDING',
      startedAt: new Date().toISOString()
    };

    try {
      // Inicia pagamento no EDGE
      const paymentResult = await this._startPayment(paymentType, amount, volume_ml, beverage_id, installments);

      if (!paymentResult.success) {
        this._emitStatus('ERROR', { error: paymentResult.error });
        return {
          status: 'ERROR',
          error: paymentResult.error,
          transactionId: this.currentTransaction.id
        };
      }

      this.currentPaymentId = paymentResult.payment_id;
      const expiresAt = new Date(paymentResult.expires_at);

      // Renderiza QR Code baseado no tipo de pagamento
      if (paymentType === 'PIX') {
        this._emitStatus('PIX_GENERATED', {
          qrCode: paymentResult.qr_code,
          qrCodeBase64: paymentResult.qr_base64,
          expiresAt: paymentResult.expires_at
        });
      } else if (paymentType === 'QR') {
        this._emitStatus('QR_GENERATED', {
          qrCode: paymentResult.qr_code,
          qrCodeBase64: paymentResult.qr_base64,
          expiresAt: paymentResult.expires_at
        });
      }

      // Polling para status de aprovação
      const approved = await this._pollPaymentStatus(
        paymentResult.payment_id,
        paymentType,
        expiresAt
      );

      if (!approved) {
        this._emitStatus('DENIED');
        return {
          status: 'DENIED',
          transactionId: this.currentTransaction.id,
          reason: 'Pagamento não aprovado ou expirado'
        };
      }

      this._emitStatus('APPROVED');

      return {
        status: 'APPROVED',
        transactionId: this.currentTransaction.id,
        paymentId: paymentResult.payment_id,
        paymentType: paymentType,
        amount: amount,
        pixEndToEnd: paymentResult.pix_e2e_id || undefined,
        nsu: paymentResult.payment_id,  // Usar ID do MP como NSU
        approvedAt: new Date().toISOString()
      };

    } catch (error) {
      console.error('[PaymentSDK] Erro na transação:', error);
      this._emitStatus('ERROR', { error: error.message });

      return {
        status: 'ERROR',
        error: error.message,
        transactionId: this.currentTransaction.id
      };
    }
  },

  /**
   * Inicia pagamento no EDGE
   * @private
   */
  async _startPayment(paymentType, amount, volume_ml, beverage_id, installments = 1) {
    try {
      const response = await fetch(`${this.config.edge_payments_url}/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          amount,
          volume_ml,
          beverage_id,
          payment_type: paymentType,
          external_reference: this.currentTransaction.id,
          installments: installments
        })
      });

      const data = await response.json();

      if (!response.ok || !data.success) {
        throw new Error(data.error || 'Falha ao iniciar pagamento');
      }

      return data;

    } catch (error) {
      console.error('[PaymentSDK] Erro ao iniciar pagamento:', error);
      throw error;
    }
  },

  /**
   * Polling de status do pagamento
   * @private
   */
  async _pollPaymentStatus(paymentId, paymentType, expiresAt) {
    const startTime = Date.now();
    const timeout = paymentType === 'PIX' 
      ? this.config.pix_timeout_ms 
      : this.config.qr_timeout_ms;

    while (true) {
      // Verifica timeout
      const elapsed = Date.now() - startTime;
      if (elapsed > timeout) {
        console.log('[PaymentSDK] Timeout de pagamento');
        this._emitStatus('TIMEOUT');
        return false;
      }

      // Verifica expiração do QR Code
      if (expiresAt && Date.now() > expiresAt) {
        console.log('[PaymentSDK] QR Code expirado');
        this._emitStatus('EXPIRED');
        return false;
      }

      try {
        // Consulta status no EDGE
        const statusUrl = paymentType === 'QR'
          ? `${this.config.edge_payments_url}/order/status/${paymentId}`
          : `${this.config.edge_payments_url}/status/${paymentId}`;

        const response = await fetch(statusUrl, {
          method: 'GET',
          headers: {
            'Accept': 'application/json'
          }
        });

        const data = await response.json();

        if (response.ok && data.success) {
          const status = data.status || data.approved;

          console.log(`[PaymentSDK] Status: ${status}`);

          // Se aprovado, retorna true
          if (data.approved || status === 'approved') {
            // Armazenar dados da aprovação para posterior uso
            this.currentTransaction.approvalData = data;
            return true;
          }

          // Se rejeitado ou cancelado
          if (status === 'rejected' || status === 'cancelled') {
            console.log('[PaymentSDK] Pagamento rejeitado');
            return false;
          }

          // Se ainda pending, continua polling
        }

      } catch (error) {
        console.warn('[PaymentSDK] Erro ao consultar status:', error.message);
        // Continua polling mesmo em erro (timeout se falhar muitas vezes)
      }

      // Aguarda antes do próximo polling
      await this._sleep(this.config.polling_interval_ms);
    }
  },

  /**
   * Emite evento de status para listeners
   * @private
   */
  _emitStatus(status, detail = {}) {
    console.log(`[PaymentSDK] Status: ${status}`, detail);

    if (this.onStatusChange) {
      this.onStatusChange(status, detail);
    }

    // Emite evento global
    const event = new CustomEvent('paymentStatusChange', {
      detail: {
        status,
        ...detail,
        transactionId: this.currentTransaction?.id
      }
    });
    document.dispatchEvent(event);
  },

  /**
   * Cancela pagamento em andamento
   */
  async cancelPayment() {
    if (!this.currentPaymentId) {
      console.warn('[PaymentSDK] Nenhum pagamento em andamento para cancelar');
      return false;
    }

    try {
      console.log('[PaymentSDK] Cancelando pagamento:', this.currentPaymentId);
      this._emitStatus('CANCELLED');
      return true;
    } catch (error) {
      console.error('[PaymentSDK] Erro ao cancelar:', error);
      return false;
    }
  },

  /**
   * Gera ID único para transação
   * @private
   */
  _generateTransactionId() {
    return `TXN_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  },

  /**
   * Sleep helper
   * @private
   */
  _sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
};

// Exportar para uso global (const/let não vinculam automaticamente ao window)
if (typeof window !== 'undefined') {
  window.PaymentSDK = PaymentSDK;
}
