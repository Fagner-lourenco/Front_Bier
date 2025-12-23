/**
 * STORAGE.JS
 * Gerencia localStorage para recovery
 */

const Storage = {
  // Prefixo para todas as chaves
  PREFIX: 'bierpass_',

  /**
   * Salva dado no localStorage
   */
  set(key, value) {
    try {
      const fullKey = this.PREFIX + key;
      const data = typeof value === 'string' ? value : JSON.stringify(value);
      localStorage.setItem(fullKey, data);
      this.log(`Saved: ${key}`, value);
      return true;
    } catch (error) {
      console.error('Storage.set error:', error);
      return false;
    }
  },

  /**
   * Recupera dado do localStorage
   */
  get(key, defaultValue = null) {
    try {
      const fullKey = this.PREFIX + key;
      const data = localStorage.getItem(fullKey);
      
      if (data === null) return defaultValue;
      
      // Tenta fazer parse como JSON, senão retorna string
      try {
        return JSON.parse(data);
      } catch {
        return data;
      }
    } catch (error) {
      console.error('Storage.get error:', error);
      return defaultValue;
    }
  },

  /**
   * Remove dado do localStorage
   */
  remove(key) {
    try {
      const fullKey = this.PREFIX + key;
      localStorage.removeItem(fullKey);
      this.log(`Removed: ${key}`);
      return true;
    } catch (error) {
      console.error('Storage.remove error:', error);
      return false;
    }
  },

  /**
   * Limpa tudo do localStorage do app
   */
  clear() {
    try {
      const keys = Object.keys(localStorage);
      keys.forEach(key => {
        if (key.startsWith(this.PREFIX)) {
          localStorage.removeItem(key);
        }
      });
      this.log('Cleared all storage');
      return true;
    } catch (error) {
      console.error('Storage.clear error:', error);
      return false;
    }
  },

  /**
   * Salva token para recovery
   */
  saveToken(token, expiresAt) {
    this.set('current_token', {
      token: token,
      expiresAt: expiresAt,
      savedAt: new Date().toISOString()
    });
  },

  /**
   * Recupera token salvo
   */
  getToken() {
    const tokenData = this.get('current_token');
    
    if (!tokenData) return null;
    
    // Verifica se expirou
    if (Validators.isTokenExpired(tokenData.expiresAt)) {
      this.remove('current_token');
      return null;
    }
    
    return tokenData.token;
  },

  /**
   * Salva última transação
   */
  saveTransaction(transactionData) {
    this.set('last_transaction', {
      ...transactionData,
      savedAt: new Date().toISOString()
    });
  },

  /**
   * Recupera última transação
   */
  getLastTransaction() {
    return this.get('last_transaction');
  },

  /**
   * Salva estado atual para recovery
   */
  saveAppState(state, data) {
    this.set('app_state', {
      state: state,
      data: data,
      timestamp: new Date().getTime()
    });
  },

  /**
   * Recupera estado do app
   */
  getAppState() {
    return this.get('app_state');
  },

  /**
   * Limpa estado do app
   */
  clearAppState() {
    this.remove('app_state');
  },

  /**
   * Salva configurações de usuário
   */
  saveUserPreferences(preferences) {
    this.set('user_preferences', preferences);
  },

  /**
   * Recupera preferências do usuário
   */
  getUserPreferences() {
    return this.get('user_preferences', {
      language: 'pt-BR',
      theme: 'light'
    });
  },

  /**
   * Log interno de storage
   */
  log(message, data = '') {
    if (window.APP && window.APP.debug) {
      console.log(`[Storage] ${message}`, data);
    }
  }
};

// Exportar para uso global
window.Storage = Storage;
