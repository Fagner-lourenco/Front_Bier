# 🔧 CORREÇÃO DO ERRO 404 NO SYNC + HMAC INVALID SIGNATURE

## ❌ Problemas Identificados

### 1️⃣ HTTP 404 no Sync
- Edge tentava sincronizar consumo com SaaS
- HTTP 404: "Machine/Sale not found"
- **Causa**: Machine ID estava errado nos configs

### 2️⃣ HTTP 401 Invalid Signature
- App enviava token HMAC para Edge
- HTTP 401: "Invalid signature"
- **Causa**: HMAC secret diferente entre App e Edge

## ✅ Solução Implementada

### 1️⃣ Máquina Cadastrada no SaaS
```
ID real: 7ef8ddb1-3a10-4678-8e56-a8aee3184c40
Code: M001
API Key: sk_eKZVLSB56JEajCN70PJ4ResGqxH1B3L3W7CgNrJGIq4
HMAC Secret: P9llzEpC52LsXIa-te9YSYH7ufzieNswt1aKFX9aNAU
```

### 2️⃣ Configs Atualizados

**app-kiosk/config.json:**
- ✅ machine.id atualizado
- ✅ machine.api_key atualizado
- ✅ **security.hmac_secret atualizado** (match com Edge)

**edge-server/config.py:**
- ✅ HMAC_SECRET atualizado (match com SaaS)
- ✅ MACHINE_ID atualizado
- ✅ API_KEY atualizado
- ✅ **SYNC_INTERVAL = 0** (desabilitado)

**edge-server/sync_service.py:**
- ✅ Não inicia thread se SYNC_INTERVAL = 0

### 3️⃣ Fluxo Final

```
1. App paga → registra Sale → recebe sale_id
2. App gera token HMAC com sale_id
3. Edge valida token e dispensa
4. Edge salva consumo localmente
5. **App reporta** consumo ao SaaS ✅
6. Edge NÃO tenta sync (desabilitado) ✅
```

## 🧪 Próximos Passos

1. Reiniciar Edge Server
2. Reiniciar SaaS Backend
3. Testar dispense completo:
   - Pagamento → Sale
   - Dispense → Edge
   - Report → SaaS
   
## 📝 Arquivos Modificados

- ✅ app-kiosk/config.json
- ✅ edge-server/config.py
- ✅ edge-server/sync_service.py
- ✅ check_machine.py (novo)
- ✅ list_machines.py (novo)
