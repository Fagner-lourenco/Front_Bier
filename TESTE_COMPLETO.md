# 🧪 Guia de Testes - BierPass

**Objetivo:** Validar funcionamento completo da aplicação antes de deployment  
**Duração Estimada:** 30 minutos  
**Data:** 23 de dezembro de 2025

---

## 📋 Pré-Requisitos

- [ ] 3 servidores rodando (SaaS, EDGE, HTTP)
- [ ] App acessível em http://localhost:8080/app-kiosk/
- [ ] Console aberto (F12 → Console)
- [ ] Terminal para verificar banco de dados
- [ ] Familiaridade com o fluxo (leia [FLUXO_COMPLETO.md](FLUXO_COMPLETO.md))

---

## 🟢 Teste 1: Dispensa Simples (200ml)

### Passos

1. **Abrir App**
   - Acesse http://localhost:8080/app-kiosk/
   - Aguarde "🚀 Aplicação inicializada com sucesso!"

2. **Selecionar Bebida**
   - Clique em "Chopp Pilsen"
   - Console: `[Handler] Beverage selecionado: 0f7099dc-...`

3. **Confirmar Idade**
   - Clique "✅ Sim, tenho +18"
   - Console: `[Handler] Idade confirmada: true`

4. **Selecionar Volume**
   - Clique em "200ml"
   - Console: `[Handler] Volume selecionado: 200`

5. **Selecionar Pagamento**
   - Clique em "Cartão de Crédito"
   - Aguarde 3 segundos (simulação)
   - Console: `[PaymentSDK] Status: PROCESSING` → `APPROVED`

6. **Acompanhar Dispensa**
   - Barra de progresso: 0% → 100%
   - Console: `[UI] Progress atualizado: 20% 40ml` → `100% 200ml`

7. **Verificar Resultado**
   - Tela exibe: "✅ Pronto! Aproveite! 200ml"
   - Console: `[App] Consumo reportado com sucesso`

8. **Voltar ao Menu**
   - Após 5 segundos → "Estado: IDLE"
   - Cardápio aparece novamente

### ✅ Esperado no Banco de Dados

```powershell
python check_sales.py

VENDAS:
- 1 nova venda de 200ml
- Valor: R$ 8.00
- Status: pending

CONSUMOS:
- 1 novo consumo
- ml_served: 200
- ml_authorized: 200
- Status: OK
```

### 📊 Verificação de Logs

**SaaS Terminal:**
```
INFO:     POST /api/v1/sales
INFO:     POST /api/v1/consumptions
```

**EDGE Terminal:**
```
👍 Pump ON
🍺 Dispensing 200ml for sale ...
  → 10% (20ml / 200ml)
  → 20% (40ml / 200ml)
  ...
  → 100% (200ml / 200ml)
✅ Mock dispensing complete: 200ml
🛑 Pump OFF
```

---

## 🟢 Teste 2: Múltiplas Dispensas Sequenciais

### Objetivo
Verificar que volumes não se acumulam entre dispensas

### Passos

1. **Dispensa 1: 300ml**
   - Selecione Chopp Pilsen → 300ml → Crédito
   - Aguarde conclusão
   - ✅ Tela final: "300ml"

2. **Imediatamente → Dispensa 2: 200ml**
   - (Não aguarde volltar ao IDLE, volta automático)
   - Selecione Chopp Pilsen → 200ml → Crédito
   - Aguarde conclusão
   - ✅ Tela final: "200ml" (NÃO 500ml!)

3. **Imediatamente → Dispensa 3: 500ml**
   - Selecione Chopp Pilsen → 500ml → Crédito
   - Aguarde conclusão
   - ✅ Tela final: "500ml" (NÃO 1000ml!)

### ✅ Esperado no Banco de Dados

```powershell
python check_sales.py

VENDAS:
- 3 vendas novas
- Valores: R$ 12 + R$ 8 + R$ 30 = R$ 50

CONSUMOS:
- 3 consumos novos
- ml_served: 300, 200, 500 (CADA UM EXATO!)
- Sem acumulação
```

### 🐛 Se Falhar

- **Volume errado?** → EDGE não foi reiniciado após última dispensa
- **Solução:** Verifique se pulse_count foi resetado (logs EDGE)

---

## 🟢 Teste 3: Recuperação (Page Refresh)

### Objetivo
Verificar que transações incompletas são recuperadas

### Passos

1. **Iniciar Dispensa**
   - Selecione Chopp Pilsen → 300ml → Crédito
   - Aguarde pagamento (fase AUTHORIZED)

2. **Recarregar Página**
   - Durante dispensa (não espere completar)
   - Pressione F5 (refresh)
   - App recarrega

3. **Verificar Recuperação**
   - App tenta reenviar transação pendente
   - Console: `[Recovery] Reenviando transação pendente`
   - Aguarde resposta: `[Recovery] Transação reenviada com sucesso!`

4. **Verificar Banco**
   ```powershell
   python check_sales.py
   
   CONSUMOS:
   - Deve ter consumo registrado (não perdeu)
   - Status: OK
   - Sem duplicação
   ```

### ✅ Esperado

- ✅ Transação recuperada automaticamente
- ✅ Nenhum erro 422 (ml_served é inteiro)
- ✅ Consumo registrado uma única vez

### 🐛 Se Falhar

- **Erro 422?** → ml_served não foi arredondado (verifique código)
- **Transação duplicada?** → Remova localStorage com recovery antigo
- **Transação perdida?** → localStorage foi limpo incorretamente

---

## 🟢 Teste 4: Validação de HMAC

### Objetivo
Verificar que token inválido é rejeitado pelo EDGE

### Passos

1. **Interceptar Token (Browser Dev Tools)**
   - Abra F12 → Network
   - Faça uma dispensa normal
   - Procure POST para `/edge/authorize`
   - Copie o token da request

2. **Modificar Token**
   - Abra Console (F12)
   - Execute:
     ```javascript
     // Modifique 1 caractere do token
     const malformedToken = "eyJzYWxlX2lkIjoiZTA5ZGI5ZGYtZmEzZS00ZTA..."
       .replace("Zm9vYmF", "Zm9vYmI");  // Corromper assinatura
     ```

3. **Tentar Autorizar com Token Inválido**
   - Execute no console:
     ```javascript
     fetch('http://localhost:5000/edge/authorize', {
       method: 'POST',
       headers: { 'Content-Type': 'application/json' },
       body: JSON.stringify({ token: malformedToken })
     }).then(r => r.json()).then(console.log)
     ```

4. **Verificar Resposta**
   - ✅ DEVE retornar: `{ "authorized": false, "error": "Invalid signature" }`
   - ❌ NÃO deve aceitar token inválido

### 📊 Resultado Esperado

```json
{
  "authorized": false,
  "error": "Invalid signature",
  "valid_signature": false
}
```

---

## 🟡 Teste 5: Stress Test (Banco de Dados)

### Objetivo
Verificar que banco cresce corretamente com múltiplas transações

### Passos

1. **Executar 10 Dispensas**
   - 10 vezes: Pilsen 300ml → R$12
   - Cada uma completa normalmente

2. **Verificar Banco**
   ```powershell
   python check_sales.py
   
   Esperado:
   - +10 vendas
   - +10 consumos
   - +R$120 de valor
   ```

3. **Verificar Performance**
   - App responde rápido? ✅
   - Tela final carrega em < 2s? ✅
   - Nenhum erro? ✅

### 🎯 Métricas

| Métrica | Esperado |
|---------|----------|
| Tempo dispensa (300ml) | 15s |
| Tempo UI atualizar | < 500ms |
| Tempo recuperação | < 5s |
| Tamanho banco | < 1MB |
| Número transações | 10+ |

---

## 🔴 Teste 6: Tratamento de Erros

### 6.1 - Rejeição de Pagamento

**Passos:**
1. Clique em "Cartão de Crédito"
2. Aguarde PaymentSDK
3. Simule rejeição no código (ou aguarde que falhe naturalmente)

**Esperado:**
```
❌ Pagamento recusado
[DECLINED]
Voltar e tentar novamente
```

### 6.2 - Perda de Conexão EDGE

**Passos:**
1. Pare o EDGE server (Ctrl+C no Terminal 2)
2. Inicie uma dispensa
3. Observe erro de conexão

**Esperado:**
```
❌ EDGE não está respondendo
[Error] Connection refused
Mensagem de erro na UI
```

### 6.3 - Timeout de Dispensa

**Passos:**
1. Aguarde > 60 segundos na tela DISPENSING
2. StateMachine deve timeout

**Esperado:**
```
⚠️ Timeout de dispensa
[StateMachine] Timeout de 60000ms configurado para DISPENSING
Voltar ao IDLE
```

---

## 📊 Checklist Final

Após completar todos os testes:

- [ ] Teste 1 (Simples): Passou ✅
- [ ] Teste 2 (Múltiplos): Passou ✅
- [ ] Teste 3 (Recovery): Passou ✅
- [ ] Teste 4 (HMAC): Passou ✅
- [ ] Teste 5 (Stress): Passou ✅
- [ ] Teste 6 (Erros): Passou ✅
- [ ] Console sem erros críticos
- [ ] Banco com dados esperados
- [ ] Tempos de resposta aceitáveis
- [ ] Documentação atualizada

---

## 📈 Resultado Final

```powershell
python check_sales.py

Resultado Esperado:
═════════════════════════════════════════
Total de Vendas:     50+
Total de Consumos:   50+
Valor Total Vendido: R$ 2000+
═════════════════════════════════════════
```

---

## 🎉 Pronto para Produção?

Se todos os testes passarem:

✅ **Arquitetura funcional**  
✅ **API respondendo**  
✅ **Banco de dados persistindo**  
✅ **Fluxo de pagamento OK**  
✅ **Recovery funcionando**  
✅ **Segurança HMAC validada**  

### Próximos Passos

1. [ ] Testes com hardware real (Raspberry + GPIO)
2. [ ] Integração com maquininha real (Cielo/Stone)
3. [ ] Teste de segurança (OWASP Top 10)
4. [ ] Performance test com 1000+ transações
5. [ ] Deploy em produção (VPS/Cloud)
6. [ ] Monitoramento e alertas
7. [ ] Dashboard de vendas

---

## 📞 Suporte nos Testes

Se algum teste falhar:

1. **Leia a mensagem de erro** (console + terminais)
2. **Consulte [FLUXO_COMPLETO.md](FLUXO_COMPLETO.md)** → Troubleshooting
3. **Verifique banco de dados:** `python check_sales.py`
4. **Reinicie servidores:** Ctrl+C em cada terminal, inicie novamente
5. **Limpe localStorage:** Abra console e execute:
   ```javascript
   localStorage.clear();
   location.reload();
   ```

---

**Data de Conclusão dos Testes:** _______________  
**Resultado:** _______________  
**Assinado por:** _______________  

---

*Documento criado: 23 de dezembro de 2025*
