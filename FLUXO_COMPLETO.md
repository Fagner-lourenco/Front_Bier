# 🍺 BierPass - Fluxo Completo da Aplicação

## 📊 Visão Geral da Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                         APP KIOSK (Tablet)                          │
│                      http://localhost:8080/app-kiosk                │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ UI: Seleção de bebida → Volume → Pagamento → Dispensa       │  │
│  │ Local: Gera token HMAC + valida EDGE                        │  │
│  │ Storage: localStorage (transações, beverage cache)          │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓↑
                    HTTP POST/GET (Rest API)
                                  ↓↑
┌─────────────────────────────────────────────────────────────────────┐
│                     EDGE SERVER (Raspberry Pi)                      │
│                      http://localhost:5000                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ /edge/authorize    → Valida token + inicia dispensa          │  │
│  │ /edge/status       → Retorna progresso de dispensa           │  │
│  │ /edge/maintenance  → Modo manutenção                         │  │
│  │ GPIO + Sensor      → Controla bomba + mede ml               │  │
│  │ SQLite local       → Histórico de consumos                   │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                  ↓↑
                    HTTP POST/GET (Rest API)
                                  ↓↑
┌─────────────────────────────────────────────────────────────────────┐
│                    SaaS BACKEND (FastAPI)                           │
│                      http://localhost:3001                          │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ /api/v1/beverages      → CRUD de bebidas                    │  │
│  │ /api/v1/machines       → CRUD de máquinas                   │  │
│  │ /api/v1/sales          → Registra vendas                    │  │
│  │ /api/v1/consumptions   → Registra consumos do EDGE          │  │
│  │ /api/v1/health         → Health check                       │  │
│  │ SQLite (bierpass.db)   → Banco de dados                     │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Fluxo de Transação Completo

### 1️⃣ BOOT (Inicialização do App)

```
APP inicia
  ├─ Carrega config.json
  │  └─ machine.id, api_key, hmac_secret, polling_ms, etc
  │
  ├─ Inicializa MockAPIs (testes)
  │
  ├─ GET /api/v1/beverages (SaaS)
  │  └─ Obtém lista de bebidas disponíveis
  │
  ├─ Recuperação de transação pendente
  │  ├─ Se há last_transaction em localStorage
  │  ├─ E synced === false
  │  ├─ POST /api/v1/consumptions (reenvio)
  │  └─ Se OK → Remove do localStorage
  │
  └─ StateMachine → IDLE (pronto para venda)
```

### 2️⃣ SELEÇÃO (Cliente escolhe bebida)

```
Cliente toca em bebida no cardápio
  │
  ├─ Confirmar idade (+18)
  │  ├─ Se NÃO → Volta ao cardápio
  │  └─ Se SIM → Próximo
  │
  ├─ Selecionar volume (100/200/300/400/500ml)
  │  └─ Calcula preço: volume_ml * price_per_ml
  │
  ├─ Selecionar método de pagamento (CREDIT/DEBIT/PIX)
  │  └─ Em produção: integra com maquininha (Cielo/Stone)
  │  └─ Em teste: SDK simula aprovação
  │
  └─ StateMachine → AWAITING_PAYMENT
```

### 3️⃣ PAGAMENTO

```
Usuario seleciona método (ex: CREDIT)
  │
  ├─ PaymentSDK.processPayment(method, amount)
  │  ├─ WAITING_CARD   → Aguarda cartão
  │  ├─ PROCESSING     → Processando transação
  │  ├─ APPROVED       → ✅ Pagamento aprovado
  │  └─ DECLINED       → ❌ Cartão recusado (retry)
  │
  ├─ POST /api/v1/sales (SaaS)
  │  ├─ Registra venda com dados do pagamento
  │  ├─ Retorna: sale_id (UUID)
  │  └─ Status: REGISTERED
  │
  ├─ Gera token HMAC (local)
  │  ├─ Payload: { sale_id, volume_ml, beverage_id, expires }
  │  ├─ Assinatura: HMAC-SHA256(payload, hmac_secret)
  │  ├─ Formato: base64(payload).base64(signature)
  │  └─ Salva em localStorage: current_token
  │
  ├─ POST /edge/authorize (EDGE)
  │  ├─ Envia token HMAC
  │  ├─ EDGE valida: assinatura + expiração + unicidade
  │  ├─ Se válido → Retorna { authorized: true }
  │  └─ Se inválido → Retorna { authorized: false, error: "..." }
  │
  └─ StateMachine → AUTHORIZED → DISPENSING (após 1s)
```

### 4️⃣ DISPENSA

```
StateMachine entra em DISPENSING
  │
  ├─ Polling inicia (GET /edge/status a cada 300ms)
  │  │
  │  ├─ EDGE Status:
  │  │  ├─ status: DISPENSING
  │  │  ├─ volume_dispensed_ml: 50 → 100 → 150 → ... → 300
  │  │  └─ Atualiza a cada poll
  │  │
  │  ├─ UI atualiza progress bar
  │  │  ├─ Percentual: (volume_dispensed / volume_authorized) * 100
  │  │  └─ Exibe: "60% - 180ml"
  │  │
  │  └─ Continua até receber COMPLETED
  │
  ├─ EDGE internamente:
  │  ├─ GPIO pump_on() → Liga bomba
  │  ├─ Sensor lê ml em tempo real
  │  ├─ Simula 20ml/s (mock mode)
  │  ├─ Quando atinge volume_authorized → pump_off()
  │  ├─ Salva em SQLite local
  │  └─ Retorna status: COMPLETED
  │
  ├─ Polling detecta COMPLETED
  │  ├─ Extrai ml_served da resposta
  │  ├─ Reporta consumo ao SaaS (background)
  │  │  POST /api/v1/consumptions
  │  │  {
  │  │    token_id: "eyJ...",
  │  │    machine_id: "7ef8ddb1-...",
  │  │    ml_served: 300,
  │  │    ml_authorized: 300,
  │  │    status: "OK"
  │  │  }
  │  │
  │  └─ StateMachine → FINISHED
  │
  └─ EDGE reseta pulse_count para próxima dispensa
```

### 5️⃣ FINALIZAÇÃO

```
StateMachine em FINISHED
  │
  ├─ UI exibe:
  │  ├─ ✅ Pronto! Aproveite!
  │  ├─ Nome da bebida
  │  ├─ Volume servido (ml_served)
  │  └─ Emoji da bebida
  │
  ├─ Storage salva last_transaction
  │  {
  │    token: "eyJ...",
  │    ml_served: 300,
  │    ml_authorized: 300,
  │    sale_id: "a04c...",
  │    synced: true
  │  }
  │
  ├─ SaaS recebeu e salvou consumption
  │
  ├─ EDGE sincroniza com SaaS (sync_service)
  │  └─ Se SYNC_INTERVAL > 0, tenta sincronizar consumos locais
  │
  └─ Após 5 segundos → StateMachine → IDLE (volta ao cardápio)
```

---

## 🔐 Autenticação & Segurança

### HMAC Token (APP → EDGE)

**Quando é gerado:**
- Após pagamento aprovado, antes de autorizar EDGE

**Estrutura:**
```
Token = base64(Payload) + "." + base64(Signature)

Payload = {
  "sale_id": "a04c2ed0-9c2e-487d-8712-26cadbf90363",
  "volume_ml": 300,
  "beverage_id": "0f7099dc-d353-4d32-8ff2-ef468eb1ee05",
  "beverage_price_per_ml": 0.04,
  "tap_id": 1,
  "expires": "2025-12-23T15:57:51.973Z"
}

Signature = HMAC-SHA256(Payload, hmac_secret)
hmac_secret = "P9llzEpC52LsXIa-te9YSYH7ufzieNswt1aKFX9aNAU"
```

**EDGE Validação:**
1. ✅ Extrai payload e signature do token
2. ✅ Recalcula HMAC-SHA256(payload, hmac_secret)
3. ✅ Compara com signature recebida
4. ✅ Valida expiração (expires > now)
5. ✅ Evita reuso (marca como consumido)

**Em Teste:**
```javascript
// app-kiosk/js/main.js
const token = {
  sale_id: saleId,
  volume_ml: volume,
  beverage_id: beverage.id,
  expires: new Date(Date.now() + 300000).toISOString() // 5 min
};
const signature = HMAC_SHA256(JSON.stringify(token), AppConfig.security.hmac_secret);
const fullToken = base64(token) + "." + base64(signature);
```

---

## 📊 Banco de Dados

### SaaS (bierpass.db)

**SALES**
```sql
id (UUID)
organization_id (UUID)
machine_id (UUID) -- 7ef8ddb1-3a10-4678-8e56-a8aee3184c40
beverage_id (UUID)
volume_ml (int) -- 300
total_value (float) -- 12.00
payment_method (varchar) -- CREDIT, DEBIT, PIX
status (varchar) -- pending, completed, failed
created_at (datetime)
```

**CONSUMPTIONS**
```sql
id (UUID)
sale_id (UUID) -- Foreign key → SALES
machine_id (UUID)
token_id (varchar) -- HMAC token usado
ml_served (int) -- Volume realmente servido
ml_authorized (int) -- Volume autorizado
status (varchar) -- OK, INCOMPLETE, ERROR
created_at (datetime)
```

### EDGE (edge_data.db)

**CONSUMPTIONS (local)**
```sql
id (UUID)
sale_id (UUID)
token_id (varchar)
ml_served (float)
ml_authorized (float)
status (varchar)
pulse_count (int)
created_at (datetime)
synced (boolean) -- Já enviado ao SaaS?
```

---

## 🛠️ Configurações

### app-kiosk/config.json

```json
{
  "app": {
    "name": "BierPass Kiosk",
    "version": "1.1.0"
  },
  "api": {
    "saas_url": "http://localhost:3001",
    "edge_url": "http://localhost:5000",
    "use_mock": false,
    "timeout_ms": 30000
  },
  "machine": {
    "id": "7ef8ddb1-3a10-4678-8e56-a8aee3184c40",
    "code": "M001",
    "api_key": "sk_eKZVLSB56JEajCN70PJ4ResGqxH1B3L3W7CgNrJGIq4"
  },
  "security": {
    "hmac_secret": "P9llzEpC52LsXIa-te9YSYH7ufzieNswt1aKFX9aNAU"
  },
  "ui": {
    "polling_ms": 300,
    "boot_timeout_ms": 2000,
    "idle_timeout_ms": 90000,
    "dispensing_timeout_ms": 60000
  }
}
```

### edge-server/config.py

```python
# Database
DATABASE_URL = "sqlite:///edge_data.db"

# Machine
MACHINE_ID = "7ef8ddb1-3a10-4678-8e56-a8aee3184c40"
API_KEY = "sk_eKZVLSB56JEajCN70PJ4ResGqxH1B3L3W7CgNrJGIq4"
HMAC_SECRET = "P9llzEpC52LsXIa-te9YSYH7ufzieNswt1aKFX9aNAU"

# Sync (0 = desabilitado)
SYNC_INTERVAL = 0  # Em segundos. 0 = não sincroniza (App relata direto ao SaaS)

# GPIO
MOCK_GPIO = True  # Mock mode para testes sem hardware real

# Dispenser
MAX_DISPENSE_TIME = 120  # Timeout máximo
EMPTY_KEG_TIMEOUT = 10   # Se não houver flow por 10s = keg vazio
```

### saas-backend/app/config.py

```python
database_url: str = "sqlite:///./bierpass.db"
debug: bool = True
api_v1_prefix: str = "/api/v1"
cors_origins: list[str] = [
    "http://localhost:3000",
    "http://localhost:8080",
    "file://",
]
```

---

## 🧪 Fluxo de Teste Manual

### Teste 1: Dispensa Simples (200ml)

```
1. Acesse http://localhost:8080/app-kiosk/
2. Clique em "Chopp Pilsen"
3. Confirme "Sim, tenho +18"
4. Selecione 200ml
5. Clique em "Cartão de Crédito"
6. Aguarde pagamento (mock simula após 3s)
7. Observe progress bar: 0% → 100%
8. Tela final: "200ml" deve aparecer
9. Volta ao cardápio após 5s

Esperado:
✅ SaaS salva 1 SALE (volume_ml=200, total_value=8.00)
✅ SaaS salva 1 CONSUMPTION (ml_served≈200, ml_authorized=200)
✅ EDGE registra consumo localmente
✅ Sem erros no console
```

### Teste 2: Multiplos Dispensos Sequenciais

```
1. Dispense 1: 300ml → ✅
2. Imediatamente Dispense 2: 200ml → ✅
3. Imediatamente Dispense 3: 500ml → ✅

Esperado:
✅ Cada volume exibido corretamente (não acumula de dispensa anterior)
✅ 3 SALEs diferentes
✅ 3 CONSUMPTIONs diferentes
✅ Total: R$744.50 (30+8+17.50 = 55.50 em 3 transações diferentes)
```

### Teste 3: Recuperação (Page Refresh)

```
1. Inicie dispense, mude de página ANTES de completar
2. Recarregue o navegador
3. Aplicação detecta transação pendente
4. Reenvio automático do CONSUMPTION ao SaaS
5. localStorage é limpado

Esperado:
✅ Sem erro 422 (ml_served é inteiro)
✅ Consumo registrado com valores corretos
✅ Sem duplicação de transações
```

---

## 🐛 Troubleshooting

| Problema | Causa | Solução |
|----------|-------|---------|
| **HTTP 422 na recuperação** | ml_served é float (2437.8) | Arredondar para inteiro antes de enviar |
| **Volume errado na tela final** | Dados acumulados de dispensa anterior | Resetar _mock_volume_ml e pulse_count após COMPLETED |
| **Polling retorna 978ml para 200ml** | GPIO não foi resetado | EDGE reseta pulse_count após dispensa completar |
| **HMAC 401 Invalid signature** | Segredo não bate entre App e Edge | Verificar security.hmac_secret em ambos os configs |
| **Consumo não é registrado** | POST /api/v1/consumptions falha | Verificar se SaaS está rodando, URL correta, token_id válido |
| **Dados em banco vazio** | SaaS criou DB em diretório errado | SEMPRE iniciar de D:\Front_Bier\ |
| **Dispensa não para no volume exato** | Polling muito lento ou sensor inaccurado | Aumentar frequência de polling (diminuir polling_ms) |
| **"Machine não encontrada" 404** | Machine_id não está no banco | Usar list_machines.py para encontrar UUID real |

---

## 📈 Monitoramento

### Check Banco de Dados
```bash
cd d:\Front_Bier
python check_sales.py
```

### Check Health
```bash
# SaaS
curl http://localhost:3001/api/v1/health

# EDGE (não tem health endpoint ainda, mas pode verificar /edge/status)
curl http://localhost:5000/edge/status
```

### Logs
- **App**: Console do navegador (F12 → Console)
- **EDGE**: Terminal onde rodando (stdout)
- **SaaS**: Terminal do uvicorn (stdout)
- **Banco**: Uso de `check_sales.py` para verificar dados

---

## ✅ Resumo de Componentes

| Componente | Porta | Stack | Função |
|-----------|-------|-------|--------|
| **APP Kiosk** | 8080 | HTML+JS | UI, pagamento, polling |
| **EDGE** | 5000 | Flask | Controle GPIO, dispensa |
| **SaaS** | 3001 | FastAPI | CRUD, registros, API |
| **HTTP Server** | 8080 | Python http.server | Serve arquivos estáticos |

**Fluxo de Dados:**
```
APP(Tablet) ←→ EDGE(Raspberry) ←→ SaaS(Backend)
   8080           5000              3001
```

**Banco de Dados:**
```
SaaS: bierpass.db (D:\Front_Bier\)
EDGE: edge_data.db (D:\Front_Bier\edge-server\)
APP: localStorage (browser)
```
