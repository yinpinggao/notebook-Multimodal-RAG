# Advanced Configuration

Performance tuning, debugging, and advanced features.

---

## Performance Tuning

### Connection Pooling

```env
# Max concurrent database connections (default: 5)
OPEN_NOTEBOOK_SEEKDB_POOL_SIZE=5
```

**Guidelines:**
- CPU: 2 cores → 2-3 connections
- CPU: 4 cores → 5 connections (default)
- CPU: 8+ cores → 10-20 connections

### Query Timeout

```env
# Query timeout in seconds (default: 30)
OPEN_NOTEBOOK_SEEKDB_TIMEOUT_SECONDS=30
```

### Timeout Tuning

```env
# Client timeout (default: 300 seconds)
API_CLIENT_TIMEOUT=300

# LLM timeout (default: 60 seconds)
ESPERANTO_LLM_TIMEOUT=60
```

**Guideline:** Set `API_CLIENT_TIMEOUT` > `ESPERANTO_LLM_TIMEOUT` + buffer

```
Example:
  ESPERANTO_LLM_TIMEOUT=120
  API_CLIENT_TIMEOUT=180  # 120 + 60 second buffer
```

---

## Batching

### TTS Batch Size

For podcast generation, control concurrent TTS requests:

```env
# Default: 5
TTS_BATCH_SIZE=2
```

**Providers and recommendations:**
- OpenAI: 5 (can handle many concurrent)
- Google: 4 (good concurrency)
- ElevenLabs: 2 (limited concurrent requests)
- Local TTS: 1 (single-threaded)

Lower = slower but more stable. Higher = faster but more load on provider.

---

## Logging & Debugging

### Enable Detailed Logging

```bash
# Start with debug logging
RUST_LOG=debug  # For Rust components
LOGLEVEL=DEBUG  # For Python components
```

### Debug Specific Components

```bash
# Only langchain
LOGLEVEL=langchain:debug

# Only specific module
LOGLEVEL=open_notebook:debug
```

### LangSmith Tracing

For debugging LLM workflows:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_API_KEY=your-key
LANGCHAIN_PROJECT="Open Notebook"
```

Then visit https://smith.langchain.com to see traces.

---

## Port Configuration

### Default Ports

```
Frontend: 8502 (Docker deployment)
Frontend: 3000 (Development from source)
API: 5055
SeekDB: 2881 (MySQL client port), 2886 (OceanBase agent port)
Redis: 6379
```

### Changing Frontend Port

Edit `docker-compose.yml`:

```yaml
services:
  open-notebook:
    ports:
      - "8001:8502"  # Change from 8502 to 8001
```

Access at: `http://localhost:8001`

API auto-detects to: `http://localhost:5055` ✓

### Changing API Port

```yaml
services:
  open-notebook:
    ports:
      - "127.0.0.1:8502:8502"  # Frontend
      - "5056:5055"            # Change API from 5055 to 5056
    environment:
      - API_URL=http://localhost:5056  # Update API_URL
```

Access API directly: `http://localhost:5056/docs`

**Note:** When changing API port, you must set `API_URL` explicitly since auto-detection assumes port 5055.

### Changing SeekDB Port

```yaml
services:
  seekdb:
    ports:
      - "2882:2881"  # Change MySQL port from 2881 to 2882
    environment:
      - SEEKDB_DATABASE=${SEEKDB_DATABASE:-open_notebook_ai}
```

**Important:** When changing SeekDB port, update `OPEN_NOTEBOOK_SEEKDB_DSN` to match:
```env
OPEN_NOTEBOOK_SEEKDB_DSN=mysql://root:pass@seekdb:2882/open_notebook_ai
```

---

## SSL/TLS Configuration

### Custom CA Certificate

For self-signed certs on local providers:

```env
ESPERANTO_SSL_CA_BUNDLE=/path/to/ca-bundle.pem
```

### Disable Verification (Development Only)

```env
# WARNING: Only for testing/development
# Vulnerable to MITM attacks
ESPERANTO_SSL_VERIFY=false
```

---

## Multi-Provider Setup

### Use Different Providers for Different Tasks

Configure multiple AI providers via **Settings → API Keys**. Each provider gets its own credential:

1. Add a credential for your main language model provider (e.g., OpenAI, Anthropic)
2. Add a credential for embeddings (e.g., Voyage AI, or use the same provider)
3. Add a credential for TTS (e.g., ElevenLabs, or OpenAI-Compatible for local Speaches)
4. Each credential's models are registered and available independently

### Multiple Endpoints for OpenAI-Compatible

When using OpenAI-Compatible providers, you can configure per-service URLs in a single credential:

1. Go to **Settings** → **API Keys**
2. Click **Add Credential** → Select **OpenAI-Compatible**
3. Configure separate URLs for LLM, Embedding, TTS, and STT
4. Click **Save**, then **Test Connection**

---

## Security Hardening

### Change Default Credentials

```env
# Don't use defaults in production
# Use a secure password for SeekDB
SEEKDB_ROOT_PASSWORD=$(openssl rand -base64 32)  # Generate secure password
```

### Add Password Protection

```env
# Protect your Open Notebook instance
OPEN_NOTEBOOK_PASSWORD=your_secure_password
```

### Use HTTPS

```env
# Always use HTTPS in production
API_URL=https://mynotebook.example.com
```

### Firewall Rules

Restrict access to your Open Notebook:
- Port 8502 (frontend): Only from your IP
- Port 5055 (API): Only from frontend
- Port 2881 (SeekDB MySQL): Never expose to internet
- Port 2886 (SeekDB agent): Never expose to internet

---

## Web Scraping & Content Extraction

Open Notebook uses multiple services for content extraction:

### Firecrawl

For advanced web scraping:

```env
FIRECRAWL_API_KEY=your-key
```

Get key from: https://firecrawl.dev/

### Jina AI

Alternative web extraction:

```env
JINA_API_KEY=your-key
```

Get key from: https://jina.ai/

---

## Environment Variable Groups

### Credential Storage (Required)
```env
OPEN_NOTEBOOK_ENCRYPTION_KEY    # Required for storing credentials
```

AI provider API keys are configured via **Settings → API Keys** (not environment variables).

### Database
```env
OPEN_NOTEBOOK_SEEKDB_DSN
OPEN_NOTEBOOK_AI_CONFIG_BACKEND=seekdb
OPEN_NOTEBOOK_SEARCH_BACKEND=seekdb
```

### Performance
```env
OPEN_NOTEBOOK_SEEKDB_POOL_SIZE
OPEN_NOTEBOOK_SEEKDB_TIMEOUT_SECONDS
```

### API Settings
```env
API_URL
INTERNAL_API_URL
API_CLIENT_TIMEOUT
ESPERANTO_LLM_TIMEOUT
```

### Audio/TTS
```env
TTS_BATCH_SIZE
```

> **Note:** `ELEVENLABS_API_KEY` is deprecated. Configure ElevenLabs via **Settings → API Keys**.

### Debugging
```env
LANGCHAIN_TRACING_V2
LANGCHAIN_ENDPOINT
LANGCHAIN_API_KEY
LANGCHAIN_PROJECT
```

---

## Testing Configuration

### Quick Test

```bash
# Test API health
curl http://localhost:5055/health

# Test with sample (requires configured credential and registered models)
curl -X POST http://localhost:5055/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'
```

### Validate Config

```bash
# Check environment variables are set
env | grep OPEN_NOTEBOOK_ENCRYPTION_KEY

# Verify database connection
python -c "import os; print(os.getenv('OPEN_NOTEBOOK_SEEKDB_DSN'))"
```

---

## Troubleshooting Performance

### High Memory Usage

```env
# Reduce connection pool size
OPEN_NOTEBOOK_SEEKDB_POOL_SIZE=2

# Reduce TTS batch size
TTS_BATCH_SIZE=1
```

### High CPU Usage

```env
# Check pool size setting
OPEN_NOTEBOOK_SEEKDB_POOL_SIZE

# Reduce if maxed out:
OPEN_NOTEBOOK_SEEKDB_POOL_SIZE=5
```

### Slow Responses

```env
# Check timeout settings
API_CLIENT_TIMEOUT=300

# Increase SeekDB query timeout
OPEN_NOTEBOOK_SEEKDB_TIMEOUT_SECONDS=60
```

### Database Connection Issues

```env
# Reduce connection pool size
OPEN_NOTEBOOK_SEEKDB_POOL_SIZE=3
```

---

## Backup & Restore

### Data Locations

| Path | Contents |
|------|----------|
| `./data` or `/app/data` | Uploads, podcasts, checkpoints |
| Docker volume `seekdb_data` | SeekDB database files |

### Quick Backup

```bash
# Stop services (recommended for consistency)
docker compose down

# Create timestamped backup
tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  notebook_data/

# Restart services
docker compose up -d
```

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh - Run daily via cron

BACKUP_DIR="/path/to/backups"
DATE=$(date +%Y%m%d-%H%M%S)

# Create backup
tar -czf "$BACKUP_DIR/open-notebook-$DATE.tar.gz" \
  /path/to/notebook_data

# Keep only last 7 days
find "$BACKUP_DIR" -name "open-notebook-*.tar.gz" -mtime +7 -delete

echo "Backup complete: open-notebook-$DATE.tar.gz"
```

Add to cron:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/open-notebook-backup.log 2>&1
```

### Restore

```bash
# Stop services
docker compose down

# Remove old data (careful!)
rm -rf notebook_data/

# Extract backup
tar -xzf backup-20240115-120000.tar.gz

# Restart services
docker compose up -d
```

### Migration Between Servers

```bash
# On source server
docker compose down
tar -czf open-notebook-migration.tar.gz notebook_data/

# Transfer to new server
scp open-notebook-migration.tar.gz user@newserver:/path/

# On new server
tar -xzf open-notebook-migration.tar.gz
docker compose up -d
```

---

## Container Management

### Common Commands

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs (all services)
docker compose logs -f

# View logs (specific service)
docker compose logs -f api

# Restart specific service
docker compose restart api

# Update to latest version
docker compose down
docker compose pull
docker compose up -d

# Check resource usage
docker stats

# Check service health
docker compose ps
```

### Clean Up

```bash
# Remove stopped containers
docker compose rm

# Remove unused images
docker image prune

# Full cleanup (careful!)
docker system prune -a
```

---

## Summary

**Most deployments need:**
- One AI provider API key
- Default database settings
- Default timeouts

**Tune performance only if:**
- You have specific bottlenecks
- High-concurrency workload
- Custom hardware (very fast or very slow)

**Advanced features:**
- Firecrawl for better web scraping
- LangSmith for debugging workflows
- Custom CA bundles for self-signed certs
