# Single Container Installation

Minimal multi-container setup with SeekDB + Redis. **Simpler than full Docker Compose, but less flexible.**

**Best for:** PikaPods, Railway, shared hosting, minimal setups

> **Note**: While this is a simpler way to get started, we recommend [Docker Compose](docker-compose.md) for most users. Docker Compose is more flexible and will make it easier if we add more services to the setup in the future. This option is best for platforms that specifically require it (PikaPods, Railway, etc.).

## Prerequisites

- Docker installed (for local testing)
- API key from OpenAI, Anthropic, or another provider
- 5 minutes

## Quick Setup

### For Local Testing (Docker)

```yaml
# docker-compose.yml
services:
  seekdb:
    image: oceanbase/seekdb:latest
    entrypoint:
      - /bin/bash
      - /root/seekdb-start-fixed.sh
    ports:
      - "2881:2881"
      - "2886:2886"
    environment:
      - ROOT_PASSWORD=${SEEKDB_ROOT_PASSWORD:-SeekDBRoot123!}
      - SEEKDB_DATABASE=${SEEKDB_DATABASE:-open_notebook_ai}
    volumes:
      - seekdb_data:/var/lib/oceanbase
      - ./scripts/seekdb-start-fixed.sh:/root/seekdb-start-fixed.sh:ro
    restart: always

  redis:
    image: redis:7-alpine
    command: redis-server --save "" --appendonly no
    restart: always

  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    pull_policy: always
    ports:
      - "8502:8502"  # Web UI (React frontend)
      - "5055:5055"  # API
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=change-me-to-a-secret-string
      - OPEN_NOTEBOOK_SEEKDB_DSN=${OPEN_NOTEBOOK_SEEKDB_DSN:-mysql://root:SeekDBRoot123%21@seekdb:2881/open_notebook_ai}
      - OPEN_NOTEBOOK_AI_CONFIG_BACKEND=seekdb
      - OPEN_NOTEBOOK_SEARCH_BACKEND=seekdb
      - OPEN_NOTEBOOK_JOB_BACKEND=arq
      - OPEN_NOTEBOOK_REDIS_URL=redis://redis:6379/0
    volumes:
      - ./notebook_data:/app/data
    depends_on:
      - seekdb
      - redis
    restart: always

volumes:
  seekdb_data:
```

**Note:** Create a `scripts/` folder with the [seekdb-start-fixed.sh](https://raw.githubusercontent.com/lfnovo/open-notebook/main/scripts/seekdb-start-fixed.sh) script, or remove the entrypoint override if not needed.

Run:
```bash
docker compose up -d
```

Access: `http://localhost:8502`

Then configure your AI provider:
1. Go to **Settings** → **API Keys**
2. Click **Add Credential** → Select your provider → Paste API key
3. Click **Save**, then **Test Connection**
4. Click **Discover Models** → **Register Models**

### For Cloud Platforms

**Note:** Cloud platforms require a separate SeekDB database. You can use the Docker Compose setup for local development and testing, then deploy to cloud platforms with a managed database (like PlanetScale, Neon, or a self-hosted SeekDB instance).

**PikaPods:**
1. Click "New App"
2. Search "Open Notebook"
3. Set environment variables: `OPEN_NOTEBOOK_ENCRYPTION_KEY`, and your SeekDB DSN (`OPEN_NOTEBOOK_SEEKDB_DSN`)
4. Click "Deploy"
5. Open the app → Go to **Settings → API Keys** to configure your AI provider

**Railway:**
1. Create new project
2. Add `lfnovo/open_notebook:v1-latest`
3. Set environment variables: `OPEN_NOTEBOOK_ENCRYPTION_KEY`, `OPEN_NOTEBOOK_SEEKDB_DSN`, and other SeekDB vars
4. Deploy
5. Open the app → Go to **Settings → API Keys** to configure your AI provider

**Render:**
1. Create new Web Service
2. Use Docker image: `lfnovo/open_notebook:v1-latest`
3. Set environment variables in dashboard (at minimum: `OPEN_NOTEBOOK_ENCRYPTION_KEY` and `OPEN_NOTEBOOK_SEEKDB_DSN`)
4. Configure persistent disk for `/app/data`

**DigitalOcean App Platform:**
1. Create new app from Docker Hub
2. Use image: `lfnovo/open_notebook:v1-latest`
3. Set port to 8502
4. Add environment variables (at minimum: `OPEN_NOTEBOOK_ENCRYPTION_KEY` and `OPEN_NOTEBOOK_SEEKDB_DSN`)
5. Configure persistent storage

**Heroku:**
```bash
# Using heroku.yml
heroku container:push web
heroku container:release web
heroku config:set OPEN_NOTEBOOK_ENCRYPTION_KEY=your-secret-key
heroku config:set OPEN_NOTEBOOK_SEEKDB_DSN=mysql://user:pass@host:2881/db
```

**Coolify:**
1. Add new service → Docker Image
2. Image: `lfnovo/open_notebook:v1-latest`
3. Port: 8502
4. Add environment variables (at minimum: `OPEN_NOTEBOOK_ENCRYPTION_KEY` and `OPEN_NOTEBOOK_SEEKDB_DSN`)
5. Enable persistent volumes
6. Coolify handles HTTPS automatically

---

## Environment Variables

| Variable | Purpose | Example |
|----------|---------|---------|
| `OPEN_NOTEBOOK_ENCRYPTION_KEY` | Encryption key for credentials (required) | `my-secret-key` |
| `OPEN_NOTEBOOK_SEEKDB_DSN` | Database connection (MySQL protocol) | `mysql://root:pass@seekdb:2881/db` |
| `OPEN_NOTEBOOK_AI_CONFIG_BACKEND` | AI config storage backend | `seekdb` |
| `OPEN_NOTEBOOK_SEARCH_BACKEND` | Search backend | `seekdb` |
| `OPEN_NOTEBOOK_JOB_BACKEND` | Job queue backend | `arq` |
| `OPEN_NOTEBOOK_REDIS_URL` | Redis connection | `redis://redis:6379/0` |
| `API_URL` | External URL (for remote access) | `https://myapp.example.com` |

AI provider API keys are configured via the **Settings → API Keys** UI after deployment.

---

## Limitations vs Docker Compose

| Feature | This Setup | Docker Compose |
|---------|------------|----------------|
| Services | 3 (SeekDB + Redis + App) | 3 (SeekDB + Redis + App) |
| Complexity | Moderate | Moderate |
| Scalability | Limited | Excellent |
| Memory usage | ~1.2GB | ~1.2GB |

This setup and Docker Compose now use the same services. The main difference is Docker Compose gives you more control over configuration.

---

## Next Steps

Same as Docker Compose setup - just access via `http://localhost:8502` (local) or your platform's URL (cloud).

1. Go to **Settings → API Keys** to add your AI provider credential
2. **Test Connection** and **Discover Models**

See [Docker Compose](docker-compose.md) for full post-install guide.
