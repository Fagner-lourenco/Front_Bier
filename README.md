# 🍺 BierPass - Distribuidor Inteligente de Bebidas

**Status:** ✅ MVP Funcional (Testes em andamento)  
**Data da Última Atualização:** 23 de dezembro de 2025

---

## 📚 Documentação Disponível

### 🚀 Para Começar Agora
- **[STARTUP_GUIDE.md](STARTUP_GUIDE.md)** ← **COMECE AQUI!**
  - Inicialização rápida dos 3 servidores
  - Checklist de setup
  - Teste rápido em 5 minutos
  - Troubleshooting dos problemas comuns

### 🔍 Entender o Sistema
- **[FLUXO_COMPLETO.md](FLUXO_COMPLETO.md)**
  - Arquitetura completa da aplicação
  - Fluxo de transação passo a passo
  - Estrutura de banco de dados
  - Autenticação e segurança (HMAC)
  - Guia completo de testes
  - Troubleshooting avançado

### 📋 Documentação Original
- **[Projeto.md](Projeto.md)** - Especificação do projeto e princípios
- **[FIX_404_SUMMARY.md](FIX_404_SUMMARY.md)** - Histórico de fixes
- **[IMPLEMENTATION_COMPLETE.md](app-kiosk/IMPLEMENTATION_COMPLETE.md)** - Status do App Kiosk

---

## ⚡ Quick Start (60 segundos)

### Abrir 3 Terminais e Executar:

**Terminal 1 - SaaS Backend (Porta 3001)**
```powershell
cd D:\Front_Bier
.\.venv\Scripts\python.exe -m uvicorn saas-backend.app.main:app --host 0.0.0.0 --port 3001 --reload
```

**Terminal 2 - EDGE Server (Porta 5000)**
```powershell
cd D:\Front_Bier
.\.venv\Scripts\python.exe edge-server/app.py
```

**Terminal 3 - HTTP Server (Porta 8080)**
```powershell
cd D:\Front_Bier
.\.venv\Scripts\python.exe -m http.server 8080 --directory .
```

### Acessar
```
http://localhost:8080/app-kiosk/
```

---

## 🎯 Fluxo de Funcionamento

```
1. CLIENTE SELECIONA BEBIDA
   ├─ Escolhe volume
   ├─ Confirma idade (+18)
   └─ Seleciona pagamento

2. PAGAMENTO
   ├─ SDK Maquininha processa
   ├─ POST /api/v1/sales (SaaS registra venda)
   └─ Gera token HMAC local

3. AUTORIZAÇÃO NO EDGE
   ├─ POST /edge/authorize (envia token)
   ├─ EDGE valida assinatura HMAC
   └─ Inicia dispensa se válido

4. DISPENSAÇÃO
   ├─ GET /edge/status (polling a cada 300ms)
   ├─ UI mostra progresso (0% → 100%)
   └─ EDGE pausa bomba ao atingir volume exato

5. FINALIZAÇÃO
   ├─ Mostra volume servido
   ├─ POST /api/v1/consumptions (registra consumo)
   ├─ Volta ao cardápio após 5s
   └─ Storage: last_transaction armazenada para recovery
```

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────┐
│   APP KIOSK (Tablet/Web)        │
│   html + css + javascript       │
│   http://localhost:8080         │
└─────────────┬───────────────────┘
              │ HTTP API
              ↓↑
┌─────────────────────────────────┐
│   EDGE SERVER (Raspberry Pi)    │
│   Flask + GPIO + Sensor         │
│   http://localhost:5000         │
├─────────────────────────────────┤
│ • /edge/authorize → Inicia      │
│ • /edge/status    → Progresso   │
│ • GPIO pump       → Liga bomba  │
│ • Sensor          → Mede ml     │
│ • SQLite local    → Histórico   │
└─────────────┬───────────────────┘
              │ HTTP API
              ↓↑
┌─────────────────────────────────┐
│   SaaS BACKEND (FastAPI)        │
│   Python + SQLAlchemy           │
│   http://localhost:3001         │
├─────────────────────────────────┤
│ • CRUD Bebidas                  │
│ • CRUD Máquinas                 │
│ • Registra Vendas               │
│ • Registra Consumos             │
│ • Dashboard                     │
│ • SQLite (bierpass.db)          │
└─────────────────────────────────┘
```

---

## 📊 Status da Implementação

| Componente | Status | Observações |
|-----------|--------|-------------|
| **APP Kiosk** | ✅ Funcional | UI completa, pagamento mock, polling, recovery |
| **EDGE Server** | ✅ Funcional | Autorização, dispensa, GPIO mock, sincronização |
| **SaaS Backend** | ✅ Funcional | APIs CRUD, autenticação, banco de dados |
| **HMAC Auth** | ✅ Implementado | Token gerado localmente, validado no EDGE |
| **Polling** | ✅ Implementado | 300ms, atualiza progress em tempo real |
| **Recovery** | ✅ Implementado | Transações pendentes reenviadas automaticamente |
| **Volume Exato** | ✅ Corrigido | Resetando pulse_count após dispensa |
| **Banco de Dados** | ✅ Sincronizado | 44 vendas, 10 consumos registrados |

---

## 🐛 Bugs Fixos Recentemente

### Acumulação de Volume em Dispensas Sequenciais
- **Problema:** Dispensa 1 (300ml) + Dispensa 2 (200ml) = resultava em 978ml
- **Causa:** GPIO pulse_count não era resetado entre dispensas
- **Solução:** Resetar pulse_count imediatamente após dispensa completar

### Erro 422 na Recuperação
- **Problema:** `ml_served: 2437.8` (float com decimal)
- **Causa:** FastAPI espera inteiro, não float
- **Solução:** `Math.round()` antes de enviar ao SaaS

### Dados em Banco Vazio
- **Problema:** SaaS criava banco em local diferente
- **Causa:** Iniciar uvicorn de diretórios diferentes
- **Solução:** **SEMPRE iniciar de `D:\Front_Bier\`**

### HMAC 401 Invalid Signature
- **Problema:** Token rejeitado no EDGE
- **Causa:** hmac_secret diferente entre App e Edge
- **Solução:** Sincronizar `P9llzEpC52LsXIa-te9YSYH7ufzieNswt1aKFX9aNAU` em ambos

---

## 🔐 Configurações Críticas

### Machine ID (UUID)
```
7ef8ddb1-3a10-4678-8e56-a8aee3184c40
```
Local: `app-kiosk/config.json` + `edge-server/config.py`

### HMAC Secret
```
P9llzEpC52LsXIa-te9YSYH7ufzieNswt1aKFX9aNAU
```
⚠️ **DEVE ser idêntico em ambos os locais**

### API Key
```
sk_eKZVLSB56JEajCN70PJ4ResGqxH1B3L3W7CgNrJGIq4
```

---

## 📈 Dados Atuais no Banco

```
Total de Vendas:       44
Total de Consumos:     10
Valor Total Vendido:   R$ 754.50
```

**Últimas Transações:**
- 200ml → R$ 8.00 ✅
- 500ml → R$ 30.00 ✅
- 300ml → R$ 12.00 ✅

**Verificar com:**
```powershell
cd D:\Front_Bier
python check_sales.py
```

---

## 🧪 Próximos Testes

- [ ] Múltiplos clientes simultâneos
- [ ] Falha de conexão durante dispensa
- [ ] Timeout de operação
- [ ] Validação de HMAC com payload inválido
- [ ] Teste em hardware real (Raspberry + GPIO)
- [ ] Integração com maquininha real (Cielo/Stone)
- [ ] Performance com 1000+ transações

---

## 📱 Endpoints Principais

### SaaS Backend (http://localhost:3001)
```
GET    /api/v1/health                 - Health check
GET    /api/v1/beverages              - Lista bebidas
POST   /api/v1/sales                  - Registra venda
POST   /api/v1/consumptions           - Registra consumo
GET    /api/v1/machines/{id}          - Detalhes máquina
POST   /docs                          - Swagger UI
```

### EDGE Server (http://localhost:5000)
```
POST   /edge/authorize                - Autoriza dispensa
GET    /edge/status                   - Status da máquina
POST   /edge/maintenance              - Modo manutenção
```

### App Kiosk (http://localhost:8080)
```
/app-kiosk/                           - Aplicação principal
/app-kiosk/index.html                 - Página inicial
/app-kiosk/config.json                - Configuração
```

---

## 🛠️ Ferramentas Úteis

### Verificar Banco de Dados
```powershell
python check_sales.py
python check_db.py
python list_machines.py
```

### Testar APIs
```bash
# SaaS Health
curl http://localhost:3001/api/v1/health

# EDGE Status
curl http://localhost:5000/edge/status

# Swagger SaaS
http://localhost:3001/docs
```

### Limpar localStorage (App)
```javascript
localStorage.removeItem('last_transaction');
localStorage.removeItem('current_token');
```

---

## 📞 Suporte & Troubleshooting

### Passo 1: Verifique os Servidores
```powershell
Get-Process | Where-Object {$_.Name -match 'python'}
```
Deve haver **3 processos python** rodando.

### Passo 2: Verifique o Console (F12)
Erros de conexão aparecerão no **F12 → Console**

### Passo 3: Consulte os Logs
- **SaaS:** Procure por `ERROR` no terminal do uvicorn
- **EDGE:** Procure por `❌` no terminal do app.py
- **App:** Procure por `[Error]` no console (F12)

### Passo 4: Verifique o Banco
```powershell
python check_sales.py
```
Dados em branco? Verifique se iniciou de `D:\Front_Bier\`

### Passo 5: Leia a Documentação
- [FLUXO_COMPLETO.md](FLUXO_COMPLETO.md) → Troubleshooting avançado
- [Projeto.md](Projeto.md) → Arquitetura e princípios

---

## 📝 Notas de Desenvolvimento

### Importante para Testes Futuros
1. ✅ **SEMPRE iniciar de `D:\Front_Bier\`** (problema de múltiplos bancos)
2. ✅ **Hmac_secret DEVE ser idêntico** em app-kiosk/config.json e edge-server/config.py
3. ✅ **Machine ID é UUID**, não código (ex: `7ef8ddb1-...`, não `M001`)
4. ✅ **Polling a 300ms** → mudar `config.json` se precisar mais frequente
5. ✅ **Consumos com ml_served=0** são intencionais (resetou pulse_count)

### Para Produção
- [ ] Usar banco PostgreSQL (não SQLite)
- [ ] Usar Https (certificados SSL)
- [ ] Implementar autenticação real (JWT)
- [ ] Integrar maquininha real
- [ ] Implementar GPS da máquina
- [ ] Dashboard de vendas
- [ ] Alertas de manutenção
- [ ] Rate limiting nas APIs

---

## 👥 Contribuidores

Desenvolvido para BierPass - Dezembro 2025

---

**Última Atualização:** 23 de dezembro de 2025  
**Versão:** 1.1.0
