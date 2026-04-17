SHELL := /bin/bash

.PHONY: run frontend check ruff database database-seekdb lint api start-all start-all-seekdb stop-all status clean-cache worker worker-start worker-stop worker-restart verify-seekdb
.PHONY: seekdb-dev-up seekdb-dev-stop seekdb-dev-status seekdb-dev-logs
.PHONY: docker-buildx-prepare docker-buildx-clean docker-buildx-reset
.PHONY: docker-push docker-push-latest docker-release docker-build-local tag export-docs

# Get version from pyproject.toml
VERSION := $(shell grep -m1 version pyproject.toml | cut -d'"' -f2)

# Image names for both registries
DOCKERHUB_IMAGE := lfnovo/open_notebook
GHCR_IMAGE := ghcr.io/lfnovo/open-notebook

# Build platforms
PLATFORMS := linux/amd64,linux/arm64
SEEKDB_ENV_FILE ?= .env.seekdb
SEEKDB_JOB_BACKEND ?= arq
SEEKDB_REDIS_URL ?= redis://127.0.0.1:6379/0
SEEKDB_UV_ENV_ARGS := $(if $(wildcard $(SEEKDB_ENV_FILE)),--env-file $(SEEKDB_ENV_FILE),)
SEEKDB_COMPOSE := docker compose -f docker-compose.dev.yml -f docker-compose.seekdb.yml
SEEKDB_RUN_DIR := .run/seekdb-dev
SEEKDB_LOG_DIR := .logs/seekdb-dev
SEEKDB_API_PID := $(SEEKDB_RUN_DIR)/api.pid
SEEKDB_WORKER_PID := $(SEEKDB_RUN_DIR)/worker.pid
SEEKDB_FRONTEND_PID := $(SEEKDB_RUN_DIR)/frontend.pid

database:
	docker compose up -d seekdb redis

database-seekdb:
	docker compose -f docker-compose.dev.yml -f docker-compose.seekdb.yml up -d seekdb redis

run:
	@echo "⚠️  Warning: Starting frontend only. For full functionality, use 'make start-all'"
	cd frontend && npm run dev

frontend:
	cd frontend && npm run dev

lint:
	uv run python -m mypy .

ruff:
	ruff check . --fix

# === Docker Build Setup ===
docker-buildx-prepare:
	@docker buildx inspect multi-platform-builder >/dev/null 2>&1 || \
		docker buildx create --use --name multi-platform-builder --driver docker-container
	@docker buildx use multi-platform-builder

docker-buildx-clean:
	@echo "🧹 Cleaning up buildx builders..."
	@docker buildx rm multi-platform-builder 2>/dev/null || true
	@docker ps -a | grep buildx_buildkit | awk '{print $$1}' | xargs -r docker rm -f 2>/dev/null || true
	@echo "✅ Buildx cleanup complete!"

docker-buildx-reset: docker-buildx-clean docker-buildx-prepare
	@echo "✅ Buildx reset complete!"

# === Docker Build Targets ===

# Build production image for local platform only (no push)
docker-build-local:
	@echo "🔨 Building production image locally ($(shell uname -m))..."
	docker build \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(DOCKERHUB_IMAGE):local \
		.
	@echo "✅ Built $(DOCKERHUB_IMAGE):$(VERSION) and $(DOCKERHUB_IMAGE):local"
	@echo "Run with: docker run -p 5055:5055 -p 3000:3000 $(DOCKERHUB_IMAGE):local"

# Build and push version tags ONLY (no latest) for both regular and single images
docker-push: docker-buildx-prepare
	@echo "📤 Building and pushing version $(VERSION) to both registries..."
	@echo "🔨 Building regular image..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(GHCR_IMAGE):$(VERSION) \
		--push \
		.
	@echo "🔨 Building single-container image..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-f Dockerfile.single \
		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
		-t $(GHCR_IMAGE):$(VERSION)-single \
		--push \
		.
	@echo "✅ Pushed version $(VERSION) to both registries (latest NOT updated)"
	@echo "  📦 Docker Hub:"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)-single"
	@echo "  📦 GHCR:"
	@echo "    - $(GHCR_IMAGE):$(VERSION)"
	@echo "    - $(GHCR_IMAGE):$(VERSION)-single"

# Update v1-latest tags to current version (both regular and single images)
docker-push-latest: docker-buildx-prepare
	@echo "📤 Updating v1-latest tags to version $(VERSION)..."
	@echo "🔨 Building regular image with latest tag..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-t $(DOCKERHUB_IMAGE):$(VERSION) \
		-t $(DOCKERHUB_IMAGE):v1-latest \
		-t $(GHCR_IMAGE):$(VERSION) \
		-t $(GHCR_IMAGE):v1-latest \
		--push \
		.
	@echo "🔨 Building single-container image with latest tag..."
	docker buildx build --pull \
		--platform $(PLATFORMS) \
		--progress=plain \
		-f Dockerfile.single \
		-t $(DOCKERHUB_IMAGE):$(VERSION)-single \
		-t $(DOCKERHUB_IMAGE):v1-latest-single \
		-t $(GHCR_IMAGE):$(VERSION)-single \
		-t $(GHCR_IMAGE):v1-latest-single \
		--push \
		.
	@echo "✅ Updated v1-latest to version $(VERSION)"
	@echo "  📦 Docker Hub:"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION) → v1-latest"
	@echo "    - $(DOCKERHUB_IMAGE):$(VERSION)-single → v1-latest-single"
	@echo "  📦 GHCR:"
	@echo "    - $(GHCR_IMAGE):$(VERSION) → v1-latest"
	@echo "    - $(GHCR_IMAGE):$(VERSION)-single → v1-latest-single"

# Full release: push version AND update latest tags
docker-release: docker-push-latest
	@echo "✅ Full release complete for version $(VERSION)"

tag:
	@version=$$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'); \
	echo "Creating tag v$$version"; \
	git tag "v$$version"; \
	git push origin "v$$version"


dev:
	docker compose -f docker-compose.dev.yml up --build 

full:
	docker compose -f docker-compose.full.yml up --build 


api:
	uv run --env-file .env run_api.py

.PHONY: worker worker-start worker-stop worker-restart

worker: worker-start

worker-start:
	@echo "Starting background worker..."
	@OPEN_NOTEBOOK_JOB_BACKEND=$(SEEKDB_JOB_BACKEND) OPEN_NOTEBOOK_REDIS_URL=$${OPEN_NOTEBOOK_REDIS_URL:-$(SEEKDB_REDIS_URL)} uv run $(SEEKDB_UV_ENV_ARGS) open-notebook-worker

worker-stop:
	@pkill -f "open-notebook-worker" || true

worker-restart: worker-stop
	@sleep 2
	@$(MAKE) worker-start

# === Service Management ===
start-all:
	@echo "🚀 Starting Open Notebook (SeekDB + Redis + API + Frontend)..."
	@echo "📊 Starting datastore and queue..."
	@docker compose -f docker-compose.dev.yml -f docker-compose.seekdb.yml up -d seekdb redis
	@sleep 3
	@echo "🔧 Starting API backend..."
	@OPEN_NOTEBOOK_JOB_BACKEND=$(SEEKDB_JOB_BACKEND) OPEN_NOTEBOOK_REDIS_URL=$${OPEN_NOTEBOOK_REDIS_URL:-$(SEEKDB_REDIS_URL)} uv run $(SEEKDB_UV_ENV_ARGS) run_api.py &
	@sleep 3
	@echo "⚙️ Starting background worker..."
	@OPEN_NOTEBOOK_JOB_BACKEND=$(SEEKDB_JOB_BACKEND) OPEN_NOTEBOOK_REDIS_URL=$${OPEN_NOTEBOOK_REDIS_URL:-$(SEEKDB_REDIS_URL)} uv run $(SEEKDB_UV_ENV_ARGS) open-notebook-worker &
	@echo "🌐 Starting Next.js frontend..."
	@echo "✅ All services started!"
	@echo "📱 Frontend: http://localhost:3000"
	@echo "🔗 API: http://localhost:5055"
	@echo "📚 API Docs: http://localhost:5055/docs"
	cd frontend && npm run dev

start-all-seekdb:
	@$(MAKE) seekdb-dev-up

seekdb-dev-up:
	@if [ ! -f "$(SEEKDB_ENV_FILE)" ]; then \
		echo "❌ Missing $(SEEKDB_ENV_FILE)."; \
		echo "   Create it first, for example: cp .env.seekdb.example $(SEEKDB_ENV_FILE)"; \
		exit 1; \
	fi
	@mkdir -p "$(SEEKDB_RUN_DIR)" "$(SEEKDB_LOG_DIR)"
	@echo "🚀 Starting Open Notebook dev stack with SeekDB..."
	@echo "📊 Starting SeekDB and Redis containers..."
	@$(SEEKDB_COMPOSE) up -d seekdb redis
	@echo "⏳ Waiting for SeekDB to be ready..."
	@uv run --env-file "$(SEEKDB_ENV_FILE)" python scripts/wait_for_seekdb_ready.py --timeout 240

	@api_running=false; \
	if ss -tlnp 2>/dev/null | grep -q ':5055 '; then \
		api_pid=$$(ss -tlnp 2>/dev/null | grep ':5055 ' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2); \
		if [ -n "$$api_pid" ]; then echo "🔧 API already running (pid $$api_pid, port 5055 confirmed)"; echo "$$api_pid" > "$(SEEKDB_API_PID)"; api_running=true; fi; \
	fi; \
	if [ "$$api_running" != "true" ]; then rm -f "$(SEEKDB_API_PID)"; echo "🔧 Starting API backend..."; \
		setsid bash -lc 'exec env API_RELOAD=false OPEN_NOTEBOOK_JOB_BACKEND="$(SEEKDB_JOB_BACKEND)" OPEN_NOTEBOOK_REDIS_URL="$${OPEN_NOTEBOOK_REDIS_URL:-$(SEEKDB_REDIS_URL)}" uv run --env-file "$(SEEKDB_ENV_FILE)" run_api.py' < /dev/null > "$(SEEKDB_LOG_DIR)/api.log" 2>&1 & echo $$! > "$(SEEKDB_API_PID)"; fi
	@echo "⏳ Waiting for API to become ready..."
	@for i in {1..60}; do \
		if curl -fsS http://127.0.0.1:5055/api/config >/dev/null 2>&1; then \
			echo "✅ API is ready"; \
			break; \
		fi; \
		if [ $$i -eq 60 ]; then \
			echo "❌ API did not become ready. Check $(SEEKDB_LOG_DIR)/api.log"; \
			exit 1; \
		fi; \
		sleep 2; \
	done
	@worker_running=false; \
	if [ -f "$(SEEKDB_WORKER_PID)" ] && kill -0 "$$(cat "$(SEEKDB_WORKER_PID)")" 2>/dev/null; then echo "⚙️ Worker already running (pid $$(cat "$(SEEKDB_WORKER_PID)"))"; worker_running=true; \
	else rm -f "$(SEEKDB_WORKER_PID)"; \
		existing_worker_pid="$$(ps -eo pid=,args= | grep -E '[o]pen-notebook-worker($$| )|uv run .*open-notebook-worker($$| )' | grep -v 'bash -lc' | awk 'NR==1 {print $$1}')"; \
		if [ -n "$$existing_worker_pid" ] && kill -0 "$$existing_worker_pid" 2>/dev/null; then echo "$$existing_worker_pid" > "$(SEEKDB_WORKER_PID)"; echo "⚙️ Worker already running (pid $$existing_worker_pid)"; worker_running=true; fi; \
	fi; \
	if [ "$$worker_running" != "true" ]; then echo "⚙️ Starting background worker..."; \
		setsid bash -lc 'exec env OPEN_NOTEBOOK_JOB_BACKEND="$(SEEKDB_JOB_BACKEND)" OPEN_NOTEBOOK_REDIS_URL="$${OPEN_NOTEBOOK_REDIS_URL:-$(SEEKDB_REDIS_URL)}" uv run --env-file "$(SEEKDB_ENV_FILE)" open-notebook-worker' < /dev/null > "$(SEEKDB_LOG_DIR)/worker.log" 2>&1 & echo $$! > "$(SEEKDB_WORKER_PID)"; \
		sleep 2; \
		if ! kill -0 "$$(cat "$(SEEKDB_WORKER_PID)")" 2>/dev/null; then \
			echo "❌ Worker failed to start. Check $(SEEKDB_LOG_DIR)/worker.log"; \
			tail -n 40 "$(SEEKDB_LOG_DIR)/worker.log" || true; \
			exit 1; \
		fi; \
	fi

	@frontend_running=false; \
	if ss -tlnp 2>/dev/null | grep -q ':3000 '; then \
		frontend_pid=$$(ss -tlnp 2>/dev/null | grep ':3000 ' | grep -o 'pid=[0-9]*' | head -1 | cut -d= -f2); \
		if [ -n "$$frontend_pid" ]; then echo "🌐 Frontend already running (pid $$frontend_pid, port 3000 confirmed)"; echo "$$frontend_pid" > "$(SEEKDB_FRONTEND_PID)"; frontend_running=true; fi; \
	fi; \
	if [ "$$frontend_running" != "true" ]; then rm -f "$(SEEKDB_FRONTEND_PID)"; echo "🌐 Starting Next.js frontend..."; \
		setsid bash -lc 'cd frontend && exec npm run dev' < /dev/null > "$(SEEKDB_LOG_DIR)/frontend.log" 2>&1 & echo $$! > "$(SEEKDB_FRONTEND_PID)"; \
		sleep 3; if ! ss -tlnp 2>/dev/null | grep -q ':3000 '; then echo "❌ Frontend failed to start. Check $(SEEKDB_LOG_DIR)/frontend.log"; exit 1; fi; \
	fi
	@echo "✅ SeekDB dev stack is up"
	@echo "📱 Frontend: http://localhost:3000"
	@echo "🔗 API: http://localhost:5055"
	@echo "📚 API Docs: http://localhost:5055/docs"
	@echo "🪵 Logs: $(SEEKDB_LOG_DIR)"
	@echo "📌 Status: make seekdb-dev-status"
	@echo "🛑 Stop: make seekdb-dev-stop"

seekdb-dev-stop:
	@echo "🛑 Stopping SeekDB dev stack..."
	$(info Stop services via PID files first, then fallback to pattern-based kill)
	@for pid_file in "$(SEEKDB_FRONTEND_PID)" "$(SEEKDB_WORKER_PID)" "$(SEEKDB_API_PID)"; do \
		if [ -f "$$pid_file" ]; then pid="$$(cat "$$pid_file")"; \
			if kill -0 "$$pid" 2>/dev/null; then kill "$$pid" 2>/dev/null || true; sleep 1; kill -9 "$$pid" 2>/dev/null || true; fi; \
			rm -f "$$pid_file"; fi; \
	done
	$(info Fallback: also kill by pattern to catch any orphaned processes)
	@api_pids="$$(ps -eo pid=,args= | grep -E '[r]un_api\\.py($$| )' | grep -v 'bash -lc' | awk '{print $$1}')"; \
	if [ -n "$$api_pids" ]; then echo "$$api_pids" | xargs -r kill 2>/dev/null || true; echo "🛑 Stopped orphaned API processes"; fi
	@worker_pids="$$(ps -eo pid=,args= | grep -E '[o]pen-notebook-worker($$| )|uv run .*open-notebook-worker($$| )' | grep -v 'bash -lc' | awk '{print $$1}')"; \
	if [ -n "$$worker_pids" ]; then echo "$$worker_pids" | xargs -r kill 2>/dev/null || true; echo "🛑 Stopped orphaned worker processes"; fi
	@frontend_pids="$$(ps -eo pid=,args= | grep -E '[n]ext dev($$| )' | grep -v 'bash -lc' | awk '{print $$1}')"; \
	if [ -n "$$frontend_pids" ]; then echo "$$frontend_pids" | xargs -r kill 2>/dev/null || true; echo "🛑 Stopped orphaned frontend processes"; fi
	@$(SEEKDB_COMPOSE) down
	@echo "✅ SeekDB dev stack stopped"

seekdb-dev-status:
	@echo "📊 SeekDB Dev Stack Status:"
	@echo "Containers:"
	@$(SEEKDB_COMPOSE) ps || true
	@echo "API:"
	@api_pid="$$(if [ -f "$(SEEKDB_API_PID)" ] && kill -0 "$$(cat "$(SEEKDB_API_PID)")" 2>/dev/null; then cat "$(SEEKDB_API_PID)"; else pgrep -f '$(CURDIR)/run_api.py' | head -n 1; fi)"; \
	if [ -n "$$api_pid" ] && kill -0 "$$api_pid" 2>/dev/null; then \
		echo "  ✅ Running (pid $$api_pid)"; \
	else \
		echo "  ❌ Not running"; \
	fi
	@echo "Worker:"
	@worker_pid="$$(if [ -f "$(SEEKDB_WORKER_PID)" ] && kill -0 "$$(cat "$(SEEKDB_WORKER_PID)")" 2>/dev/null; then cat "$(SEEKDB_WORKER_PID)"; else ps -eo pid=,args= | grep -E '[o]pen-notebook-worker($$| )|uv run .*open-notebook-worker($$| )' | grep -v 'bash -lc' | awk 'NR==1 {print $$1}'; fi)"; \
	if [ -n "$$worker_pid" ] && kill -0 "$$worker_pid" 2>/dev/null; then \
		echo "  ✅ Running (pid $$worker_pid)"; \
	else \
		echo "  ❌ Not running"; \
	fi
	@echo "Frontend:"
	@frontend_pid="$$(if [ -f "$(SEEKDB_FRONTEND_PID)" ] && kill -0 "$$(cat "$(SEEKDB_FRONTEND_PID)")" 2>/dev/null; then cat "$(SEEKDB_FRONTEND_PID)"; else pgrep -f '$(CURDIR)/frontend/node_modules/.bin/next dev' | head -n 1; fi)"; \
	if [ -n "$$frontend_pid" ] && kill -0 "$$frontend_pid" 2>/dev/null; then \
		echo "  ✅ Running (pid $$frontend_pid)"; \
	else \
		echo "  ❌ Not running"; \
	fi
	@echo "Logs:"
	@echo "  $(SEEKDB_LOG_DIR)/api.log"
	@echo "  $(SEEKDB_LOG_DIR)/worker.log"
	@echo "  $(SEEKDB_LOG_DIR)/frontend.log"

seekdb-dev-logs:
	@mkdir -p "$(SEEKDB_LOG_DIR)"
	@touch "$(SEEKDB_LOG_DIR)/api.log" "$(SEEKDB_LOG_DIR)/worker.log" "$(SEEKDB_LOG_DIR)/frontend.log"
	@tail -n 100 -f "$(SEEKDB_LOG_DIR)/api.log" "$(SEEKDB_LOG_DIR)/worker.log" "$(SEEKDB_LOG_DIR)/frontend.log"

stop-all:
	@echo "🛑 Stopping all Open Notebook services..."
	@pkill -f "next dev" || true
	@pkill -f "run_api.py" || true
	@pkill -f "uvicorn api.main:app" || true
	@docker compose down
	@echo "✅ All services stopped!"

status:
	@echo "📊 Open Notebook Service Status:"
	@echo "Datastore / Queue:"
	@docker compose ps seekdb redis 2>/dev/null || echo "  ❌ Not running"
	@echo "API Backend:"
	@pgrep -f "run_api.py\|uvicorn api.main:app" >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"
	@echo "Background Worker:"
	@ps -eo pid=,args= | grep -E '[o]pen-notebook-worker($$| )|uv run .*open-notebook-worker($$| )' | grep -v 'bash -lc' >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"
	@echo "Next.js Frontend:"
	@pgrep -f "next dev" >/dev/null && echo "  ✅ Running" || echo "  ❌ Not running"

verify-seekdb:
	uv run --env-file .env.seekdb python scripts/verify_seekdb_integration.py

# === Documentation Export ===
export-docs:
	@echo "📚 Exporting documentation..."
	@uv run python scripts/export_docs.py
	@echo "✅ Documentation export complete!"

# === Cleanup ===
clean-cache:
	@echo "🧹 Cleaning cache directories..."
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".mypy_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".ruff_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -type f -delete 2>/dev/null || true
	@find . -name "*.pyo" -type f -delete 2>/dev/null || true
	@find . -name "*.pyd" -type f -delete 2>/dev/null || true
	@echo "✅ Cache directories cleaned!"
