# Rollback Plan — Bayesian-AGI-Core MCP Server

## Trigger Conditions

Rollback is required if any of these occur within 30 minutes of deployment:

| Condition | Threshold |
|-----------|-----------|
| Error rate (5xx) | > 5% of requests |
| P95 latency | > 2s sustained for 5 minutes |
| Task queue backlog | > 1000 items not draining |
| Container OOM/crash loop | > 2 restarts in 5 minutes |
| Memory growth | Not plateauing after 15 minutes |

## Rollback Steps

### 1. Restore Container Image (if using tagged image)

```bash
docker service update --image bayesian-agi-core:previous hengshu-mcp
# or
docker-compose -f docker-compose.yml up -d hengshu-mcp
```

### 2. Revert File Changes (if using bind mount / live code)

```bash
# On server
cd /opt/hengsu-mcp

# Restore from git (assuming a git-backed deployment)
git checkout HEAD~1 -- src/mcp_server.py src/core/

# Or restore from backup tarball created at deploy time
tar -xzf backup-$(date -d '1 hour ago' +%Y%m%d-%H%M%S).tar.gz

# Restart container
docker restart hengshu-mcp
```

### 3. Verify Rollback

```bash
# Health check
curl -s http://localhost:8090/health

# Confirm old version
curl -s http://localhost:8090/ | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['version'])"

# Confirm tools available
curl -s http://localhost:8090/tools | python3 -c "import sys,json; print(len(json.load(sys.stdin)['tools']), 'tools')"
```

### 4. Notify

- Log the rollback reason and duration
- Tag the deployment in git with `rollback-YYYYMMDD-HHMMSS`

## Deploy Checklist (Prevention)

Before future deploys:

- [ ] Run `test_stress.py` on staging first
- [ ] Run `test_mcp_server.py` tests
- [ ] Check memory growth plateaus (`GET /metrics` → `bayesian_memory_free_energy`)
- [ ] Verify no syntax errors or import failures (`docker exec hengshu-mcp python3 -c "import mcp_server"`)
- [ ] Create backup tarball of current code (`tar -czf backup-$(date +%Y%m%d-%H%M%S).tar.gz src/`)

## Alerting Rules (Prometheus)

```yaml
groups:
  - name: bayesian-agi-core
    rules:
      - alert: HighTaskQueueBacklog
        expr: bayesian_task_queue_size > 100
        for: 5m
        annotations:
          summary: "Task queue backlog > 100 for 5 minutes"

      - alert: CriticalFreeEnergy
        expr: bayesian_memory_free_energy > 0.8
        for: 2m
        annotations:
          summary: "Free energy critically high, memory may be overloaded"

      - alert: HighMemoryUsage
        expr: bayesian_memory_items > 5000
        for: 5m
        annotations:
          summary: "Memory item count exceeds 5000"

      - alert: WorkerFailure
        expr: bayesian_workers_active < 2
        for: 1m
        annotations:
          summary: "Less than 2 task workers active"
```

## Time Budget

| Step | Target Duration |
|------|----------------|
| Detect failure | < 1 min |
| Decide to rollback | < 30 sec |
| Execute rollback | < 1 min |
| Verify recovery | < 30 sec |
| **Total** | **< 3 min** |
