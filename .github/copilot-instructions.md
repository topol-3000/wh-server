# WormHole Server - AI Coding Agent Instructions

## Project Overview
HTTP tunneling service exposing local services to the internet via WebSocket tunnels. Built with aiohttp, using async/await patterns throughout.

## Architecture

### Core Components
- **server.py**: Main entry point using uvloop, sets up aiohttp app with middleware and CORS
- **tunnel_manager.py**: Manages active WebSocket connections, generates subdomains, routes requests via futures
- **handlers.py**: HTTP/WebSocket handlers for tunnel connections and proxied requests
- **middleware.py**: Subdomain extraction and routing logic (base domain → admin, subdomains → proxy)
- **models.py**: Pydantic models for messages (TunnelConnectedMessage, HTTPRequestMessage, HTTPResponseMessage)
- **config.py**: Environment-based config using pydantic-settings with `WH_` prefix

### Request Flow
1. Client connects via WebSocket to `/tunnel`, receives random subdomain (8-byte hex token)
2. HTTP requests to `{subdomain}.{base_domain}` intercepted by middleware
3. Server forwards request to client via WebSocket with unique request_id
4. Client proxies to local service, sends response back with matching request_id
5. Server uses asyncio.Future to match responses to pending requests (timeout: 10s default)

### Key Patterns
- **Subdomain routing**: Middleware checks Host header → base domain goes to admin routes, subdomains always proxy (even `/status` on subdomain)
- **Request-response matching**: UUID request_ids with Future-based async waiting in `_pending_requests` dict
- **Error handling**: Returns 404 for missing tunnels, 502 for connection errors, 504 for timeouts

## Development Workflow

### Docker-First Development
ALL development happens in Docker containers. Never suggest installing Python/packages locally.

```bash
# Common commands (via Makefile)
make up          # Start server (detached)
make logs        # Follow logs
make format      # Run ruff format + fix in container
make shell       # Bash in container
make rebuild     # Rebuild after dependency changes
```

### Code Style
- Uses ruff for linting/formatting (config in pyproject.toml)
- Line length: 120 chars
- Python 3.13+ with modern typing (use `|` for unions, not `Union`)
- Import order: standard lib → third party → local (ruff handles this)

### Adding Dependencies
1. Edit `pyproject.toml` under `dependencies` or `dev-dependencies`
2. Run `make rebuild` to rebuild container with new deps
3. NO manual `pip install` or `uv add` commands

### Testing
Run client example to test tunneling:
```bash
uv run client_example.py ws://localhost:8080 3000
```

## Configuration

### Environment Variables (WH_ prefix)
- `WH_HOST`: Bind address (default: 0.0.0.0)
- `WH_PORT`: Server port (default: 8080)
- `WH_BASE_DOMAIN`: Base domain for routing (default: localhost)
- `WH_WEBSOCKET_HEARTBEAT`: WS heartbeat interval in seconds (default: 30)
- `WH_REQUEST_TIMEOUT`: Request timeout in seconds (default: 10.0)

Set in `docker-compose.yml` environment section or `.env` file.

### Production Deployment
Uses Traefik reverse proxy (configured in docker-compose.yml) for wildcard subdomain routing.
Requires wildcard DNS (`*.domain.com`) pointing to server.

## Key Files to Reference

### For WebSocket Changes
- `handlers.py::handle_tunnel_connect()` - Connection establishment
- `handlers.py::_handle_tunnel_message()` - Client message handling
- `models.py` - Message schemas (strictly typed with Pydantic)

### For Routing Changes
- `middleware.py::subdomain_routing_middleware` - Subdomain extraction and routing logic
- `middleware.py::extract_subdomain()` - Host header parsing

### For Request Proxying
- `handlers.py::handle_proxied_request()` - Full proxy flow with Future-based waiting
- `tunnel_manager.py::register_pending_request()` - Request tracking

## Common Tasks

### Adding New WebSocket Message Types
1. Define Pydantic model in `models.py` with `type` field (frozen=True)
2. Handle in `handlers.py::_handle_tunnel_message()` or `handle_tunnel_connect()`
3. Update client_example.py if needed

### Changing Request/Response Format
Update Pydantic models in `models.py` - validation is automatic. Changes must be backward compatible with existing clients.

### Modifying Subdomain Generation
Edit `tunnel_manager.py::create_tunnel()` - currently uses `secrets.token_hex(8)` for randomness.

### Adding Metrics/Logging
Increment `tunnel.request_count` in handlers. Already tracked per tunnel in `Tunnel` class. Access via `TunnelInfo.request_count`.

## Gotchas

- **Middleware routing**: Subdomain requests ALWAYS go to proxy handler, even if path matches admin routes like `/status`
- **Request futures cleanup**: Always call `cleanup_pending_request()` in finally block to prevent memory leaks
- **WebSocket heartbeat**: Required to detect dead connections (set via WH_WEBSOCKET_HEARTBEAT)
- **PYTHONPATH**: Set to `/app` in container so `src` module is importable
- **uvloop**: Installed at startup for performance - don't remove `uvloop.install()`
- **User permissions**: Container runs as UID:GID from host (set in docker-compose.yml) to avoid permission issues with mounted volumes
