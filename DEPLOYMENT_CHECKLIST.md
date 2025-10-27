# Deployment and Validation Checklist

This checklist guides the deployment and final validation of the Ollama integration.

## Pre-Deployment

- [ ] Review all code changes
- [ ] Run module tests: `python test_minimal_acceptance.py`
- [ ] Verify CodeQL security scan passed (0 vulnerabilities)
- [ ] Check dependency vulnerabilities cleared
- [ ] Review documentation (OLLAMA_INTEGRATION.md)

## Deployment Steps

### 1. Environment Setup

- [ ] Ensure Docker and Docker Compose are installed
- [ ] Verify adequate system resources:
  - CPU: 4+ cores recommended
  - RAM: 8GB+ available
  - Disk: 10GB+ free space for models

### 2. Configuration

- [ ] Copy `.env.example` to `.env`
- [ ] Set `OLLAMA_BASE_URL=http://ollama:11434`
- [ ] (Optional) Configure Firestore if needed
- [ ] (Optional) Add GOOGLE_API_KEY for Gemini fallback

### 3. Start Services

```bash
# Start all services
docker compose up -d

# Check status
docker compose ps

# Expected: both tamagotchi-ollama and tamagotchi-pet healthy
```

- [ ] Ollama service status: `healthy`
- [ ] Tamagotchi service status: `healthy`

### 4. Initialize Ollama Model

```bash
# Run initialization script
./init-ollama.sh

# Or manually:
docker exec tamagotchi-ollama ollama pull llama3.2:3b
```

- [ ] Model pull completed successfully
- [ ] Verify model: `docker exec tamagotchi-ollama ollama list`
- [ ] Test generation: See init-ollama.sh output for test result

### 5. Verify Backend Connection

```bash
# Test health endpoint
curl http://localhost:8080/health

# Expected: {"status":"ok"}
```

- [ ] Health check returns OK
- [ ] No errors in logs: `docker compose logs tamagotchi`

## Functional Testing

### 6. Test Basic Interaction

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user",
    "message": "Olá, como você está?"
  }'
```

- [ ] Response received
- [ ] Response is coherent
- [ ] No errors in logs

### 7. Run Full Acceptance Tests

```bash
# Install dependencies if needed
pip install -r requirements.txt

# Run full acceptance tests
python test_acceptance.py
```

- [ ] Test 1: C&C Promise - PASSED
- [ ] Test 2: Style Change - PASSED
- [ ] Test 3: Topic Switching - PASSED
- [ ] Test 4: SCG Error Detection - PASSED
- [ ] Test 5: Telemetry - PASSED

### 8. Verify Metrics

```bash
# Get metrics summary
curl http://localhost:8080/metrics

# Get detailed report
curl http://localhost:8080/metrics/report
```

- [ ] Metrics endpoint accessible
- [ ] Latency p50 < 3000ms (adjust based on hardware)
- [ ] Consistency rate visible
- [ ] Token counts tracked

## Performance Validation

### 9. Measure Self-Consistency Rate

Run 20+ conversations and check metrics:

```bash
# After 20+ interactions
curl http://localhost:8080/metrics/report?recent=20
```

**Target:** Self-Consistency Rate ≥ 95%

- [ ] Measured consistency rate: _____%
- [ ] Target met (≥95%) OR documented acceptable level

### 10. Measure Token Reduction

Compare with baseline (if available):

- [ ] Avg tokens/turn measured: _____
- [ ] Compared to baseline: _____%
- [ ] Target met (20% reduction) OR context improved

### 11. Measure Commitment Resolution

Track promises over multiple sessions:

- [ ] Commitments created: _____
- [ ] Commitments fulfilled: _____
- [ ] Resolution rate: _____%
- [ ] Target met (≥80%)

## Load Testing (Optional but Recommended)

### 12. Concurrent Requests

Test with multiple users:

```bash
# Use a load testing tool like Apache Bench
ab -n 100 -c 10 -p payload.json -T application/json \
  http://localhost:8080/webhook
```

- [ ] All requests completed
- [ ] No errors under load
- [ ] Response times acceptable
- [ ] Resource usage stable

## Production Readiness

### 13. Monitoring Setup

- [ ] Metrics endpoint integrated with monitoring system
- [ ] Alerts configured for:
  - High latency (p95 > threshold)
  - Low consistency rate (< 95%)
  - Service health failures
  - High error rates

### 14. Backup and Recovery

- [ ] Ollama models volume backed up
- [ ] Firestore data backed up (if used)
- [ ] Recovery procedure documented
- [ ] Tested restore from backup

### 15. Resource Limits

Edit `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 4G
      cpus: '2'
    reservations:
      memory: 2G
      cpus: '1'
```

- [ ] Resource limits set
- [ ] Tested under limits
- [ ] No OOM or CPU throttling

## Documentation

### 16. Deployment Guide

- [ ] Internal deployment guide created
- [ ] Runbook for common issues
- [ ] Escalation procedures defined
- [ ] Training materials prepared

### 17. User Documentation

- [ ] User-facing features documented
- [ ] API changes (if any) documented
- [ ] Migration guide (if needed)

## Security

### 18. Security Review

- [ ] CodeQL scan passed (0 vulnerabilities)
- [ ] Dependency scan passed
- [ ] No secrets in code/config
- [ ] Environment variables properly secured
- [ ] Network access restricted (if needed)

### 19. Privacy Compliance

- [ ] Local inference confirmed (no external API calls when Ollama is used)
- [ ] Data retention policy reviewed
- [ ] User consent obtained (if required)

## Final Sign-Off

### 20. Acceptance Criteria

Review `ACCEPTANCE_VERIFICATION.md`:

- [ ] Infrastructure: 3/3 ✅
- [ ] Integration: 3/3 ✅
- [ ] API Contract: 2/2 ✅
- [ ] Telemetry: 2/2 ✅
- [ ] Tests: 4/4 ✅
- [ ] Final Criteria: 3/3 ✅
- [ ] Operational Policies: 5/5 ✅

**Total:** 22/22 (100%)

### 21. Stakeholder Approval

- [ ] Product Owner reviewed
- [ ] Technical Lead approved
- [ ] Security team signed off
- [ ] Operations team ready

### 22. Go/No-Go Decision

**Date:** __________  
**Decision:** GO / NO-GO  
**Approved by:** __________  

**Notes:**
```
[Add any final notes, concerns, or action items here]
```

## Post-Deployment

### 23. Monitoring (First 24h)

- [ ] Hour 1: Check metrics, no errors
- [ ] Hour 4: Review telemetry, performance stable
- [ ] Hour 12: Consistency rate acceptable
- [ ] Hour 24: All systems green, ready for full rollout

### 24. Gradual Rollout (If Applicable)

- [ ] 10% traffic: Monitoring looks good
- [ ] 25% traffic: No issues detected
- [ ] 50% traffic: Performance stable
- [ ] 100% traffic: Full deployment complete

## Rollback Plan

If issues arise:

1. **Immediate:** Revert to Gemini API
   ```bash
   # Comment out Ollama in docker-compose.yml
   docker compose up -d --force-recreate tamagotchi
   ```

2. **Investigation:** Check logs
   ```bash
   docker compose logs ollama
   docker compose logs tamagotchi
   ```

3. **Fix Forward:** Address specific issue and redeploy

## Success Criteria

✅ All 22 acceptance criteria met  
✅ Consistency rate ≥ 95%  
✅ Token reduction ≥ 20% OR improved context quality  
✅ No security vulnerabilities  
✅ Performance meets SLA  
✅ Monitoring in place  
✅ Team trained and ready  

**Status:** READY FOR DEPLOYMENT ✅

---

**Last Updated:** [Date]  
**Updated By:** [Name]  
**Version:** 1.0
