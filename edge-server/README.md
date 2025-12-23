# EDGE Server - BierPass

Servidor de borda para controle do dispenser de bebidas no Raspberry Pi.

## 📋 Visão Geral

O EDGE Server é o componente físico do sistema BierPass, responsável por:
- Receber tokens de autorização do APP Kiosk
- Validar tokens via HMAC-SHA256
- Controlar a bomba de chopp via GPIO
- Medir volume dispensado com sensor de fluxo
- Sincronizar consumos com o SaaS Backend

## 🏗️ Arquitetura

```
┌─────────────────┐     HMAC Token      ┌─────────────────┐
│   APP Kiosk     │ ──────────────────► │   EDGE Server   │
│   (Tablet)      │                     │  (Raspberry Pi) │
└─────────────────┘                     └────────┬────────┘
                                                 │
                                        ┌────────┴────────┐
                                        │                 │
                                        ▼                 ▼
                                ┌──────────────┐  ┌──────────────┐
                                │  GPIO Pump   │  │ Flow Sensor  │
                                │  (Relay)     │  │ (YF-S201)    │
                                └──────────────┘  └──────────────┘
                                                         │
                                                         ▼
                                                ┌──────────────┐
                                                │ SaaS Backend │
                                                │ (Sync Data)  │
                                                └──────────────┘
```

## 📁 Estrutura de Arquivos

```
edge-server/
├── app.py              # Flask API principal
├── config.py           # Configurações (GPIO, HMAC, SaaS)
├── token_validator.py  # Validação HMAC de tokens
├── gpio_controller.py  # Controle de GPIO (bomba + sensor)
├── dispenser.py        # Lógica de dispensação
├── database.py         # SQLite para armazenamento local
├── sync_service.py     # Sincronização com SaaS
├── requirements.txt    # Dependências Python
└── README.md           # Este arquivo
```

## 🔧 Instalação no Raspberry Pi

### 1. Pré-requisitos

```bash
# Atualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Python 3.9+
sudo apt install python3 python3-pip python3-venv -y

# Habilitar GPIO
sudo raspi-config
# Interface Options > GPIO > Enable
```

### 2. Configurar o projeto

```bash
# Clonar repositório
cd /home/pi
git clone <repo-url> bierpass
cd bierpass/edge-server

# Criar ambiente virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt

# No Raspberry Pi, também instalar RPi.GPIO
pip install RPi.GPIO
```

### 3. Configurar variáveis de ambiente

```bash
# Criar arquivo .env ou exportar variáveis
export EDGE_MACHINE_ID="seu-machine-uuid-do-saas"
export EDGE_API_KEY="sua-api-key-do-saas"
export SAAS_URL="http://seu-servidor:3001"
export EDGE_HMAC_SECRET="chave-hmac-compartilhada-com-saas"
export EDGE_DEBUG="false"
```

### 4. Executar

```bash
# Desenvolvimento
python app.py

# Produção (com Gunicorn)
pip install gunicorn
gunicorn -w 1 -b 0.0.0.0:5000 app:app
```

### 5. Configurar como serviço (systemd)

```bash
sudo nano /etc/systemd/system/bierpass-edge.service
```

```ini
[Unit]
Description=BierPass EDGE Server
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/bierpass/edge-server
Environment=EDGE_MACHINE_ID=seu-uuid
Environment=EDGE_API_KEY=sua-key
Environment=SAAS_URL=http://servidor:3001
Environment=EDGE_HMAC_SECRET=sua-chave
ExecStart=/home/pi/bierpass/edge-server/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable bierpass-edge
sudo systemctl start bierpass-edge
```

## 📡 API Endpoints

### Health Check
```http
GET /edge/health

Response:
{
  "status": "healthy",
  "service": "edge-server",
  "machine_id": "uuid"
}
```

### Status Detalhado
```http
GET /edge/status

Response:
{
  "dispenser": {
    "status": "idle",
    "is_dispensing": false
  },
  "sync": {
    "running": true,
    "saas_reachable": true,
    "records": {
      "pending_sync": 0,
      "synced": 42
    }
  },
  "gpio": {
    "mock_mode": false,
    "pump_state": "off"
  }
}
```

### Autorizar e Dispensar
```http
POST /edge/authorize
Content-Type: application/json

{
  "token": "eyJzYWxlX2lkIjoiLi4uIn0=.HMAC_SIGNATURE"
}

Response (200):
{
  "authorized": true,
  "result": {
    "success": true,
    "volume_authorized_ml": 500,
    "volume_dispensed_ml": 498.5,
    "duration_seconds": 5.2
  }
}
```

### Cancelar Dispensação
```http
POST /edge/cancel

Response:
{
  "cancelled": true
}
```

### Forçar Sincronização (requer API Key)
```http
POST /edge/sync
X-API-Key: sua-api-key

Response:
{
  "synced": 5,
  "failed": 0,
  "pending": 0
}
```

## 🔌 GPIO Pinout

| Pino Físico | GPIO BCM | Função | Descrição |
|-------------|----------|--------|-----------|
| 11 | GPIO 17 | PUMP_PIN | Relé da bomba (OUTPUT) |
| 13 | GPIO 27 | FLOW_SENSOR_PIN | Sensor de fluxo (INPUT) |
| 15 | GPIO 22 | LED_STATUS_PIN | LED verde status |
| 16 | GPIO 23 | LED_ERROR_PIN | LED vermelho erro |

### Diagrama de Conexão

```
Raspberry Pi                    Componentes
─────────────                   ───────────
GPIO 17 (Pin 11) ────────────► Relé 5V ────► Bomba 12V
GPIO 27 (Pin 13) ◄──────────── Sensor YF-S201 (Sinal)
3.3V (Pin 1) ────────────────► Sensor YF-S201 (VCC)
GND (Pin 6) ─────────────────► Sensor YF-S201 (GND)
                               Relé (GND)
5V (Pin 2) ──────────────────► Relé (VCC)
```

## 🔐 Formato do Token

O token é gerado pelo SaaS/APP e validado pelo EDGE:

```
TOKEN = base64(PAYLOAD) + "." + base64(HMAC-SHA256(PAYLOAD, SECRET))
```

### Payload JSON
```json
{
  "sale_id": "uuid-da-venda",
  "beverage_id": "uuid-da-bebida",
  "volume_ml": 500,
  "tap_id": 1,
  "timestamp": 1703347200.123,
  "nonce": "random-unique-string"
}
```

### Validações
1. ✅ Assinatura HMAC válida
2. ✅ Token não expirado (30s tolerância)
3. ✅ Token não reutilizado (single-use)
4. ✅ tap_id configurado na máquina

## 💾 Armazenamento Local

O EDGE mantém um SQLite local para:
- Consumos pendentes de sincronização
- Tokens já utilizados (anti-replay)
- Log de tentativas de sync

Isso permite operação offline - consumos são armazenados localmente e sincronizados quando a conexão com o SaaS é restabelecida.

## 🧪 Desenvolvimento (sem Raspberry Pi)

O servidor detecta automaticamente a ausência de `RPi.GPIO` e usa um mock GPIO que simula o comportamento:

```bash
# Windows/Mac/Linux sem GPIO
cd edge-server
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt

# Executar em modo debug
set EDGE_DEBUG=true  # Windows
export EDGE_DEBUG=true  # Linux/Mac

python app.py
```

### Testar com token gerado
```bash
# Gerar token de teste (apenas em debug mode)
curl -X POST http://localhost:5000/edge/test/generate-token \
  -H "Content-Type: application/json" \
  -d '{"volume_ml": 300}'

# Usar o token para dispensar
curl -X POST http://localhost:5000/edge/authorize \
  -H "Content-Type: application/json" \
  -d '{"token": "TOKEN_GERADO"}'
```

## 🔍 Troubleshooting

### Pump não liga
1. Verificar conexão GPIO 17
2. Verificar alimentação do relé (5V)
3. Testar: `python -c "from gpio_controller import gpio_controller; gpio_controller.initialize(); gpio_controller.pump_on()"`

### Sensor não conta pulsos
1. Verificar conexão GPIO 27
2. Verificar alimentação do sensor (3.3V)
3. O sensor YF-S201 precisa de fluxo mínimo de ~1L/min

### Sync falhando
1. Verificar conectividade: `curl http://saas-url:3001/api/v1/health`
2. Verificar API Key
3. Ver logs: `journalctl -u bierpass-edge -f`

### Token sempre inválido
1. Verificar se HMAC_SECRET é igual no SaaS e EDGE
2. Verificar sincronização de relógio (NTP)
3. Tokens expiram em 30 segundos

## 📊 Calibração do Sensor

O sensor YF-S201 tem ~450 pulsos/litro, mas pode variar. Para calibrar:

1. Dispensar 1L medido manualmente
2. Contar pulsos registrados
3. Atualizar `PULSES_PER_LITER` em `config.py`

```python
# config.py
PULSES_PER_LITER: float = 450.0  # Ajustar conforme medição
```

## 📝 Logs

```bash
# Ver logs do serviço
journalctl -u bierpass-edge -f

# Ver últimas 100 linhas
journalctl -u bierpass-edge -n 100
```

## 🔄 Atualizações

```bash
cd /home/pi/bierpass
git pull
sudo systemctl restart bierpass-edge
```
