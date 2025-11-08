# 🚀 WormHole Server

A lightweight HTTP tunneling service that allows you to expose your localhost services to the public internet. Built with Python and WebSockets.

## ✨ Features

- **HTTP Tunneling**: Expose local services through secure WebSocket tunnels
- **Dynamic Subdomains**: Automatic subdomain generation for each tunnel
- **Real-time Proxying**: Low-latency request forwarding
- **Docker Support**: Fully containerized deployment
- **Web Interface**: Simple status dashboard
- **RESTful API**: Monitor active tunnels and server status

## 📋 Prerequisites

- Docker & Docker Compose
- Make (optional, but recommended for convenience)

**Note:** All commands run inside Docker containers. No need to install Python, uv, or dependencies locally!

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone and build**
   ```bash
   git clone <repository-url>
   cd wh-server
   make setup
   ```

2. **Start the server**
   ```bash
   make up
   ```

3. **Check logs**
   ```bash
   make logs
   ```

The server will be available at `http://localhost:8080`

### Without Make

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# View logs
docker-compose logs -f
```

## 📖 Usage

### Server

The server listens for WebSocket connections from clients and proxies HTTP requests.

**Access points:**
- Web Interface: `http://localhost:8080/`
- Status API: `http://localhost:8080/status`
- Tunnel WebSocket: `ws://localhost:8080/tunnel`

### Client Example

Run the example client to tunnel a local service:

```bash
# Start local service on port 3000 (included in client example)
uv run client_example.py ws://localhost:8080 3000

# Or using make
make client
```

The client will:
1. Connect to the WormHole server
2. Receive a unique subdomain
3. Start a local test server on port 3000
4. Forward all requests from `http://localhost:8080/{subdomain}/*` to `http://localhost:3000/*`

### Architecture

```
Internet Request → WormHole Server → WebSocket Tunnel → Local Client → Local Service
                    (Public)                                           (localhost:3000)
```

## 🛠️ Makefile Commands

All commands run inside Docker containers:

```bash
make help          # Show all available commands
make setup         # Build Docker image
make up            # Start server in detached mode
make down          # Stop server
make restart       # Restart server
make logs          # View server logs (follow mode)
make logs-tail     # View last 100 lines of logs
make status        # Check service status
make lint          # Run ruff linter in Docker
make format        # Format code with ruff in Docker
make shell         # Open bash shell in container
make python        # Open Python shell in container
make healthcheck   # Check server health
make rebuild       # Rebuild and restart
make dev           # Start in development mode (with logs)
make clean         # Clean up containers
make clean-all     # Remove everything (containers, images, data)
```

## 🐳 Docker Commands

```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Rebuild
docker-compose up -d --build
```

## 📡 API Endpoints

### GET `/`
Welcome page with server information

### GET `/status`
Returns server status and active tunnels
```json
{
  "status": "running",
  "active_tunnels": 2,
  "tunnels": [
    {
      "subdomain": "abc123xyz",
      "tunnel_id": "uuid-here",
      "created_at": "2025-11-05T12:00:00",
      "request_count": 42
    }
  ]
}
```

### WebSocket `/tunnel`
Create a new tunnel connection

**Server → Client (on connect):**
```json
{
  "type": "connected",
  "tunnel_id": "uuid",
  "subdomain": "abc123xyz",
  "public_url": "http://localhost:8080/abc123xyz"
}
```

**Server → Client (on request):**
```json
{
  "type": "http_request",
  "request_id": "uuid",
  "method": "GET",
  "path": "/api/users",
  "query_string": "page=1",
  "headers": {},
  "body": ""
}
```

**Client → Server (response):**
```json
{
  "request_id": "uuid",
  "status": 200,
  "headers": {},
  "body": "response content"
}
```

### ANY `/{subdomain}/*`
Proxied requests to tunnel clients

## 🔧 Configuration

Environment variables:

- `WH_HOST`: Server bind address (default: `0.0.0.0`)
- `WH_PORT`: Server port (default: `8080`)

Update in `docker-compose.yml`:
```yaml
environment:
  - WH_HOST=0.0.0.0
  - WH_PORT=8080
```

## 🧪 Development

### Docker-First Approach

This project uses Docker for all development tasks. No need to install Python or dependencies locally!

```bash
# Format code
make format

# Lint code
make lint

# Open shell in container
make shell

# Open Python REPL
make python

# Start in dev mode (with logs)
make dev
```

### Adding Dependencies

1. Edit `pyproject.toml` and add your dependency
2. Rebuild the container:
   ```bash
   make rebuild
   ```

### Project Structure

```
wh-server/
├── server.py              # Main server implementation
├── client_example.py      # Example client
├── pyproject.toml        # Project config and dependencies
├── Dockerfile            # Container definition
├── docker-compose.yml    # Compose configuration
├── Makefile             # Development commands
└── README.md            # This file
```

## 🔒 Security Considerations

**⚠️ This is a prototype for development/testing purposes. For production use, consider:**

- HTTPS/WSS encryption
- Authentication and authorization
- Rate limiting
- Request size limits
- Subdomain validation
- Connection timeouts
- Resource limits

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make format` and `make lint` (runs in Docker)
5. Submit a pull request

## 📝 License

MIT License - feel free to use this project as you wish.

## 🐛 Troubleshooting

### Port already in use
```bash
# Check what's using port 8080
lsof -i :8080

# Stop the service or change port in docker-compose.yml
```

### Docker issues
```bash
# Clean everything
make clean-all

# Rebuild from scratch
make rebuild
```

### Client can't connect
- Ensure server is running: `make status`
- Check server logs: `make logs`
- Verify WebSocket URL is correct

## 📚 Further Reading

- [aiohttp Documentation](https://docs.aiohttp.org/)
- [WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [Docker Documentation](https://docs.docker.com/)

## 💡 Future Enhancements

- [ ] HTTPS/TLS support
- [ ] Custom subdomain selection
- [ ] Authentication system
- [ ] Request logging and analytics
- [ ] Multiple protocol support (TCP, UDP)
- [ ] Client SDKs for different languages
- [ ] Web dashboard for tunnel management
- [ ] Persistent tunnel configuration

---

Made with ❤️ for the developer community
