# ARCHITECTURE.md — Wormhole Tunneling System

## 🔥 Overview

**Wormhole** is a scalable reverse-tunneling system similar to **Ngrok** or **Cloudflare Tunnel**.

It allows users to expose their local services to the internet via public URLs such as:

```
https://<tunnel-id>.wormhole.app
```

Requests received on that domain are forwarded through a persistent WebSocket connection to a *client agent* running locally on the user’s machine.

The architecture is built so both:

- **WebSocket control plane**  
- **HTTP/WS data plane**

can scale horizontally.

Message routing is handled through **NATS** using request/reply semantics.

---

# 🧱 System Architecture

```
                       ┌────────────────────┐
 Public Internet  →    │   Edge Proxy (L7)  │  ← Traefik / Nginx / Hetzner LB
                       └───────────┬────────┘
                                   │
        ┌──────────────────────────┴────────────────────────────┐
        │                                                       │
        ▼                                                       ▼
┌──────────────────┐                                   ┌──────────────────┐
│  Tunnel Service   │  ←→ NATS request/response ←→      │ WebSocket Service │
│ (HTTP/WS Data)    │                                   │ (Control Plane)   │
└──────────────────┘                                   └──────────────────┘
                                                                 │
                                                                 ▼
                                                        ┌──────────────────┐
                                                        │  Client Agent     │
                                                        │ (local machine)   │
                                                        └──────────────────┘
```

---

# 📌 Components

## 1. **Edge Proxy (Traefik / Nginx / LB)**

- Terminates TLS  
- Routes:
  - `wss://control.wormhole.app/connect` → **WebSocket Service**
  - `https://<tunnel-id>.wormhole.app/*` → **Tunnel Service**

---

## 2. **WebSocket Service (Control Plane)**

Responsible for maintaining active tunnels.

### Responsibilities:
- Accept WebSocket connections from client agents
- Register active tunnels:
  ```python
  active_tunnels[tunnel_id] = {
      "ws": <conn>,
      "target": "http://localhost:3000"
  }
  ```
- Subscribe to NATS subject `tunnel.<tunnel_id>`
- Forward requests to agent via WS
- Forward responses back to Tunnel Service via NATS

### Scaling:
- Horizontally scalable
- Each instance owns different tunnels
- Load balancer distributes WS connections

---

## 3. **Tunnel Service (Data Plane)**

Stateless HTTP service that receives public requests.

### Responsibilities:
1. Extract tunnel ID from hostname  
2. Convert HTTP → `InternalRequest`  
3. Send NATS request to `tunnel.<id>`  
4. Wait for `InternalResponse`  
5. Convert to HTTP response and return  

### Unknown Tunnels:
If no NATS subscriber → return:

```
404 Tunnel Not Active
```

### Scaling:
- Fully stateless  
- Unlimited horizontal scaling  

---

## 4. **NATS Message Bus**

Backbone communication layer.

### Subjects:
- `tunnel.<tunnel_id>`

### Pattern:
- Tunnel Service → `nats.request()`
- WS Service → `nats.subscribe()`

Ensures dynamic routing and auto-failover.

---

## 5. **Client Agent**

Local lightweight worker.

### Responsibilities:
- Connect to WS service
- Receive tunneled requests
- Convert them into real HTTP requests to localhost
- Return results via WebSocket

### Full HTTP Fidelity:
- Method  
- Path  
- Query  
- Headers  
- Body (binary → base64)  

---

# 🧩 Internal Request/Response

### InternalRequest

```jsonc
{
  "request_id": "uuid",
  "tunnel_id": "abc123",
  "method": "GET",
  "path": "/api",
  "query": "x=1",
  "headers": { "user-agent": "..." },
  "body": "base64",
  "is_websocket": false
}
```

### InternalResponse

```jsonc
{
  "request_id": "uuid",
  "status_code": 200,
  "headers": { "content-type": "application/json" },
  "body": "base64"
}
```

---

# 🔁 Request Flow Overview

### 1. Agent connects

```
wss://control.wormhole.app/connect?tunnel_id=abc123&target=http://localhost:3000
```

WS service registers tunnel + subscribes NATS.

---

### 2. Public request hits:

```
GET https://abc123.wormhole.app/api/users
```

Tunnel Service:
- Parses ID  
- Sends InternalRequest over NATS  

---

### 3. WS service forwards to agent

- Receives NATS request  
- Sends via WebSocket to agent  

---

### 4. Agent → localhost → WS service → NATS → Tunnel service

Full response propagates back and is sent to public client.

---

# 📦 Deployment Model

### WS Service

- Stateful (keeps WS connections)
- Sharded by load balancer
- Automatic failover on disconnect

### Tunnel Service

- Stateless
- Infinite horizontal scaling

### NATS

- Routes tunnel requests  
- Ensures correct message delivery  

---

# 🔒 Security

- TLS termination at proxy  
- Tunnel IDs are random  
- Optional tokens for tunnel authentication  
- Heartbeats detect dead tunnels  
- NATS authenticated via creds/JWT  

---

# 🧰 Recommended Stack

- FastAPI  
- Python or Go agent  
- NATS JetStream  
- Traefik  
- Docker Compose (dev)  
- Kubernetes or Nomad (prod)  

---

# 🧭 Future Extensions

- Binary WebSocket stream tunneling  
- Public dashboard  
- Traffic analytics  
- Permanent tunnel records in DB  

