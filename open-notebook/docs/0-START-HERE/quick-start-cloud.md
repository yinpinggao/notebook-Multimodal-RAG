# Quick Start - Cloud AI Providers (5 minutes)

Get Open Notebook running with **Anthropic, Google, Groq, or other cloud providers**. Same simplicity as OpenAI, with more choices.

## Prerequisites

1. **Docker Desktop** installed
   - [Download here](https://www.docker.com/products/docker-desktop/)
   - Already have it? Skip to step 2

2. **API Key** from your chosen provider:
   - **OpenRouter** (100+ models, one key): https://openrouter.ai/keys
   - **Anthropic (Claude)**: https://console.anthropic.com/
   - **Google (Gemini)**: https://aistudio.google.com/
   - **Groq** (fast, free tier): https://console.groq.com/
   - **Mistral**: https://console.mistral.ai/
   - **DeepSeek**: https://platform.deepseek.com/
   - **xAI (Grok)**: https://console.x.ai/

## Step 1: Create Configuration (1 min)

Create a new folder `open-notebook` and add this file:

**docker-compose.yml**:
```yaml
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
    ports:
      - "6379:6379"
    restart: always

  open_notebook:
    image: lfnovo/open_notebook:v1-latest
    pull_policy: always
    ports:
      - "8502:8502"  # Web UI
      - "5055:5055"  # REST API
    environment:
      - OPEN_NOTEBOOK_ENCRYPTION_KEY=change-me-to-a-secret-string

      # Database (SeekDB with MySQL protocol)
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

**Edit the file:**
- Replace `change-me-to-a-secret-string` with your own secret (any string works)
- Create a `scripts/` folder with the [seekdb-start-fixed.sh](https://raw.githubusercontent.com/lfnovo/open-notebook/main/scripts/seekdb-start-fixed.sh) script, or remove the entrypoint override if not needed.

---

## Step 2: Start Services (1 min)

Open terminal in your `open-notebook` folder:

```bash
docker compose up -d
```

Wait 15-20 seconds for services to start.

---

## Step 3: Access Open Notebook (instant)

Open your browser:
```
http://localhost:8502
```

You should see the Open Notebook interface!

---

## Step 4: Configure Your AI Provider (1 min)

1. Go to **Settings** → **API Keys**
2. Click **Add Credential**
3. Select your provider (e.g., Anthropic, Google, Groq, OpenRouter)
4. Give it a name, paste your API key
5. Click **Save**
6. Click **Test Connection** — should show success
7. Click **Discover Models** → **Register Models**

Your provider's models are now available!

> **Multiple providers**: You can add credentials for as many providers as you want. Just repeat this step for each provider.

---

## Step 5: Configure Your Model (1 min)

1. Go to **Settings** (gear icon)
2. Navigate to **Models**
3. Select your provider's model:

| Provider | Recommended Model | Notes |
|----------|-------------------|-------|
| **OpenRouter** | `anthropic/claude-3.5-sonnet` | Access 100+ models |
| **Anthropic** | `claude-3-5-sonnet-latest` | Best reasoning |
| **Google** | `gemini-2.0-flash` | Large context, fast |
| **Groq** | `llama-3.3-70b-versatile` | Ultra-fast |
| **Mistral** | `mistral-large-latest` | Strong European option |

4. Click **Save**

---

## Step 6: Create Your First Notebook (1 min)

1. Click **New Notebook**
2. Name: "My Research"
3. Click **Create**

---

## Step 7: Add Content & Chat (2 min)

1. Click **Add Source**
2. Choose **Web Link**
3. Paste any article URL
4. Wait for processing
5. Go to **Chat** and ask questions!

---

## Verification Checklist

- [ ] Docker is running
- [ ] You can access `http://localhost:8502`
- [ ] Provider credential is configured and tested
- [ ] Models are registered
- [ ] You created a notebook
- [ ] Chat works

**All checked?** You're ready to research!

---

## Provider Comparison

| Provider | Speed | Quality | Context | Cost |
|----------|-------|---------|---------|------|
| **OpenRouter** | Varies | Varies | Varies | Varies (100+ models) |
| **Anthropic** | Medium | Excellent | 200K | $$$ |
| **Google** | Fast | Very Good | 1M+ | $$ |
| **Groq** | Ultra-fast | Good | 128K | $ (free tier) |
| **Mistral** | Fast | Good | 128K | $$ |
| **DeepSeek** | Medium | Very Good | 64K | $ |

---

## Troubleshooting

### "Model not found" Error

1. Go to **Settings** → **API Keys**
2. Click **Test Connection** on your credential
3. If valid, click **Discover Models** → **Register Models**
4. Check you have credits/access for the model

### "Cannot connect to server"

```bash
docker ps  # Check all services running
docker compose logs  # View logs
docker compose restart  # Restart everything
```

### Provider-Specific Issues

**Anthropic**: Ensure key starts with `sk-ant-`
**Google**: Use AI Studio key, not Cloud Console
**Groq**: Free tier has rate limits; upgrade if needed

---

## Cost Estimates

Approximate costs per 1K tokens:

| Provider | Input | Output |
|----------|-------|--------|
| Anthropic (Sonnet) | $0.003 | $0.015 |
| Google (Flash) | $0.0001 | $0.0004 |
| Groq (Llama 70B) | Free tier available | - |
| Mistral (Large) | $0.002 | $0.006 |

Check provider websites for current pricing.

---

## Next Steps

1. **Add Your Content**: PDFs, web links, documents
2. **Explore Features**: Podcasts, transformations, search
3. **Full Documentation**: [See all features](../3-USER-GUIDE/index.md)

---

**Need help?** Join our [Discord community](https://discord.gg/37XJPXfz2w)!
