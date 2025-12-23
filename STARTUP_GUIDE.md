# 🍺 BierPass - Guia de Inicialização Rápida

## ⚠️ Problema Crítico: Banco de Dados em Múltiplos Locais

**SEMPRE inicie todos os servidores do diretório raiz** `D:\Front_Bier\`

Se iniciar de locais diferentes, o FastAPI cria `bierpass.db` em cada local, causando dados fragmentados.

---

## 🚀 Inicialização Rápida (3 Terminais)

### Terminal 1: SaaS Backend (Porta 3001)
```powershell
cd D:\Front_Bier
.\.venv\Scripts\python.exe -m uvicorn saas-backend.app.main:app --host 0.0.0.0 --port 3001 --reload
```
✅ Aguarde: `INFO:     Application startup complete`  
✅ Teste: http://localhost:3001/api/v1/health

### Terminal 2: EDGE Server (Porta 5000)
```powershell
cd D:\Front_Bier
.\.venv\Scripts\python.exe edge-server/app.py
```
✅ Aguarde: `✅ EDGE Server ready on 0.0.0.0:5000`

### Terminal 3: HTTP Server (Porta 8080)
```powershell
cd D:\Front_Bier
.\.venv\Scripts\python.exe -m http.server 8080 --directory .
```
✅ Aguarde: `Serving HTTP on 0.0.0.0 port 8080`

---

## 🎯 Acessar a Aplicação

**App Kiosk:** http://localhost:8080/app-kiosk/

**APIs:**
- SaaS Swagger: http://localhost:3001/docs
- EDGE Status: http://localhost:5000/edge/status

---

## ✅ Checklist de Inicialização

- [ ] 3 terminais abertos, todos em `D:\Front_Bier\`
- [ ] SaaS Backend rodando na porta 3001
- [ ] EDGE Server rodando na porta 5000
- [ ] HTTP Server rodando na porta 8080
- [ ] Banco de dados em `D:\Front_Bier\bierpass.db` (não em `saas-backend/`)
- [ ] App carrega em http://localhost:8080/app-kiosk/
- [ ] Sem erros de conexão no console (F12 → Console)

---

## 🔍 Verificar Dados no Banco

```powershell
cd D:\Front_Bier
python check_sales.py
```

Mostra:
- Últimas 5 vendas
- Últimos 5 consumos
- Total de transações
- Total vendido

---

## 🧪 Teste Rápido

1. Acesse http://localhost:8080/app-kiosk/
2. Selecione "Chopp Pilsen"
3. Confirme idade
4. Escolha 300ml
5. Pague com "Cartão de Crédito"
6. Aguarde pagamento (3s simulado)
7. Observe barra de progresso
8. Veja resultado: "300ml" ✅

**Esperado no banco:**
```
Vendas: 1
Consumos: 1
Volume: 300ml
Valor: R$ 12.00
```

---

## 📋 Configurações Importantes

### Machine ID
- **UUID:** `7ef8ddb1-3a10-4678-8e56-a8aee3184c40`
- **Código:** `M001`
- **Local:** app-kiosk/config.json + edge-server/config.py

### HMAC Secret (Autenticação)
- **Valor:** `P9llzEpC52LsXIa-te9YSYH7ufzieNswt1aKFX9aNAU`
- **Local:** app-kiosk/config.json + edge-server/config.py
- **⚠️ DEVE ser idêntico em ambos os locais**

### Endpoints
- **SaaS:** http://localhost:3001/api/v1/
- **EDGE:** http://localhost:5000/edge/
- **App:** http://localhost:8080/app-kiosk/

---

## 🐛 Problemas Comuns

| Problema | Solução |
|----------|---------|
| **Connection refused na porta 3001** | SaaS não está rodando. Verifique Terminal 1 |
| **Connection refused na porta 5000** | EDGE não está rodando. Verifique Terminal 2 |
| **Banco vazio após venda** | Verificar se iniciou de `D:\Front_Bier\` (não outro local) |
| **HMAC 401 error** | Verificar se hmac_secret é idêntico em config.json e config.py |
| **Volume errado na tela final** | Reiniciar EDGE (Terminal 2) para limpar estado |
| **Erro 422 no recovery** | ml_served não é inteiro. (Já foi fixado no código) |

---

## 📚 Documentação Completa

Veja [FLUXO_COMPLETO.md](FLUXO_COMPLETO.md) para:
- Arquitetura detalhada
- Fluxo de transação passo a passo
- Estrutura de banco de dados
- Segurança HMAC
- Troubleshooting avançado

---

## 🎬 Script de Inicialização Automática (Windows)

Crie arquivo `start-all.bat` em `D:\Front_Bier\`:

```batch
@echo off
echo ====================================
echo Iniciando BierPass (3 Servidores)
echo ====================================

start "SaaS Backend (3001)" cmd /k "cd D:\Front_Bier && .\.venv\Scripts\python.exe -m uvicorn saas-backend.app.main:app --host 0.0.0.0 --port 3001 --reload"

timeout /t 2 /nobreak

start "EDGE Server (5000)" cmd /k "cd D:\Front_Bier && .\.venv\Scripts\python.exe edge-server/app.py"

timeout /t 2 /nobreak

start "HTTP Server (8080)" cmd /k "cd D:\Front_Bier && .\.venv\Scripts\python.exe -m http.server 8080 --directory ."

echo.
echo ====================================
echo Todos os servidores iniciados!
echo ====================================
echo.
echo Acesse: http://localhost:8080/app-kiosk/
echo.
pause
```

Depois basta clicar duplo em `start-all.bat`.

---

## 📊 Stack da Aplicação

```
┌─────────────────────────────────────────┐
│     APP KIOSK (Frontend)                │
│  HTML5 + CSS3 + JavaScript              │
│  Rodando em: http://localhost:8080      │
└─────────────────────────────────────────┘
              ↓↑ HTTP
┌─────────────────────────────────────────┐
│     EDGE SERVER (Middleware)            │
│  Python Flask + GPIO                    │
│  Rodando em: http://localhost:5000      │
│  Banco: edge_data.db (SQLite)           │
└─────────────────────────────────────────┘
              ↓↑ HTTP
┌─────────────────────────────────────────┐
│     SaaS BACKEND (API)                  │
│  Python FastAPI + SQLAlchemy            │
│  Rodando em: http://localhost:3001      │
│  Banco: bierpass.db (SQLite)            │
└─────────────────────────────────────────┘
```

---

## ✨ Recursos Principais

✅ Fluxo de pagamento integrado (SDK Maquininha)  
✅ Geração local de token HMAC  
✅ Validação de token no EDGE  
✅ Polling de status em tempo real  
✅ Controle de dispensa com precisão  
✅ Recuperação automática de transações pendentes  
✅ Sincronização com SaaS  
✅ Funcionamento offline (EDGE completa dispensa mesmo sem internet)  

---

## 📞 Suporte

Se encontrar problemas:

1. **Verifique os 3 servidores estão rodando** (Ctrl+Shift+Esc → procure `python`)
2. **Verifique o console do App** (F12 → Console)
3. **Verifique os logs dos servidores** (terminais)
4. **Verifique o banco de dados** (`python check_sales.py`)
5. **Leia [FLUXO_COMPLETO.md](FLUXO_COMPLETO.md)** para troubleshooting avançado



# Verificar se EDGE está respondendo
curl http://localhost:5000/edge/status

# Verificar se bebidas carregam
curl http://localhost:3001/api/v1/beverages
```

## 🔧 Troubleshooting

### Problema: API retorna bebidas vazias
**Solução**: Verifique se há dois arquivos `bierpass.db`:
```bash
cd D:\Front_Bier
Get-ChildItem -Recurse -Name "bierpass.db"
```
- Se houver em dois lugares, **delete o em `D:\Front_Bier\bierpass.db`**
- Execute seed novamente: `cd saas-backend && .\.venv\Scripts\python.exe seed.py`

### Problema: Porta em uso (Address already in use)
```bash
# Encontrar processo na porta (ex: 3001)
netstat -ano | findstr :3001

# Matar processo (substitua PID)
taskkill /PID <PID> /F
```

### Problema: StateMachine não definido
Certifique-se que `state-machine.js` foi restaurado corretamente após o undo:
```bash
# Verificar arquivo
Get-Content app-kiosk/js/state-machine.js | Measure-Object -Line
# Deve mostrar ~200 linhas, não 0
```

## 📁 Estrutura de Diretórios

```
D:\Front_Bier\
├── bierpass.db                 ← IMPORTANTE: Banco aqui
├── app-kiosk/
│   ├── index.html
│   ├── config.json
│   └── js/
│       ├── state-machine.js
│       ├── main.js
│       └── ...
├── saas-backend/
│   ├── app/
│   ├── seed.py
│   └── app.py
├── edge-server/
│   └── app.py
└── .venv/
```

## 🎯 Fluxo Correto de Inicialização

```
1. cd D:\Front_Bier          ← Sempre aqui!
2. Terminal 1: uvicorn (SaaS)
3. Terminal 2: edge-server
4. Terminal 3: seed.py (uma vez)
5. Terminal 4: http.server
6. Browser: http://localhost:8080/app-kiosk/
```

## 📝 Notas Importantes

- **NUNCA** execute uvicorn de dentro de `saas-backend/`
- **SEMPRE** use `cd D:\Front_Bier` antes de iniciar os servidores
- Se receber erro de banco vazio, copie: `cp saas-backend\bierpass.db bierpass.db`
- O arquivo `bierpass.db` será criado automaticamente na primeira execução se não existir
