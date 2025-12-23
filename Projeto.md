# 🍺 BIERPASS - DISTRIBUIDOR INTELIGENTE DE BEBIDAS

**Versão:** MVP Simplificado  
**Data:** 22 de dezembro de 2025  
**Status:** Planejamento Final e Executável

---

## 📋 RESUMO EXECUTIVO

**O que é:**  
Sistema distribuidor automático de bebidas alcoólicas com verificação de idade (+18), pagamento via maquininha física e controle de dose preciso.

**Como funciona:**
1. Cliente seleciona bebida e volume no tablet
2. Confirma que tem +18
3. Realiza pagamento na maquininha física (PIX/Crédito/Débito)
4. Sistema libera dosagem automática
5. Cliente recebe bebida na quantidade exata

**Arquitetura (3 camadas):**
```
[APP + MAQUININHA] → [EDGE] → [SaaS]
   Tablet + SDK       Raspberry  Backend
  (UX + Pagamento)    (Física)   (Gestão)
```

**Princípios Fundamentais:**
- ✅ O EDGE (Raspberry) tem controle total - nunca perde autoridade
- ✅ O SaaS (Backend) apenas registra e gerencia - NÃO processa pagamento
- ✅ O APP (Tablet) guia o cliente + integra com maquininha via SDK
- ✅ Maquininha física (Cielo/Stone/PagSeguro) processa pagamento
- ✅ Sistema funciona offline - EDGE finaliza dose mesmo sem internet

---

## 🎯 AS 3 CAMADAS EXPLICADAS

### 🟦 CAMADA 1: APP KIOSK (Tablet/Web)

**O que faz:**
- Exibe cardápio com imagens
- Confirma idade (+18)
- Deixa cliente escolher volume/quantidade
- **Integra com maquininha via SDK** (Cielo/Stone/PagSeguro)
- Exibe tela "Aproxime o cartão" ou QR Code PIX
- Gera token de autorização local (após pagamento aprovado)
- Mostra progresso em tempo real
- Registra venda no SaaS (background)
- Agradece e volta ao início

**O que NÃO faz:**
- ❌ Controla bomba/hardware
- ❌ Decide quantidade ml
- ❌ Gerencia internet
- ❌ Processa pagamento diretamente (delega à maquininha)

**Stack:** HTML5 + CSS3 + JavaScript + SDK Maquininha

---

### 🟩 CAMADA 2: SaaS (Backend) - SIMPLIFICADO

**O que faz:**
- CRUD de bebidas (nome, preço, estoque)
- CRUD de máquinas (localização, status)
- Recebe e registra vendas (histórico)
- Recebe e registra consumos do EDGE
- Fornece dados para dashboard/relatórios
- Gerencia usuários administradores

**O que NÃO faz:**
- ❌ Processa pagamento (maquininha faz)
- ❌ Gera tokens (APP faz localmente)
- ❌ Controla hardware
- ❌ Aciona bomba

**Stack:** Python (FastAPI) + PostgreSQL

---

### 🟥 CAMADA 3: EDGE (Raspberry Pi)

**O que faz:**
- Recebe autorização via APP (token local)
- Valida token (assinatura + expiração + uso único)
- Aciona bomba com precisão
- Mede volume via sensor
- Para exatamente no ml correto
- Registra consumo em SQLite local
- Sincroniza com SaaS quando online

**O que NÃO faz:**
- ❌ Depende do SaaS para terminar
- ❌ Para se internet cair
- ❌ Processa pagamento

**Stack:** Python (Flask) + SQLite + GPIO

---

## 💳 INTEGRAÇÃO COM MAQUININHA (SDK)

### Maquininhas Suportadas
| Provider | SDK | Conexão | PIX | Observações |
|----------|-----|---------|-----|-------------|
| **Stone** | stone-sdk-js | USB/Bluetooth | ✅ | Melhor para Web/Electron |
| **Cielo LIO** | lio-sdk | Android nativo | ✅ | Tablet Android dedicado |
| **PagSeguro** | PlugPag | Bridge USB | ✅ | Moderninha Pro |
| **Rede** | e.Rede | USB/Serial | ✅ | Menos comum |

### Fluxo de Pagamento com Maquininha

```
┌─────────────────────────────────────────────────────────────────┐
│ FLUXO DE PAGAMENTO (Nova Arquitetura)                           │
│                                                                 │
│ 1. Cliente escolhe bebida/volume no APP                         │
│    ↓                                                            │
│ 2. APP calcula valor total                                      │
│    ↓                                                            │
│ 3. APP mostra: "Escolha forma de pagamento"                     │
│    [PIX] [Crédito] [Débito]                                     │
│    ↓                                                            │
│ 4. APP chama SDK: PaymentSDK.startTransaction(valor, tipo)      │
│    ↓                                                            │
│ 5. APP mostra: "Aproxime/insira cartão na maquininha"           │
│    (ou exibe QR Code PIX se for PIX)                            │
│    ↓                                                            │
│ 6. Maquininha processa pagamento localmente                     │
│    ↓                                                            │
│ 7. SDK retorna: { status: APPROVED, transactionId, nsu }        │
│    ↓                                                            │
│ 8. APP gera token local: generateLocalToken(transactionId)      │
│    ↓                                                            │
│ 9. APP envia token ao EDGE: POST /edge/authorize                │
│    ↓                                                            │
│ 10. EDGE valida e dispensa bebida                               │
│    ↓                                                            │
│ 11. APP registra venda no SaaS (background, não bloqueia)       │
│     POST /api/v1/sales                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Exemplo de Código SDK (Genérico)

```javascript
// payment-sdk.js - Interface unificada para qualquer maquininha

const PaymentSDK = {
  provider: null, // 'stone', 'cielo', 'pagseguro', 'mock'
  
  async init(config) {
    this.provider = config.provider;
    // Inicializa SDK específico
  },
  
  async startTransaction(options) {
    // options: { amount, paymentType, installments }
    // paymentType: 'PIX', 'CREDIT', 'DEBIT'
    
    // Retorna:
    // {
    //   status: 'APPROVED' | 'DENIED' | 'CANCELLED' | 'ERROR',
    //   transactionId: 'SDK_123456',
    //   nsu: '987654',
    //   authCode: 'ABC123',
    //   cardBrand: 'VISA',
    //   lastDigits: '1234',
    //   pixQRCode: 'base64...' (se PIX)
    // }
  },
  
  async cancelTransaction(transactionId) {
    // Cancela transação se necessário
  },
  
  async getTransactionStatus(transactionId) {
    // Consulta status
  }
};
```

### Token Gerado Localmente

```javascript
// Gera token após pagamento aprovado
function generateLocalToken(sdkResult, volumeMl) {
  const payload = {
    transactionId: sdkResult.transactionId,
    nsu: sdkResult.nsu,
    ml_authorized: volumeMl,
    created_at: new Date().toISOString(),
    expires_at: new Date(Date.now() + 90000).toISOString() // 90s
  };
  
  // Chave HMAC pode ficar no APP (ambiente controlado)
  const signature = hmacSHA256(JSON.stringify(payload), HMAC_SECRET);
  
  return {
    token: btoa(JSON.stringify(payload)),
    signature: signature,
    expires_at: payload.expires_at
  };
}
```

---

## 🔄 FLUXO COMPLETO (PASSO A PASSO)

```
PARTE 1: CLIENTE INTERAGE COM APP
1. Cliente toca tela → APP carrega
2. APP mostra cardápio
3. Cliente seleciona "Chopp 300ml - R$12"
4. APP pede: "Você tem +18?"
5. Cliente confirma: SIM
6. APP mostra volumes (200/300/400/500ml)
7. Cliente escolhe: 300ml
8. APP pede pagamento: PIX / Crédito / Débito
9. Cliente escolhe: PIX

PARTE 2: APP COMUNICA COM MAQUININHA (SDK)
10. APP chama SDK: startTransaction(1200, 'PIX')
11. Se PIX → APP exibe QR Code na tela
12. Se Cartão → APP mostra "Aproxime na maquininha"
13. Cliente realiza pagamento
14. SDK retorna: { status: APPROVED, transactionId: 'SDK_123' }
15. APP gera token LOCAL com HMAC

PARTE 3: APP ENVIA TOKEN AO EDGE
16. APP envia TOKEN ao EDGE (HTTP local)
17. EDGE recebe e valida TOKEN
18. EDGE verifica: assinatura OK? Expirou? Já usado?

PARTE 4: EDGE EXECUTA EXTRAÇÃO
19. EDGE aciona bomba (GPIO 17 = HIGH)
20. EDGE começa contar pulsos do sensor
21. EDGE atualiza status a cada 100ms: "ml_servido / ml_alvo"
22. APP faz polling a cada 300ms: GET /edge/status
23. APP mostra barra animada: "145 / 300 ml (48%)"

PARTE 5: EDGE FINALIZA
24. Quando ml_servido atinge 300ml:
25. EDGE desliga bomba (GPIO 17 = LOW)
26. EDGE registra consumo em SQLite
27. EDGE enfileira: "enviar ao SaaS"
28. EDGE responde: status = FINISHED

PARTE 6: APP FINALIZA
29. APP detecta FINISHED
30. APP mostra: "Pronto! Aproveite!"
31. Auto-volta para IDLE em 5s
32. Cliente pega copo e vai embora

PARTE 7: SINCRONIZAÇÃO (background)
33. APP registra venda no SaaS: POST /api/v1/sales
34. EDGE envia consumo ao SaaS: POST /api/v1/consumptions
35. Se internet DOWN → fila local, retry quando voltar
```

---

## 📐 MÁQUINA DE ESTADOS DO APP

```
BOOT (2s)
  │
  ▼
IDLE / HOME (cardápio)
  │ [Cliente toca bebida]
  ▼
CONFIRM_AGE (popup +18) ← Se bebida alcoólica
  │ [SIM] ou [NÃO→IDLE]
  ▼
SELECT_VOLUME
  │ [Escolhe 200/300/400/500ml]
  ▼
SELECT_PAYMENT (PIX/Crédito/Débito)
  │
  ▼
AWAITING_PAYMENT (aguardando maquininha/QR PIX)
  │ ← SDK callback
  ├─→ PAYMENT_DENIED (volta IDLE)
  │
  ├─→ AUTHORIZED (1s loader)
      │
      ▼
      DISPENSING (CRÍTICA - polling 300ms)
        Mostra: "145 / 300 ml (48%)"
        Barra animada
        NUNCA congelada
      │
      ▼
      FINISHED (5s auto-return)
        "Obrigado! Aproveite!"
      │
      ▼
      IDLE (reinicia)
```

---

## 🖥️ TELAS DO APP (DETALHES)

### TELA 1: BOOT
- Logo + "Verificando conexão..."
- Duração: 2 segundos máximo
- Vai para: IDLE

### TELA 2: IDLE / HOME
- Logo grande no topo
- Grid 2x2 (ou scroll) com bebidas
- Cada card: Imagem | Nome | Tipo | ABV% | Preço
- Timeout inatividade: 30s → reinicia

### TELA 3: SELECT_VOLUME
- Título: "Qual volume você quer?"
- 4 botões: "200ml - R$8" | "300ml - R$12" | "400ml - R$16" | "500ml - R$20"
- Botão voltar

### TELA 4: CONFIRM_AGE
- Aviso: "Para comprar bebida alcoólica, confirme que você tem mais de 18 anos"
- Botão: "✅ Tenho +18" | "❌ Não tenho"
- Timeout: 15s → IDLE
- Se negar: volta IDLE

### TELA 5: SELECT_PAYMENT
- Resumo: "Chopp 300ml - R$ 12,00"
- Texto: "Como você quer pagar?"
- 3 opções: "💳 PIX" | "💳 Crédito" | "💳 Débito"
- Botão voltar

### TELA 6: AWAITING_PAYMENT (NOVA!)
**Para Cartão (Crédito/Débito):**
- Ícone de cartão animado
- "Aproxime ou insira o cartão na maquininha"
- Valor: "R$ 12,00"
- Botão cancelar
- Timeout: 120s

**Para PIX:**
- QR Code grande e centralizado
- "Escaneie o QR Code para pagar"
- Valor: "R$ 12,00"
- Timer: "Expira em 5:00"
- Botão cancelar
- Timeout: 300s (5 min)

### TELA 7: PAYMENT_DENIED
- ❌ Ícone erro
- "Pagamento não foi aprovado. Tente novamente."
- Timeout: 5s → IDLE

### TELA 8: DISPENSING (A MAIS IMPORTANTE!)
**Requisitos obrigatórios:**
- ✅ Barra de progresso visual (0% → 100%)
- ✅ Número GRANDE: **245 / 300 ml**
- ✅ Porcentagem: **48%**
- ✅ Mensagem: "Servindo sua bebida..."
- ✅ Atualiza CADA 300ms (polling)
- ✅ NUNCA travado ou congelado

Layout:
```
┌─────────────────────────┐
│   Servindo sua bebida   │
│                         │
│    [█████░░░░░░]        │
│     48% Pronto          │
│                         │
│   245 ml / 300 ml       │
└─────────────────────────┘
```

### TELA 9: FINISHED
- ✅ Ícone sucesso
- "Obrigado! Aproveite sua bebida!"
- Exibe: "300 ml de Chopp"
- Auto-volta para IDLE em 5s

---

## ⚙️ MÁQUINA DE ESTADOS DO EDGE

```
IDLE
  │ [Recebe TOKEN válido]
  ▼
TOKEN_VALIDATED
  │ [Inicia extração]
  ▼
DISPENSING
  │ Bomba ON
  │ Conta pulsos
  │ Publica status a cada 100ms
  │
  ├─→ FINISHED (atingiu ml alvo)
  │
  └─→ ERROR (timeout ou falha)
      │
      ▼
      SYNC_TO_SAAS
        Tenta enviar consumo
        Retry exponencial se falhar
        Se offline: armazena em fila
      │
      ▼
      IDLE (reinicia)
```

---

## 🔌 HARDWARE DO EDGE (O que comprar)

| Componente | Especificação | Por quê |
|-----------|--------------|--------|
| **Microcontrolador** | Raspberry Pi 4 (2-4GB) | Processamento + GPIO estável |
| **SO** | Raspberry Pi OS Lite | Leve, sem GUI desnecessária |
| **Bomba** | Peristáltica 12V, 30-50ml/s | Dosagem precisa, não contamina |
| **Sensor** | YF-S201 (Hall Effect, 5V) | ±5% precisão, barato |
| **Relé** | 5V optoacoplado | Acionamento seguro 12V |
| **Fonte 5V** | 3A dedicada | Alimenta Raspberry |
| **Fonte 12V** | 5A dedicada | Alimenta bomba |
| **DB** | SQLite | Logs offline |
| **Mangueira** | Silicone grau alimentício | Não contamina |
| **Fusível** | 5A no circuito 12V | Proteção |

### Conexões Elétricas:
```
Raspberry GPIO 17 → Relé IN → Bomba 12V
Raspberry GPIO 27 ← Sensor YF-S201 (pulsos)
GND comum (Raspberry / Relé / Sensor)

Fonte 5V → Raspberry + Relé + Sensor
Fonte 12V → Bomba
```

---

## 💾 BANCO DE DADOS LOCAL (EDGE - SQLite)

### Tabela: consumptions
```
id               → auto-increment
token_id         → referência
volume_ml        → 300
started_at       → ISO timestamp
finished_at      → ISO timestamp
status           → 'OK' | 'ERROR' | 'PARTIAL'
sent             → false (pendente) | true (enviado)
created_at       → timestamp
```

### Tabela: events
```
id               → auto-increment
event_type       → 'TOKEN_REC' | 'DISPENSE_START' | 'DISPENSE_FINISH' | 'ERROR'
details          → JSON com contexto
created_at       → timestamp
```

---

## 🌐 API DO EDGE (HTTP Local)

### POST /edge/authorize
**Recebe TOKEN do APP**
```json
{
  "token": "abc123xyz",
  "ml_authorized": 300,
  "signature": "hmac_sha256_value",
  "expires_at": "2025-12-22T14:30:00Z"
}
```
**Responde:**
```json
{
  "status": "OK",
  "ml_authorized": 300,
  "timeout_sec": 35
}
```

### GET /edge/status
**Para APP fazer polling**
```json
{
  "state": "DISPENSING",
  "ml_served": 145,
  "ml_authorized": 300,
  "percentage": 48,
  "timestamp": "2025-12-22T14:30:45Z"
}
```

### POST /edge/maintenance
**Para ativar/desativar modo manutenção**
```json
{
  "action": "start" | "stop"
}
```

---

## 🌐 API DO SaaS (HTTPS) - SIMPLIFICADA

### GET /api/v1/beverages
**Retorna lista de bebidas**
```json
{
  "beverages": [
    {
      "id": 1,
      "name": "Chopp",
      "style": "Pilsen",
      "abv": 5.0,
      "price_per_ml": 0.04,
      "image_url": "https://...",
      "active": true
    }
  ]
}
```

### POST /api/v1/beverages
**Cadastra nova bebida (admin)**
```json
{
  "name": "Chopp",
  "style": "Pilsen",
  "abv": 5.0,
  "price_per_ml": 0.04
}
```

### PUT /api/v1/beverages/{id}
**Atualiza bebida (admin)**

### DELETE /api/v1/beverages/{id}
**Remove bebida (admin)**

### GET /api/v1/machines
**Lista máquinas cadastradas**

### POST /api/v1/machines
**Cadastra nova máquina (admin)**

### PUT /api/v1/machines/{id}
**Atualiza máquina (admin)**

### POST /api/v1/sales
**APP registra venda após pagamento aprovado (background)**
```json
{
  "machine_id": "M001",
  "beverage_id": 1,
  "volume_ml": 300,
  "total_value": 12.00,
  "payment_method": "PIX",
  "payment_transaction_id": "SDK_123456",
  "payment_nsu": "987654",
  "created_at": "2025-12-22T14:22:00Z"
}
```
**Retorna:**
```json
{
  "sale_id": "SALE_789",
  "status": "REGISTERED"
}
```

### POST /api/v1/consumptions
**EDGE envia consumo realizado**
```json
{
  "sale_id": "SALE_789",
  "machine_id": "M001",
  "ml_served": 300,
  "status": "OK",
  "started_at": "2025-12-22T14:22:10Z",
  "finished_at": "2025-12-22T14:22:40Z"
}
```

### GET /api/v1/dashboard
**Métricas para dashboard (admin)**
```json
{
  "today": {
    "total_sales": 45,
    "total_revenue": 540.00,
    "total_ml": 13500
  },
  "month": {...}
}
```

---

## 🔐 SEGURANÇA (SIMPLIFICADA)

### Tokenização Local:
- Token gerado pelo APP após pagamento aprovado ✓
- Contém: transactionId (da maquininha) + ml + timestamp ✓
- Assinado com HMAC-SHA256 (chave no APP) ✓
- Válido por 90 segundos ✓
- Uso único (EDGE marca após usar) ✓

### Chave HMAC:
- Pode ficar no APP (ambiente controlado, kiosk dedicado)
- Mesma chave configurada no EDGE
- Rotação manual periódica recomendada

### No EDGE:
- Valida assinatura HMAC ✓
- Valida expiração ✓
- Valida uso único ✓
- Rate limit: máx 5 falhas/minuto ✓

### Comunicação:
- HTTPS entre APP ↔ SaaS (quando online) ✓
- HTTP simples entre APP ↔ EDGE (rede local) ✓
- Sem exposição de EDGE à internet ✓
- Maquininha processa pagamento (PCI-DSS certificada) ✓

---

## 🛡️ OPERAÇÃO OFFLINE

### Cenário 1: Internet cai ANTES de pagar
- ✅ Maquininha física funciona offline (para cartão débito/crédito)
- ⚠️ PIX requer internet na maquininha
- ✅ APP pode oferecer apenas Cartão se sem internet

### Cenário 2: Internet cai DURANTE extração
- ✅ EDGE continua e finaliza dose
- ✅ EDGE registra em SQLite
- ✅ EDGE enfileira para enviar ao SaaS depois
- ✅ Nunca perde consumo

### Cenário 3: Internet volta
- ✅ APP envia vendas pendentes ao SaaS
- ✅ EDGE envia consumos pendentes ao SaaS
- ✅ Retry exponencial: 5s → 10s → 20s
- ✅ Marca como enviado após 200 OK

---

## ⏱️ TIMEOUTS REALISTAS

| Evento | Duração | Razão |
|--------|---------|-------|
| BOOT | 2s | Verificação |
| IDLE timeout | 30s | Inatividade |
| CONFIRM_AGE | 15s | Decisão cliente |
| PAYMENT | 30s | Processamento |
| TOKEN válido | 90s | Janela de início |
| DISPENSING | Dinâmico* | (ml ÷ vazão) × 1.8 |
| FINISHED → IDLE | 5s | Feedback |

*Exemplo: 300ml ÷ 30ml/s × 1.8 = ~18 segundos

---

## 🧪 TESTES OBRIGATÓRIOS

### EDGE (com água):
- [ ] 100 ciclos de extração
- [ ] Volumes: 200ml, 300ml, 500ml (5x cada)
- [ ] Simular falha de rede (desplug)
- [ ] Simular sensor preso (timeout)
- [ ] Simular token expirado
- [ ] Verificar logs após cada ciclo

### APP:
- [ ] Fluxo completo 10x seguidas
- [ ] Refresh no meio da extração
- [ ] EDGE offline
- [ ] Teste com pessoas reais (sem instruir)

### Integrados:
- [ ] Pagamento → Token → EDGE → Consumo
- [ ] APP reinicia mid-fluxo → recupera
- [ ] Internet OFF/ON → sincronização automática

---

## 📊 MODELO DE DADOS DO SaaS (PostgreSQL)

### Tabela: machines
```sql
id, name, location, status, hmac_key, created_at
```

### Tabela: beverages
```sql
id, name, style, abv, price_per_ml, image_url, active, created_at
```

### Tabela: sales
```sql
id, machine_id (FK), beverage_id (FK), 
volume_ml, total_value, 
payment_method, payment_transaction_id, payment_nsu,
created_at
```

### Tabela: consumptions
```sql
id, sale_id (FK), machine_id,
ml_served, status (OK/ERROR/PARTIAL), 
started_at, finished_at, synced_at
```

---

## 📊 MÉTRICAS DO DASHBOARD

### Por máquina:
- Total ml vendido (dia/mês/ano)
- Total vendas em R$ (dia/mês/ano)
- Ticket médio
- Taxa de sucesso (%)
- Tempo médio de extração
- Falhas por tipo

### Sistema geral:
- Uptime de máquinas
- Latência APP ↔ EDGE
- Taxa de sincronização offline
- Erros mais comuns

---

## 🚀 ROADMAP

### MVP (Agora):
- ✅ 1 máquina
- ✅ Chopp / Água de Coco
- ✅ Pagamento PIX/Crédito/Débito
- ✅ Sem tokens rotativos

### V2 (Depois):
- 📌 Múltiplas máquinas
- 📌 Bebidas espumantes (com pressão)
- 📌 Tokens rotativos
- 📌 App mobile complementar

### V3 (Bem depois):
- 📌 IA para estoque
- 📌 Fidelização
- 📌 Multi-localidade

---

## 📅 CRONOGRAMA ESTIMADO

| Fase | Etapa | Tempo |
|------|-------|-------|
| 1 | Design + Wireframes | 1 semana |
| 2 | APP Frontend (mock) | 2 semanas |
| 3 | Hardware EDGE | 1 semana |
| 4 | Sensor + calibração | 1 semana |
| 5 | Controle da bomba | 1 semana |
| 6 | SaaS Backend + DB | 2 semanas |
| 7 | Integração APP ↔ SaaS ↔ EDGE | 1 semana |
| 8 | Testes bancada | 1 semana |
| 9 | Testes operacionais | 1 semana |
| 10 | Ajustes finais | 1 semana |
| **Total** | | **~13 semanas** |

---

## ✅ CHECKLIST PRÉ-OPERAÇÃO

- [ ] APP passa em 100 ciclos
- [ ] EDGE passa em 100 ciclos com água
- [ ] SaaS processa pagamentos OK
- [ ] Offline/online alternado funciona
- [ ] Logs auditáveis e completos
- [ ] Documentação operacional pronta
- [ ] Treinamento de operador feito
- [ ] Seguro e compliance verificados

---

## 🤝 RESPONSABILIDADES DO TIME

### Você (desenvolvedor):
- Código EDGE (Python + GPIO)
- Arquitetura SaaS (FastAPI)
- Testes integração

### Designer:
- Wireframes finais
- Design visual APP
- Prototipagem interativa

### Eletricista:
- Montagem elétrica
- Calibração sensor
- Testes hardware

---

## 🔥 PRÓXIMOS PASSOS IMEDIATOS

1. **Semana 1:** Revisar documento + contatar designer
2. **Semana 1-2:** Começar montagem EDGE (compra componentes)
3. **Semana 2:** Começar APP (HTML/CSS + mocks)
4. **Semana 3:** Backend (FastAPI setup)

---

**Fim do Planejamento**  
✓ Documento limpo e organizado  
✓ Sem duplicações  
✓ Pronto para execução  
✓ MVP simplificado

Versão 2.0 - Dezembro 2025
