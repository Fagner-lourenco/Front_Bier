# BierPass SaaS Backend

Backend para gestão de máquinas dispensadoras de bebidas BierPass.

## 🚀 Quick Start (Desenvolvimento)

### 1. Criar ambiente virtual

```powershell
cd saas-backend
python -m venv venv
.\venv\Scripts\Activate
```

### 2. Instalar dependências

```powershell
pip install -r requirements.txt
```

### 3. Executar seed (dados iniciais)

```powershell
python seed.py
```

### 4. Iniciar servidor

```powershell
uvicorn app.main:app --reload --port 3001
```

### 5. Acessar documentação

- Swagger UI: http://localhost:3001/docs
- ReDoc: http://localhost:3001/redoc

## 📋 Endpoints Principais

### Para APP Kiosk (API Key)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `GET` | `/api/v1/beverages` | Lista bebidas |
| `POST` | `/api/v1/sales` | Registra venda |
| `POST` | `/api/v1/consumptions` | Registra consumo |

### Para Admin (JWT)

| Método | Endpoint | Descrição |
|--------|----------|-----------|
| `POST` | `/api/v1/auth/login` | Login |
| `GET` | `/api/v1/dashboard` | Métricas |
| `GET` | `/api/v1/machines` | Lista máquinas |
| `GET` | `/api/v1/sales` | Lista vendas |

## 🔐 Autenticação

### APP Kiosk
Header: `X-API-Key: sk_xxxxx`

### Admin Dashboard
Header: `Authorization: Bearer <jwt_token>`

## 📁 Estrutura

```
saas-backend/
├── app/
│   ├── main.py           # FastAPI app
│   ├── config.py         # Configurações
│   ├── database.py       # SQLAlchemy
│   ├── models/           # Modelos do banco
│   ├── schemas/          # Pydantic schemas
│   ├── routes/           # Endpoints
│   └── utils/            # Auth, security
├── seed.py               # Dados iniciais
├── requirements.txt
├── .env
└── bierpass.db          # SQLite (criado automaticamente)
```

## 🧪 Testando a API

### Listar bebidas (sem auth - dev mode)
```bash
curl http://localhost:3001/api/v1/beverages
```

### Listar bebidas (com API Key)
```bash
curl -H "X-API-Key: sk_xxxxx" http://localhost:3001/api/v1/beverages
```

### Registrar venda
```bash
curl -X POST http://localhost:3001/api/v1/sales \
  -H "Content-Type: application/json" \
  -d '{
    "machine_id": "M001",
    "beverage_id": "uuid-da-bebida",
    "volume_ml": 300,
    "total_value": 12.00,
    "payment_method": "PIX",
    "payment_transaction_id": "TXN_123",
    "payment_nsu": "987654"
  }'
```

### Login admin
```bash
curl -X POST http://localhost:3001/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@bierpass.com.br&password=admin123"
```

## 🔄 Integração com APP Kiosk

Edite `app-kiosk/config.json`:

```json
{
  "api": {
    "saas_url": "http://localhost:3001",
    "edge_url": "http://localhost:5000",
    "use_mock": false
  },
  "machine": {
    "id": "M001",
    "api_key": "sk_xxxxx"
  }
}
```
