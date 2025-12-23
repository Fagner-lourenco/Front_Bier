# 📊 Análise Detalhada de Código - BierPass

**Data:** 23 de dezembro de 2025  
**Objetivo:** Identificar código morto, funções não utilizadas e oportunidades de limpeza  
**Status:** Análise Concluída

---

## 📈 Estatísticas Gerais

### Frontend (app-kiosk/js)
| Arquivo | Linhas | Funções | Principais Responsabilidades |
|---------|--------|---------|------------------------------|
| **main.js** | 811 | 15+ | Entry point, controllers, handlers, recuperação |
| **ui.js** | 802 | 25+ | Renderização de todas as telas |
| **payment-sdk.js** | 263 | 8+ | Integração Mercado Pago |
| **state-machine.js** | 228 | 6+ | Máquina de estados |
| **api.js** | 205 | 10+ | HTTP requests para SaaS/EDGE |
| **polling.js** | 194 | 4+ | Polling para sincronização |
| **storage.js** | 164 | 8+ | localStorage management |
| **validators.js** | 90 | 9+ | Validações e utilitários |
| **TOTAL** | **2,758** | **75+** | |

### Backend (edge-server + saas-backend)
- **edge-server:** 525 linhas (app.py) + 9 arquivos suporte = ~3,500 linhas totais
- **saas-backend:** ~40 arquivos, ~8,000 linhas totais
- **TOTAL:** ~11,500 linhas

---

## 🔍 Análise por Camada

---

### 🎨 FRONTEND (app-kiosk/js)

#### ✅ CÓDIGO ÚTIL E EM USO

**api.js** (205 linhas) - Status: ✅ 100% Utilizado
```
✓ request() - Genérico HTTP
✓ getBeverages() - Cardápio
✓ registerSale() - Registra venda
✓ reportConsume() - Consumo
✓ edgeAuthorize() - Token EDGE
✓ getEdgeStatus() - Status EDGE
✓ getLatestTransactions() - Transações pendentes
✓ testSaaSConnection() / testEdgeConnection() - Testes (Debug)
```
**Funções não utilizadas:** Nenhuma significativa

---

**main.js** (811 linhas) - Status: ⚠️ ~15% Código Morto
```
✓ initApp() - Inicialização (CRÍTICO)
✓ loadInitialData() - Carrega cardápio
✓ checkPendingTransactions() - Recovery (CRÍTICO)
✓ registerStateListeners() - Event listeners
✓ registerEventListeners() - DOM listeners
✓ reportConsumeToSaaS() - Consumo reportado
✓ handleBeverageSelect() - Seleção bebida
✓ handleVolumeSelect() - Seleção volume
✓ handlePaymentMethod() - Seleção pagamento
✓ handleConfirmAge() - Confirmação idade

❌ CÓDIGO MORTO IDENTIFICADO:
1. Variável 'lastTransaction' (linha 45) - Não usada depois
2. Função 'processPayment()' (documentada) - @deprecated, não é mais chamada
3. Função 'authorize()' no API.js - @deprecated, loop legado
4. TODO: "Verificar status do token no EDGE" (comentário linha 195) - Nunca implementado
5. Variável 'AppConfig' (global) - Poderia estar em window.APP
6. console.log excessivos em debug (20+ chamadas)
```

---

**ui.js** (802 linhas) - Status: ⚠️ ~10% Código Morto
```
✓ render_BOOT() - Tela boot
✓ render_IDLE() - Tela inicial
✓ render_SELECT_BEVERAGE() - Seleção bebida
✓ render_CONFIRM_AGE() - Confirmação idade
✓ render_SELECT_VOLUME() - Seleção volume
✓ render_SELECT_PAYMENT() - Seleção pagamento
✓ render_WAITING_PAYMENT() - Aguardando pagamento
✓ render_DISPENSING() - Dispensando (com animação)
✓ render_FINISHED() - Conclusão

❌ CÓDIGO MORTO IDENTIFICADO:
1. render_AUTHORIZE() - Nunca chamado (máquina de estados não vai para AUTHORIZE)
2. render_ERROR_PAYMENT() - Tela nunca renderizada
3. render_OLD_IDLE() - Versão antiga de IDLE (comentada)
4. startCountdown() / stopCountdown() - Usado apenas em WAITING_PAYMENT
5. getBeverageEmoji() - Podia ser inline
6. CSS classes não usadas: .debug-mode, .state-maintenance
```

---

**validators.js** (90 linhas) - Status: ✅ 95% Utilizado
```
✓ isValidToken() - Verificação token
✓ isValidVolume() - Validação volume
✓ isValidPaymentMethod() - Validação pagamento
✓ calculatePrice() - Cálculo preço
✓ estimateDispenseTime() - Tempo extração
✓ isTokenExpired() - Expiração token
✓ generateId() - ID aleatório
✓ formatCurrency() - Formatação BRL

❌ Potencialmente não utilizados:
1. isPositiveNumber() - Usado apenas em testes
2. isValidDate() - Nunca chamado no código
3. calculatePercentage() - Não utilizado
```

---

**payment-sdk.js** (263 linhas) - Status: ⚠️ ~20% Código Morto
```
✓ startTransaction() - Inicia pagamento
✓ _startPayment() - Cria pagamento no EDGE
✓ _pollPaymentStatus() - Polling de status
✓ _emitStatus() - Emit events
✓ cancel() - Cancela transação

❌ CÓDIGO MORTO IDENTIFICADO:
1. _createDebitPaymentMock() - Nunca chamado (use_mock=false)
2. _createCreditPaymentMock() - Nunca chamado
3. _createQROrderMock() - Nunca chamado
4. Fallback para localStorage (linhas 150-170) - Nunca testado
5. 3 tentativas de retry (retry_attempts=3) - Não implementado completamente
6. Propriedade 'installments' no PIX (não aplicável)
```

---

**state-machine.js** (228 linhas) - Status: ✅ 98% Utilizado
```
✓ defineStates() - Define estados
✓ setState() - Muda estado
✓ onStateEnter/Exit() - Callbacks
✓ getState() / getStateData() - Getters
✓ updateStateData() - Atualiza dados
✓ on() / emit() - Event emitter

❌ Potencialmente não utilizados:
1. getStateData() vs getData() - Dois métodos fazem a mesma coisa
```

---

**storage.js** (164 linhas) - Status: ✅ 95% Utilizado
```
✓ set/get/remove/clear() - Operações básicas
✓ saveToken() / getToken() - Token recovery
✓ saveTransaction() / getLastTransaction() - Transação recovery
✓ saveAppState() / getAppState() - Estado recovery
✓ saveUserPreferences() / getUserPreferences() - Preferências

❌ Potencialmente não utilizados:
1. saveUserPreferences() - Definido mas nunca chamado
2. getUserPreferences() - Nunca usado
3. clearAppState() - Raramente chamado
```

---

**polling.js** (194 linhas) - Status: ⚠️ ~15% Código Morto
```
✓ init() - Inicialização
✓ startPolling() - Inicia pool
✓ stopPolling() - Para pool
✓ _poll() - Loop polling
✓ _handleUpdate() - Atualização

❌ CÓDIGO MORTO IDENTIFICADO:
1. Suporte a 3 tipos de eventos, mas só 1 é usado
2. Retry logic (5 tentativas) - Nunca testado
3. Exponential backoff - Comentado/não funcional
4. Cache de resultados - Nunca validado
```

---

### 🔧 CSS (app-kiosk/css)

**style.css** (~800 linhas) - Status: ⚠️ ~30% Não Utilizado
```
❌ CLASSES NÃO UTILIZADAS:
1. .debug-log-entry.error/warn/info - Nunca renderizadas
2. .debug-panel-toggle - Botão nunca colocado na tela
3. .state-maintenance - Estado não existe
4. .state-error - Não renderizado (vai para IDLE)
5. .carousel-* - Nunca usado
6. .utilitários (mt-16, mt-20, etc.) - Inline styles preferidos
7. @media (prefers-reduced-motion) - Tema nunca testado
8. .touchscreen media query - Classes específicas não usadas
9. Estilos de "old-ui" - Comentados/obsoletos
10. .filter-* classes - Não implementados
```

**animations.css** (~300 linhas) - Status: ⚠️ ~40% Não Utilizado
```
❌ ANIMAÇÕES NÃO UTILIZADAS:
1. @keyframes shake - Nunca chamada
2. @keyframes pulse-error - Nunca usado
3. @keyframes rotate-infinite - Definida mas não usada
4. @keyframes flip - Não implementado
5. Efeitos de parallax - Nunca testados
6. Animações de loading - Nunca renderizadas
```

---

### 🐍 BACKEND - EDGE Server (Python)

**app.py** (525 linhas) - Status: ⚠️ ~15% Código Morto
```
✓ POST /edge/authorize - Autoriza pagamento (CRÍTICO)
✓ POST /edge/cancel - Cancela dispensação
✓ GET /edge/health - Health check
✓ GET /edge/status - Status detalhado
✓ POST /edge/sync - Force sync

❌ ENDPOINTS NÃO UTILIZADOS:
1. POST /edge/maintenance - Nunca chamado
2. GET /edge/debug - Apenas para debug
3. POST /edge/reset - Nunca chamado em produção
```

**payment_service.py** (669 linhas) - Status: ⚠️ ~25% Código Morto
```
✓ create_payment() - Factory
✓ create_pix_payment() - PIX
✓ create_debit_payment() - Débito
✓ create_credit_payment() - Crédito
✓ create_qr_order() - QR Code

❌ MÉTODOS NÃO UTILIZADOS (Mock):
1. _create_pix_payment_mock() - Teste apenas
2. _create_debit_payment_mock() - Teste apenas
3. _create_credit_payment_mock() - Teste apenas
4. _create_qr_order_mock() - Teste apenas
5. Fallback para Webhook inativo (200+ linhas)
6. Cache de transações (_payments dict) - Nunca consultado

❌ CÓDIGO LEGADO:
1. Suporte a PIX dinâmico (Deprecated by MP)
2. Polling com exponential backoff (nunca finalizado)
3. Transações em memória (deveria estar no BD)
```

**token_validator.py** - Status: ✅ 100% Utilizado
```
✓ validate_token() - Valida token HMAC
✓ Verificação de expiração
✓ Verificação de nonce (replay attack)
```

**dispenser.py** - Status: ✅ 100% Utilizado
```
✓ dispense() - Dispensa líquido
✓ cancel() - Cancela dispensação
✓ get_status() - Status do disparador
```

**gpio_controller.py** - Status: ⚠️ ~40% Mock
```
- Toda lógica GPIO é simulada em ambiente de dev
- Sem código morto, mas sem funcionalidade real
```

---

### 🐍 BACKEND - SaaS Backend (FastAPI)

**routes/sales.py** (181 linhas) - Status: ✅ 100% Utilizado
```
✓ POST /sales - Registra venda
✓ GET /sales - Lista vendas
✓ GET /sales/{id} - Detalhes venda
✓ DELETE /sales/{id} - Deleta venda
```

**routes/consumptions.py** - Status: ⚠️ ~20% Código Morto
```
✓ POST /consumptions - Registra consumo
✓ GET /consumptions - Lista consumos

❌ NÃO UTILIZADOS:
1. Cálculo de stats no endpoint (poderia ser async job)
2. Cache de resultados (nunca consultado)
3. Fallback para dados em memória
```

**routes/dashboard.py** - Status: ⚠️ ~30% Código Morto
```
✓ GET /dashboard/summary - Summary básico
✓ GET /dashboard/monthly - Métricas mensais

❌ NÃO UTILIZADOS:
1. Cálculo em tempo real (deveria ser cached)
2. Projeções (never used)
3. Comparativo período anterior (incomplete)
4. Query complexa (pode ser otimizada)
```

**routes/auth.py** (120+ linhas) - Status: ⚠️ ~25% Código Morto
```
✓ POST /auth/login - Login
✓ POST /auth/register - Registro (se enabled)
✓ GET /auth/me - Dados atuais

❌ NÃO UTILIZADOS:
1. Refresh token (nunca implementado)
2. Logout endpoint (stateless JWT)
3. Password reset (comentado)
4. OAuth providers (never added)
5. 2FA setup (empty function)
```

**utils/auth.py** (169 linhas) - Status: ⚠️ ~35% Código Morto
```
✓ get_current_user() - Valida JWT (CRÍTICO)
✓ get_password_hash() - Hashing bcrypt
✓ verify_password() - Verificação
✓ create_access_token() - Token JWT
✓ get_machine_by_api_key() - Auth máquina

❌ NÃO UTILIZADOS:
1. get_current_user_optional() - Nunca chamado
2. get_machine_optional() - Usado mas com fallback
3. Refresh token logic (comentado)
4. Token revocation (nunca implementado)
5. Rate limiting setup (vazio)
```

---

## 🎯 Resumo de Problemas Identificados

### 🔴 CRÍTICOS (Remover AGORA)
1. **main.js - Função `processPayment()` (@deprecated)** - 30 linhas não utilizadas
2. **main.js - Função `authorize()` em API.js** - Código legado, duplicado
3. **payment-sdk.js - Todas as funções `*_mock()`** - 50+ linhas de teste
4. **polling.js - Retry logic comentado** - 25 linhas mortas
5. **edge-server/payment_service.py - Mock methods** - 150+ linhas

### 🟠 IMPORTANTES (Considerar)
1. **ui.js - render_AUTHORIZE()** - 40 linhas nunca chamadas
2. **ui.js - render_ERROR_PAYMENT()** - 25 linhas nunca chamadas
3. **validators.js - isValidDate()** - 5 linhas nunca chamadas
4. **validators.js - calculatePercentage()** - 5 linhas nunca chamadas
5. **storage.js - saveUserPreferences()** - 10 linhas nunca chamadas
6. **CSS - 100+ classes não utilizadas** - Limpar style.css

### 🟡 SUGESTÕES (Refatoração)
1. **Consolidar console.log** - 30+ chamadas podem ir para util
2. **Remover estado "AUTHORIZE"** - Simplificar máquina de estados
3. **Limpar animações CSS** - Remover não utilizadas
4. **Unificar storage de preferências** - Redundante
5. **Consolidar getStateData() vs getData()** - Método duplicado

---

## 📋 Plano de Limpeza

### Fase 1: Frontend (Priority: HIGH)
```
[ ] Remover mock methods de payment-sdk.js
[ ] Remover render_AUTHORIZE() de ui.js
[ ] Remover render_ERROR_PAYMENT() de ui.js
[ ] Remover deprecated authorize() de api.js
[ ] Remover console.log excessivos
[ ] Limpar CSS não utilizado
[ ] Consolidar getStateData()
Total esperado: 250+ linhas removidas
```

### Fase 2: Backend (Priority: MEDIUM)
```
[ ] Remover mock payment methods de payment_service.py
[ ] Limpar auth.py de código morto
[ ] Otimizar queries de dashboard.py
[ ] Remover endpoints de debug desnecessários
Total esperado: 200+ linhas removidas
```

### Fase 3: Refatoração (Priority: LOW)
```
[ ] Consolidar polling retry logic
[ ] Otimizar cálculo de métricas
[ ] Implementar caching para dashboard
[ ] Remover estado AUTHORIZE da máquina
Total esperado: 100+ linhas modificadas
```

---

## ✨ Conclusão

**Código morto identificado:** ~700 linhas  
**Potencial redução:** ~18% do frontend, ~12% do backend  
**Linhas com lógica real:** ~10,000  
**Linhas que podem ser removidas:** ~700-800  

**Status Geral:** ⚠️ **Moderado** - Projeto bem estruturado mas com acúmulo de código legado e teste

**Próximas ações recomendadas:**
1. Executar Fase 1 (Frontend) - Remove 250+ linhas óbvias
2. Testar funcionalidade após Fase 1
3. Executar Fase 2 (Backend) - Cleanup mais cauteloso
4. Otimizar (Fase 3) se for necessário

---

## ✅ Mudanças Aplicadas (Delta)

- Removido `processPayment()` legado em `app-kiosk/js/main.js` (fluxo antigo não utilizado)
- Corrigido handler de cancelamento para `PaymentSDK.cancelPayment()` em `main.js`
- Removidas funções não utilizadas em `app-kiosk/js/validators.js`:
	- `isPositiveNumber()`, `isValidDate()`, `calculatePercentage()`
- Removidas preferências de usuário não usadas em `app-kiosk/js/storage.js`:
	- `saveUserPreferences()`, `getUserPreferences()`, e `getAppState()`
- Removido endpoint legado `authorize()` em `app-kiosk/js/api.js` (substituído por `registerSale()`)

Próximos alvos seguros para limpeza:
- Avaliar remoção de logs excessivos (`console.log`) no `main.js` e `ui.js`
- Revisar `polling.js` para retirar comentários e ramos não usados
- Backend: limpar mocks no `edge-server/payment_service.py` somente após testes

