# 🍺 BierPass - Guia de Inicialização

## ⚠️ Problema Conhecido: Banco de Dados em Múltiplos Locais

Durante o desenvolvimento, descobrimos um problema crítico: o FastAPI cria o arquivo `bierpass.db` no diretório **de onde é executado**, não no diretório do código-fonte.

### O Problema
- Se iniciar uvicorn de `D:\Front_Bier\`, o banco fica em `D:\Front_Bier\bierpass.db`
- Se iniciar de `D:\Front_Bier\saas-backend\`, o banco fica em `D:\Front_Bier\saas-backend\bierpass.db`
- Isso causa confusão porque a API carrega dados de um banco vazio enquanto os dados estão no outro

### A Solução

**SEMPRE inicie todos os servidores do diretório raiz** (`D:\Front_Bier\`):

```bash
# Terminal 1: SaaS Backend (porta 3001)
cd D:\Front_Bier
.\.venv\Scripts\python.exe -m uvicorn saas-backend.app.main:app --host 0.0.0.0 --port 3001 --reload

# Terminal 2: EDGE Server (porta 5000)
cd D:\Front_Bier
.\.venv\Scripts\python.exe edge-server/app.py

# Terminal 3: HTTP Server (porta 8080)
cd D:\Front_Bier
.\.venv\Scripts\python.exe -m http.server 8080 --directory .
```

### Inicialização Rápida (Script)

Crie um arquivo `start-all.bat` na raiz:

```batch
@echo off
echo Iniciando BierPass em 3 terminais...

start "SaaS Backend" cmd /k "cd D:\Front_Bier && D:\.venv\Scripts\python.exe -m uvicorn saas-backend.app.main:app --host 0.0.0.0 --port 3001 --reload"

start "EDGE Server" cmd /k "cd D:\Front_Bier && D:\.venv\Scripts\python.exe edge-server/app.py"

start "HTTP Server" cmd /k "cd D:\Front_Bier && D:\.venv\Scripts\python.exe -m http.server 8080 --directory ."

echo Todos os servidores iniciados!
echo.
echo SaaS Backend:  http://localhost:3001
echo EDGE Server:   http://localhost:5000
echo App Kiosk:     http://localhost:8080/app-kiosk/
```

## 📋 Checklist de Inicialização

1. **Certifique-se que está em `D:\Front_Bier`**
   ```bash
   cd D:\Front_Bier
   ```

2. **Ative o ambiente virtual** (se necessário)
   ```bash
   .\.venv\Scripts\Activate.ps1
   ```

3. **Inicie o SaaS Backend** (Terminal 1)
   ```bash
   .\.venv\Scripts\python.exe -m uvicorn saas-backend.app.main:app --host 0.0.0.0 --port 3001 --reload
   ```
   - Aguarde: `INFO:     Application startup complete.`
   - Acesse: http://localhost:3001/docs (documentação da API)

4. **Inicie o EDGE Server** (Terminal 2)
   ```bash
   .\.venv\Scripts\python.exe edge-server/app.py
   ```
   - Aguarde: `✅ EDGE Server ready on 0.0.0.0:5000`

5. **Popule o banco de dados** (Terminal novo, uma única vez)
   ```bash
   cd D:\Front_Bier\saas-backend
   .\.venv\Scripts\python.exe seed.py
   ```
   - Resultado: `⚠️  Banco já possui dados. Seed ignorado.` é OK

6. **Inicie o HTTP Server** (Terminal 3)
   ```bash
   .\.venv\Scripts\python.exe -m http.server 8080 --directory .
   ```
   - Aguarde: `Serving HTTP on :: port 8080`

7. **Acesse a aplicação**
   ```
   http://localhost:8080/app-kiosk/index.html
   ```

## ✅ Verificar se Tudo Está Funcionando

### Terminal de Testes
```bash
# Verificar se SaaS está respondendo
curl http://localhost:3001/api/v1/health

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
