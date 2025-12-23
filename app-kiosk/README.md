# 🍺 BierPass Kiosk - APP Frontend

**Sistema de Distribuição Inteligente de Bebidas**

## 🚀 Quick Start

### 1. Pré-requisitos
- VSCode instalado
- Live Server extension (instale via marketplace)
- Windows 11

### 2. Abrir no VSCode
```powershell
code d:\Front_Bier\app-kiosk
```

### 3. Rodar com Live Server
1. Clique direito em `index.html`
2. Selecione "Open with Live Server"
3. Navegador abre em `http://127.0.0.1:5500`

### 4. Debug
- Pressione `ESC` para abrir painel de debug
- Abra DevTools (F12) para console JavaScript
- Verifique logs em Console

---

## 📁 Estrutura de Arquivos

```
app-kiosk/
├── index.html                 # Página principal
├── config.json               # Configurações
├── package.json              # Node.js (opcional)
│
├── css/
│   ├── style.css            # Estilos principais + componentes
│   ├── responsive.css       # Media queries para tablets
│   ├── state-screens.css    # Estilos específicos por tela
│   └── animations.css       # Animações customizadas
│
├── js/
│   ├── main.js              # Entry point e controllers
│   ├── state-machine.js     # Gerenciador de estados
│   ├── ui.js                # Renderização de telas
│   ├── api.js               # Chamadas HTTP
│   ├── polling.js           # Polling durante DISPENSING
│   ├── storage.js           # LocalStorage para recovery
│   ├── validators.js        # Validações e utilitários
│   └── mock-apis.js         # APIs simuladas para dev
│
├── assets/
│   ├── images/
│   │   ├── beverages/       # Fotos das bebidas
│   │   └── icons/           # Ícones (spinner, success, etc)
│   └── data/
│       └── beverages.json   # Cardápio (mock)
│
└── README.md                # Este arquivo
```

---

## 🎯 Estados da Aplicação

```
BOOT (2s)
  ↓
IDLE (cardápio) ← timeout 30s
  ↓ [clica bebida]
SELECT_VOLUME
  ↓ [escolhe volume]
CONFIRM_AGE
  ↓ [sim/não] ← timeout 15s
SELECT_PAYMENT
  ↓ [escolhe pagamento]
PAYMENT_PROCESSING ← timeout 30s
  ↓
AUTHORIZED (1s)
  ↓
DISPENSING (polling 300ms)
  ↓
FINISHED (5s)
  ↓
IDLE
```

---

## 🔧 Configuração (config.json)

```json
{
  "api": {
    "use_mock": true,        // Usar APIs simuladas
    "saas_url": "http://localhost:3001",
    "edge_url": "http://localhost:5000"
  },
  "ui": {
    "polling_ms": 300,       // Frequência de polling
    "boot_duration_ms": 2000,
    "idle_timeout_ms": 30000,
    "confirm_age_timeout_ms": 15000,
    "payment_timeout_ms": 30000,
    "finished_timeout_ms": 5000
  }
}
```

---

## 🧪 Testes Básicos

### Teste 1: Fluxo Completo
1. APP inicia → BOOT (2s)
2. Cardápio carrega → IDLE
3. Clica "Chopp"
4. Seleciona "300ml"
5. Confirma "+18"
6. Escolhe "PIX"
7. Processa pagamento (simulado)
8. Barra sobe durante DISPENSING
9. Sucesso!

### Teste 2: Timeout IDLE
1. Na tela inicial
2. Aguarda 30s sem clicar
3. Deve voltar automaticamente

### Teste 3: Refresh Mid-Fluxo
1. Em qualquer tela, pressione F5
2. APP deve tentar recuperar estado

---

## 🐛 Debug

### Console do Navegador (F12)
```javascript
// Ver estado atual
StateMachineInstance.getState()

// Mudar estado
StateMachineInstance.setState('IDLE')

// Ver dados do estado
StateMachineInstance.getStateData()

// Ver logs do app
console.log() // Aparecem no painel de debug também
```

### Painel Debug
- Pressione `ESC` para abrir
- Mostra logs em tempo real
- Canto inferior direito

---

## 📝 Fluxo de Desenvolvimento

### Fase 1 ✅ Concluída
- [x] Estrutura HTML de todas as 9 telas
- [x] CSS responsivo para tablet
- [x] Animações
- [x] State machine

### Fase 2 ✅ Concluída
- [x] APIs mock
- [x] Controllers para cada action

### Fase 3 ⏳ Próxima
- [ ] Integração com SaaS real
- [ ] Integração com EDGE real
- [ ] Testes com pessoas reais
- [ ] Refinamento de UX

---

## 🔌 Integração com Backend

### Quando pronto com SaaS/EDGE real:

**1. Mudar em config.json:**
```json
"use_mock": false
```

**2. Configurar URLs:**
```json
"saas_url": "https://api.bierpass.com",
"edge_url": "http://192.168.1.100:5000"
```

**3. Testar conexões:**
```javascript
// No console
await API.testSaaSConnection()
await API.testEdgeConnection()
```

---

## 🎨 Customização

### Cores
Editar em `css/style.css`:
```css
:root {
  --primary: #FF6B35;      /* Laranja */
  --secondary: #004E89;    /* Azul */
  --success: #28A745;      /* Verde */
  --error: #DC3545;        /* Vermelho */
}
```

### Timeouts
Editar em `config.json` seção `ui`

### Bebidas
Editar em `assets/data/beverages.json` ou via API real

---

## 🚨 Troubleshooting

### "CORS Error"
→ Use `use_mock: true` durante desenvolvimento

### "Live Server não recarrega"
→ Salve o arquivo (Ctrl+S)
→ Limpe cache (Ctrl+Shift+Delete)

### "Barra não anima suave"
→ Aumente `polling_ms` para 200ms
→ Ou reduz para 150ms

### "Debug log vazio"
→ Verifique `"debug": true` em config.json

---

## 📊 Performance

- Vanilla JavaScript (sem frameworks)
- CSS otimizado (sem Bootstrap)
- Animações com GPU acceleration
- Polling eficiente (300ms padrão)
- Storage local para recovery

---

## ✅ Checklist de Deployement

- [ ] Testar em tablet real (iPad/Android)
- [ ] Testar com internet desligada
- [ ] Testar 100 ciclos continuos
- [ ] Teste com pessoas reais
- [ ] Remover logs do debug
- [ ] Otimizar imagens
- [ ] Minificar CSS/JS (opcional)
- [ ] Setup HTTPS

---

## 📞 Suporte

Verifique:
1. Console (F12)
2. Painel Debug (ESC)
3. DevTools > Network (chamadas HTTP)

---

**Desenvolvido para o projeto BIERPASS - MVP Simplificado**
