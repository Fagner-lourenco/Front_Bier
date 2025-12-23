/**
 * VALIDATORS.JS
 * Validações e funções utilitárias
 */

const Validators = {
  /**
   * Valida se é um token válido
   */
  isValidToken(token) {
    return token && typeof token === 'string' && token.length > 0;
  },

  /**
   * Valida se o valor está dentro da faixa esperada
   */
  isValidVolume(volume, validVolumes = [200, 300, 400, 500]) {
    return validVolumes.includes(volume);
  },

  /**
   * Valida se é um método de pagamento válido
   */
  isValidPaymentMethod(method) {
    const validMethods = ['PIX', 'CREDIT', 'DEBIT'];
    return validMethods.includes(method.toUpperCase());
  },

  /**
   * Formata moeda brasileira
   */
  formatCurrency(value) {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL'
    }).format(value);
  },

  /**
   * Calcula preço total baseado no volume
   * @param {number} volumeMl - Volume em mililitros
   * @param {number} pricePerMl - Preço por mililitro (ex: 0.04 = R$0.04/ml)
   * @returns {number} Preço total (ex: 300ml * 0.04 = R$12.00)
   */
  calculatePrice(volumeMl, pricePerMl) {
    const price = volumeMl * pricePerMl;
    return Math.round(price * 100) / 100; // Arredonda para 2 decimais
  },

  /**
   * Calcula tempo estimado de extração
   */
  estimateDispenseTime(volumeMl, flowRatePerSecond = 20) {
    // flowRate em ml/s (padrão 20ml/s)
    const timeSeconds = (volumeMl / flowRatePerSecond) * 1.2; // 20% de margem
    return Math.ceil(timeSeconds);
  },

  /**
   * Verifica se um token expirou
   */
  isTokenExpired(expiresAt) {
    if (!expiresAt) return true;
    const now = new Date().getTime();
    const expireTime = new Date(expiresAt).getTime();
    return now > expireTime;
  },

  /**
   * Gera um ID aleatório
   */
  generateId(prefix = '') {
    const timestamp = Date.now().toString(36);
    const randomStr = Math.random().toString(36).substr(2, 9);
    return prefix ? `${prefix}_${timestamp}${randomStr}` : `${timestamp}${randomStr}`;
  }
};

// Exportar para uso global
window.Validators = Validators;
