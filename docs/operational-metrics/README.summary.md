# Phase-End Operational Metrics — Summary

Every phase must now end with operational checks:

- cost,
- latency,
- scalability,
- reliability,
- API outage behavior,
- bottlenecks.

The dashboard reads:

```text
docs/operational-metrics/status.json
```

Current important gaps:

- Phase 1A has unit and workflow evidence, but no full operational measurement
  package yet.
- OpenAI Moderation API failure currently degrades to inconclusive/pass and
  needs release triage.
- Scenario-level concurrency has not been load-tested.
- Cost guardrail behavior still needs an integration test.
