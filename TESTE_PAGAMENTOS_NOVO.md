# 🧪 TESTE COMPLETO - PIX, DÉBITO E CRÉDITO

**Data:** 2025-12-23  
**Status:** Pronto para execução  
**Ambiente:** Local (EDGE 5000, SaaS 3001, Frontend 8080)

---

## 📋 PRÉ-REQUISITOS

### Servidores Rodando

```bash
# Verificar status
curl http://localhost:5000/edge/health   # EDGE
curl http://localhost:3001/health         # SaaS
curl http://localhost:8080                # Frontend
```

Ou inicie com:
```bash
cd d:\Front_Bier
START_SERVERS.bat
```

### Variáveis de Ambiente (EDGE)

```bash
# .env (se usar)
EDGE_MODE=development
MP_MOCK_PAYMENTS=true
```

---

## ✅ TESTE 1: PIX (Baseline)

### 1.1 - Selecionar Bebida

```
1. Abrir: http://localhost:8080/app-kiosk
2. Clicar: "Chopp Pilsen" (bebida alcoólica)
3. Confirmar: Maioridade → "Sim"
```

**Console Esperado:**
```
[State Machine] Transition: IDLE → CONFIRM_AGE
[State Machine] Transition: CONFIRM_AGE → SELECT_VOLUME
```

---

### 1.2 - Selecionar Volume

```
1. Clicar: "300ml"
2. Aguardar: Transição visual (~1s)
```

**Console Esperado:**
```
[State Machine] Transition: SELECT_VOLUME → SELECT_PAYMENT
```

---

### 1.3 - Selecionar PIX

```
1. Clicar: Botão "PIX 📱"
2. Aguardar: EDGE gera QR Code (~1-2s)
```

**Console Esperado:**
```
[Handler] Pagamento selecionado: PIX
[PaymentSDK] Iniciando transação: PIX - R$ 12.50
POST http://localhost:5000/edge/payments/start
```

**UI Esperado:**
- QR Code PIX visível
- Status: "Aguardando pagamento... (299s)"
- Timeout de 5 minutos

---

### 1.4 - Aprovar Pagamento (Mock)

```
1. Aguardar: 5 segundos (mock aprova automaticamente)
2. Sistema: Detecta aprovação e inicia dispensa
```

**Console Esperado:**
```
[PaymentSDK] Poll: status = pending
[PaymentSDK] Poll: status = pending
[PaymentSDK] Poll: status = approved
✅ Payment APPROVED
[State Machine] Transition: AWAITING_PAYMENT → DISPENSING
```

---

### 1.5 - Dispensação (ML-por-ML)

```
Observar:
- Barra de progresso: 0% → 100% (suave, sem saltos)
- Volume: 0ml → 300ml (incremental)
- Duração: ~30 segundos (300ml @ 10ml/s)
- Final: "Pronto! Aproveite! 🎉"
```

**Console Esperado:**
```
[EDGE] Dispensing started: 300ml
[EDGE] Dispensed: 1ml...
[EDGE] Dispensed: 2ml...
[EDGE] Dispensed: 300ml
[UI] Progress: 1% (1ml/300ml)
[UI] Progress: 2% (2ml/300ml)
...
[UI] Progress: 100% (300ml/300ml)
[State Machine] Transition: DISPENSING → FINISHED
```

---

### 1.6 - Validação Banco de Dados

```bash
python check_sales.py
```

**Esperado:**
```
✅ Sale:
   - payment_method: PIX
   - status: completed ⭐ (IMPORTANTE!)
   - volume_ml: 300
   - total_price: 12.50

✅ Consumption:
   - ml_served: 300
   - status: OK
```

**Checklist Teste 1:**
- [ ] QR Code PIX renderizado
- [ ] 5s depois, status muda para "Aprovado"
- [ ] Dispensação inicia
- [ ] Progresso suave (sem regressão)
- [ ] "Pronto!" exibido
- [ ] `sale.status == "completed"` no BD
- [ ] `consumption.ml_served == 300` no BD

---

## ✅ TESTE 2: DÉBITO

### 2.1 - Selecionar Bebida (Não Alcoólica)

```
1. Clicar: "Água" ou "Refrigerante"
2. Pular: Confirmação de idade (não alcoólica)
3. Clicar: "200ml" (volume menor = teste mais rápido)
```

---

### 2.2 - Selecionar DÉBITO

```
1. Clicar: Botão "Débito 💳"
2. Aguardar: Resposta do EDGE (~1-2s)
```

**Console Esperado:**
```
[Handler] Pagamento selecionado: DEBIT
[PaymentSDK] Iniciando transação: DEBIT - R$ 5.50
POST http://localhost:5000/edge/payments/start
{
  "payment_type": "DEBIT",
  "amount": 5.50,
  "volume_ml": 200
}
```

**EDGE Console Esperado:**
```
✅ Payment started: <id> (DEBIT)
[PaymentService] DEBIT Payment created (MOCK)
```

**UI Esperado:**
- Mensagem: "Insira o cartão no leitor de débito"
- Status: "Aguardando pagamento... (119s)"
- Timeout de 2 minutos

---

### 2.3 - Aprovar Pagamento (Mock)

```
1. Aguardar: 5 segundos
2. Sistema: Aprova e inicia dispensa
```

**Console Esperado:**
```
[PaymentSDK] Poll: status = approved
✅ Payment APPROVED
[State Machine] Transition: AWAITING_PAYMENT → DISPENSING
```

---

### 2.4 - Dispensação

```
Observar:
- Progresso: 0% → 100%
- Volume: 0ml → 200ml
- Duração: ~20 segundos
- Final: "Pronto! Aproveite! 🎉"
```

---

### 2.5 - Validação BD

```bash
python check_sales.py
```

**Esperado:**
```
✅ Sale (novo):
   - payment_method: DEBIT
   - status: completed
   - volume_ml: 200
   - total_price: 5.50

✅ Consumption (novo):
   - ml_served: 200
   - status: OK
```

**Checklist Teste 2:**
- [ ] Instrução de débito exibida
- [ ] Timeout 2min mostrado
- [ ] Pagamento aprovado após 5s
- [ ] Dispensação suave para 200ml
- [ ] `sale.status == "completed"` no BD
- [ ] `consumption.ml_served == 200` no BD

---

## ✅ TESTE 3: CRÉDITO (com Parcelamento)

### 3.1 - Selecionar Bebida

```
1. Clicar: "Chopp Premium" ou "Vinho"
2. Confirmar: Maioridade (se necessário)
3. Clicar: "500ml" (volume maior para mostrar parcelamento)
```

---

### 3.2 - Selecionar CRÉDITO

```
1. Clicar: Botão "Crédito 💳"
2. Aguardar: Resposta do EDGE (~1-2s)
```

**Console Esperado:**
```
[Handler] Pagamento selecionado: CREDIT
[PaymentSDK] Iniciando transação: CREDIT
POST http://localhost:5000/edge/payments/start
{
  "payment_type": "CREDIT",
  "amount": 25.00,
  "volume_ml": 500,
  "installments": 1
}
```

**EDGE Console Esperado:**
```
✅ Payment started: <id> (CREDIT)
[PaymentService] CREDIT Payment created (MOCK)
Instructions: "Aproxime ou insira o cartão de crédito (1x sem juros)"
```

**UI Esperado:**
- Mensagem: "Aproxime ou insira o cartão de crédito"
- Parcelamento: "1x sem juros" (se renderizado)
- Status: "Aguardando pagamento... (119s)"
- Timeout de 2 minutos

---

### 3.3 - Aprovar Pagamento (Mock)

```
1. Aguardar: 5 segundos
2. Sistema: Aprova e inicia dispensa
```

---

### 3.4 - Dispensação

```
Observar:
- Progresso: 0% → 100%
- Volume: 0ml → 500ml
- Duração: ~50 segundos
- Final: "Pronto! Aproveite! 🎉"
```

---

### 3.5 - Validação BD

```bash
python check_sales.py
```

**Esperado:**
```
✅ Sale (novo):
   - payment_method: CREDIT
   - status: completed
   - volume_ml: 500
   - total_price: 25.00

✅ Consumption (novo):
   - ml_served: 500
   - status: OK
```

**Checklist Teste 3:**
- [ ] Instrução de crédito exibida
- [ ] Timeout 2min mostrado
- [ ] Pagamento aprovado após 5s
- [ ] Dispensação suave para 500ml
- [ ] `sale.status == "completed"` no BD
- [ ] `consumption.ml_served == 500` no BD

---

## 📊 RESUMO ESPERADO

| Teste | Tipo | Bebida | Volume | Status | BD |
|-------|------|--------|--------|--------|-----|
| 1 | PIX | Pilsen | 300ml | Completed | ✅ Sale + Consumption |
| 2 | DEBIT | Água | 200ml | Completed | ✅ Sale + Consumption |
| 3 | CREDIT | Premium | 500ml | Completed | ✅ Sale + Consumption |

**Totais ao Final:**
- 3 Sales registradas
- 3 Consumptions registradas
- 1000ml dispensados total

---

## 🔧 TROUBLESHOOTING

### Erro: "Connection refused"

```bash
# EDGE não está rodando
curl http://localhost:5000/edge/health

# Se falhar:
cd d:\Front_Bier\edge-server
python app.py
```

### Erro: "Pagamento stuck em pending"

```bash
# Problema: Cache não foi limpo
# Solução: Reiniciar EDGE
# (Ctrl+C e python app.py novamente)
```

### Problema: "Barra de progresso salta"

```
Verificar:
1. F12 → Console tem logs suaves?
2. EDGE está enviando ml incrementais?
3. Existe erro em "Network" (F12)?
```

### Problema: "Sale.status ainda é pending"

```bash
# Verificar:
# 1. SaaS está recebendo POST /consumptions?
# 2. API Key está correta em config.json?
# 3. EDGE log mostra "Consumption reported to SaaS"?
```

---

## 📝 LOGS PARA COLETAR

### Browser Console (F12)

```javascript
// Copiar toda a saída:
// 1. Abrir F12
// 2. Tab "Console"
// 3. Ler todos os logs [PaymentSDK], [State Machine], [UI]
// 4. Salvar em arquivo .txt
```

### EDGE Server Terminal

```bash
# Logs importantes:
# ✅ Payment started: <id> (PIX|DEBIT|CREDIT)
# [EDGE] Dispensing started: Xml
# [EDGE] Dispensed: Xml...
# ✅ Consumption reported to SaaS
```

### Banco de Dados

```bash
# Antes e depois de cada teste:
python check_sales.py

# Coletar output:
# - Total de sales
# - Total de consumptions
# - Verificar status = "completed"
```

---

## ✨ CONCLUSÃO

Após completar **todos os 3 testes**:

✅ **Funcionalidade:** PIX, Débito, Crédito funcionando  
✅ **Dispensação:** Suave, ml-por-ml, sem regressão  
✅ **Banco de Dados:** Sales com status correto, Consumptions registradas  
✅ **Integração:** EDGE ↔ SaaS sincronizados  

**Próximos Passos:**
1. Testar com dados reais de Mercado Pago (remover mock)
2. Testar webhooks (opcional)
3. Deploy em staging
4. Testes de carga

---

## 🎯 Dica Final

Se em qualquer momento quiser **resetar tudo**:

```bash
# 1. Parar todos os servidores
# 2. Deletar banco de dados
del d:\Front_Bier\bierpass.db
del d:\Front_Bier\edge-server\edge_data.db

# 3. Reiniciar servidores
cd d:\Front_Bier
START_SERVERS.bat

# 4. Reexecutar testes
```

---

**Pronto para começar? Abra http://localhost:8080/app-kiosk e clique em "Chopp Pilsen"! 🍺**
