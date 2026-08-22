# Bayesian-AGI-Core Production Runbook
# Bayesian-AGI-Core 生产环境故障手册

## 📋 Overview
This runbook documents known failure scenarios, detection methods, and recovery procedures identified through chaos engineering testing.

本文档记录了通过混沌工程测试发现的已知故障场景、检测方法和恢复流程。

---

## 🚨 Incident Severity Levels

| Level | Description | Response Time | Escalation |
|-------|-------------|---------------|-----------|
| **P0** | System Down | 15 mins | All hands |
| **P1** | Major Degradation | 30 mins | Engineering lead |
| **P2** | Partial Degradation | 1 hour | On-call engineer |
| **P3** | Minor Issue | Next business day | Support team |

---

## 🔍 Scenario 1: Circuit Breaker Open (熔断器触发)

### Symptom (症状)
- API returns "Service Unavailable"
- Logs show `Circuit 'XXX' is OPEN`
- `/api/circuit-breakers` shows state = OPEN

### Detection (检测)
```bash
# Check circuit breaker state
curl http://localhost:8001/api/health/robustness

# Look for OPEN circuits in logs
grep "tripped to OPEN" logs/app.log
```

### Root Causes (根因)
1. External API (Ollama) is down or slow
2. Database connection pool exhausted
3. Network partition between services

### Recovery Steps (恢复步骤)

#### Step 1: Verify Circuit State (验证熔断器状态)
```python
from src.utils.circuit_breaker import CircuitBreakerManager

circuits = CircuitBreakerManager.list_circuits()
for name, state in circuits.items():
    print(f"{name}: {state}")
```

#### Step 2: Check Dependent Services (检查依赖服务)
```bash
# Check Ollama
curl http://192.168.3.105:11434/api/tags

# Check database connection
# (database-specific command)
```

#### Step 3: Manual Reset (手动重置 - 仅当问题已修复时)
```bash
# Reset specific circuit
curl -X POST http://localhost:8001/api/circuit-breakers/ollama_service/reset

# Reset all circuits (caution!)
curl -X POST http://localhost:8001/api/circuit-breakers/reset-all
```

#### Step 4: Verify Recovery (验证恢复)
```bash
# Send test requests
for i in {1..5}; do
    curl http://localhost:8001/health
    sleep 1
done
```

### Prevention (预防措施)
- Configure appropriate failure thresholds in `config.yaml`
- Set up alerts for circuit state changes
- Implement fallback logic for critical paths

### Expected MTTR (预期恢复时间)
- **Detection**: 2 minutes (via alerts)
- **Diagnosis**: 5 minutes
- **Recovery**: 3 minutes
- **Total**: **10 minutes**

---

## 🚦 Scenario 2: Rate Limiting Active (限流触发)

### Symptom (症状)
- API returns "429 Too Many Requests"
- Logs show `Rate limit exceeded for key: XXX`
- System throughput drops to configured limit

### Detection (检测)
```bash
# Check rate limiter stats
curl http://localhost:8001/api/rate-limiters/per_user/stats?key=test_user

# Look for rate limit warnings
grep "Rate limit exceeded" logs/app.log
```

### Root Causes (根因)
1. Single user/IP sending too many requests
2. Attack (DDoS)
3. Misconfigured limit (too low)

### Recovery Steps (恢复步骤)

#### Step 1: Identify Offending Key (识别违规方)
```python
from src.utils.rate_limiter import get_rate_limiter_manager

manager = get_rate_limiter_manager()
# Check logs for specific keys
```

#### Step 2: Verify if Legitimate Traffic (验证是否为合法流量)
- Check user agent and IP
- Look for patterns in request timing
- Verify business justification

#### Step 3: Adjust Limits Temporarily (临时调整限制)
```yaml
# Edit config.yaml - resilience.rate_limiters
per_user:
  enabled: true
  type: "token_bucket"
  requests: 100  # Increase from 60
  period_seconds: 60
  burst_size: 30
```

#### Step 4: Apply and Reload (应用并重载配置)
```bash
# Configuration will be picked up on next request
# Or implement explicit reload endpoint
```

### Prevention (预防措施)
- Use tiered limits (free vs. paid users)
- Implement dynamic rate limiting based on user behavior
- Set up alerts for high rate limiting volume

### Expected MTTR (预期恢复时间)
- **Detection**: 1 minute
- **Diagnosis**: 3 minutes
- **Recovery**: 2 minutes
- **Total**: **6 minutes**

---

## 📊 Scenario 3: High Error Rate (高错误率)

### Symptom (症状)
- Error rate > 5% threshold
- Logs show many exceptions
- Users report issues

### Detection (检测)
```bash
# Check error count metrics
# Look at Prometheus metrics (if integrated)

# Check recent errors in logs
tail -50 logs/app.log | grep ERROR
```

### Root Causes (根因)
1. Bug in recent deployment
2. Dependent service error
3. Invalid input handling

### Recovery Steps (恢复步骤)

#### Step 1: Check Deployment (检查部署)
```bash
# Check if recent deployment happened
git log --oneline -n 10

# Consider rolling back if needed
git revert HEAD
```

#### Step 2: Correlate with Errors (关联错误信息)
```bash
# Find common error patterns
grep "ERROR" logs/app.log | awk '{print $NF}' | sort | uniq -c | sort -nr
```

#### Step 3: Implement Hotfix (实施热修复)
```python
# Deploy critical fix
# Follow change management process
```

### Prevention (预防措施)
- Canary deployments
- Feature flags
- Extensive integration tests

### Expected MTTR (预期恢复时间)
- **Detection**: 3 minutes
- **Diagnosis**: 15 minutes
- **Recovery**: 10 minutes
- **Total**: **28 minutes**

---

## 🔧 Scenario 4: Memory Leak / High Resource Usage (内存泄漏/高资源占用)

### Symptom (症状)
- Memory usage > 80% and growing
- GC pauses increasing
- System becoming unresponsive

### Detection (检测)
```bash
# Check process
ps aux | grep python

# Check memory usage
top -p <PID>

# Check logs for OOM
grep "Out of memory" logs/app.log
```

### Root Causes (根因)
1. Cache not evicting old entries
2. Unbounded collection growth
3. Large object retention

### Recovery Steps (恢复步骤)

#### Step 1: Restart Service (重启服务)
```bash
# Graceful restart
kill -SIGTERM <PID>

# Or use process manager
systemctl restart bayesian-agi
```

#### Step 2: Analyze Heap Dump (分析堆转储 - 可选)
```python
# Use tools like:
# - tracemalloc
# - objgraph
# - py-spy
```

### Prevention (预防措施)
- Monitor GC metrics
- Set memory limits in containers
- Regular load testing

### Expected MTTR (预期恢复时间)
- **Detection**: 5 minutes
- **Diagnosis**: 30 minutes
- **Recovery**: 5 minutes
- **Total**: **40 minutes**

---

## 📞 On-Call Procedures (值班流程)

### Initial Checklist (初始检查清单)
1. [ ] Check monitoring dashboards
2. [ ] Check recent deployments
3. [ ] Check logs for errors
4. [ ] Verify external dependencies
5. [ ] Acknowledge alert

### Communication (沟通)
- Update incident ticket every 30 minutes
- Inform stakeholders of estimated resolution time
- Post-mortem within 48 hours of resolution

### Escalation Path (升级路径)
1. On-call engineer (first responder)
2. Engineering lead (if > 30 minutes)
3. All engineering (if > 1 hour)

---

## 🎯 Quick Reference (快速参考)

### Useful Commands (常用命令)

#### Health Checks (健康检查)
```bash
# Basic health
curl http://localhost:8001/health

# Detailed health
curl http://localhost:8001/api/health/robustness
```

#### Circuit Breakers (熔断器)
```bash
# List all circuits
curl http://localhost:8001/api/circuit-breakers

# Reset circuit
curl -X POST http://localhost:8001/api/circuit-breakers/{name}/reset
```

#### Rate Limiters (限流器)
```bash
# List all limiters
curl http://localhost:8001/api/rate-limiters

# Get stats
curl "http://localhost:8001/api/rate-limiters/{name}/stats?key={key}"
```

#### Logs (日志)
```bash
# Follow app log
tail -f logs/app.log

# Follow daily log
tail -f logs/daily.log

# Search for errors
grep ERROR logs/app.log
```

### Configuration (配置)

#### Location (位置)
```
config.yaml
```

#### Key Sections (关键章节)
- `resilience.circuit_breakers` - Circuit breaker settings
- `resilience.rate_limiters` - Rate limiter settings
- `resilience.alerts` - Alerting thresholds

---

## 📈 Post-Incident Analysis (事后分析)

### Report Template (报告模板)

#### 1. Summary (概述)
- Date/Time:
- Impact:
- Duration:
- Root Cause:

#### 2. Timeline (时间线)
```
00:00 - Alert received
00:05 - On-call engineer starts diagnosis
00:15 - Root cause identified
00:25 - Recovery complete
00:30 - Service restored
```

#### 3. Root Cause (根因分析)
- Technical details:
- Contributing factors:

#### 4. What Worked (做得好的地方)
- Detection:
- Response:
- Recovery:

#### 5. What Didn't Work (待改进)
- Gaps in monitoring:
- Delays:

#### 6. Action Items (改进措施)
| Action | Owner | Due Date |
|--------|-------|----------|
| Item 1 | Name | YYYY-MM-DD |
| Item 2 | Name | YYYY-MM-DD |

---

## 🔗 Related Documents (相关文档)
- `/docs/ROBUSTNESS_GUIDE.md` - Resilience patterns usage
- `/docs/adr/0001-resilience-patterns.md` - Architecture decisions
- `config.yaml` - Configuration reference

---

*Last Updated: 2026-05-26*
