# 🍺 BierPass - Sistema de Venda de Bebidas

**Status:** ✅ MVP Funcional  
**Data da Última Atualização:** 23 de dezembro de 2025  
**Versão:** 1.0 Limpa

---

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.13+
- Virtual environment (`.venv`) ativado
- Pacotes instalados

### **Iniciar Sistema (Recomendado)**

```powershell
cd D:\Front_Bier
python run.py
```

Ou via batch (Windows):
```powershell
.\run.bat
```

**Resultado esperado:**
```
✅ [EDGE] Serviço iniciado em http://localhost:5000
✅ [SaaS] Serviço iniciado em http://localhost:3001
✅ [Frontend] Serviço iniciado em http://localhost:8080/app-kiosk
```

Abra no navegador: **http://localhost:8080/app-kiosk**

---

## 📁 Estrutura (100% Limpa)

```
D:\Front_Bier/
├── 🚀 run.py                    ← Launcher (USE ESTE!)
├── 🚀 run.bat                   ← Windows wrapper
├── ⚙️  config.py                ← Config centralizada
├── 📊 README.md                 ← Este arquivo
├── 💾 bierpass.db               ← Banco único
├── 🧪 reset_and_start.py        ← Reset completo
├── 📝 TESTE_PAGAMENTOS_NOVO.md  ← Guia de testes
├── 📝 ARQUIVO_ANALISE_FINAL.md  ← Análise de estrutura
│
├── 🎨 app-kiosk/                ← Frontend (Vanilla JS)
│   ├── index.html
│   ├── config.json
│   ├── js/ (8 arquivos)
│   ├── css/ (4 arquivos)
│   └── assets/data/beverages.json
│
├── 🔌 edge-server/              ← Servidor Local (Flask)
│   ├── app.py
│   ├── payment_service.py
│   ├── dispenser.py
│   ├── config.py, database.py, gpio_controller.py
│   ├── sync_service.py, token_validator.py
│   └── requirements.txt
│
└── ☁️  saas-backend/             ← Servidor SaaS (FastAPI)
    ├── app/ (main, config, database, models, routes, schemas, utils)
    ├── seed.py
    └── requirements.txt
```

---

## 💳 Pagamentos Suportados

**Modo:** Mock (Mercado Pago SDK)

- ✅ **PIX:** Aprovado automaticamente em 5 segundos
- ✅ **Débito:** Simula 2 minutos de espera com leitor
- ✅ **Crédito:** Simula 2 minutos de espera com leitor
- ✅ **QR Code:** Integração completa

---

## 📊 Fluxo Completo

```
1️⃣  Cliente seleciona bebida
    └─ Volume + método de pagamento

2️⃣  Pagamento (EDGE)
    └─ Mercado Pago Mock aprova/simula

3️⃣  Dispensação (ml-by-ml)
    └─ UI mostra progresso 0-100%

4️⃣  Registro (SaaS)
    └─ Salva venda + consumo no BD

5️⃣  Volta ao menu
    └─ Pronto para próximo cliente
```

---

## 🧪 Verificar Status via APIs

### Dashboard SaaS (Recomendado)
```
http://localhost:3001/docs
```
✅ Interface interativa para testar todas as APIs

### Verificar Banco de Dados via API
```bash
# Listar todas as bebidas
curl http://localhost:3001/api/v1/beverages

# Listar máquinas
curl http://localhost:3001/api/v1/machines

# Listar vendas
curl http://localhost:3001/api/v1/sales

# Listar consumos
curl http://localhost:3001/api/v1/consumptions
```

### Reset Completo
```powershell
python reset_and_start.py
```

---

## 🔧 Troubleshooting

### "Nenhuma bebida disponível"
```powershell
python check_db.py              # Verificar se tem dados
python saas-backend\seed.py     # Popular bebidas
python run.py                   # Reiniciar
```

### Erro de Conexão (EDGE)
- Verifique se `python run.py` iniciou todos os 3 serviços
- Aguarde 5 segundos para services ficarem prontos
- Abra: http://localhost:5000/health

### Banco Vazio
- Sempre inicie de `D:\Front_Bier/`
- Verificar: `D:\Front_Bier\bierpass.db` existe?

### Pagamento Não Funciona
- Verificar if modo Mock está ativo
- Testar: http://localhost:5000/edge/health
- Consultar logs no terminal
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
