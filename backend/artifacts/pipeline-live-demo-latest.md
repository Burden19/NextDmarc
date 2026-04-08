# NextDmarc Live Pipeline Proof

- Generated: 2026-04-07 09:34:17 +01:00
- Mode: executed

## Stage by stage evidence
| Stage | Worker task | What it does | Key output | Proof test | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Collect | app.workers.tasks.collect.collect_mailbox_reports | Fetch unseen mailbox messages, apply idempotency, and upload report objects. | fetched_messages, processed_messages, skipped_messages, uploaded_objects | tests/test_collect_task.py::test_collect_task_applies_message_idempotency | PASS | 1 passed in 2.45s |
| Parse | app.workers.tasks.parse.parse_report_object | Read report object, parse DMARC XML, persist report, and index records. | report_id, report_db_id, record_count, indexed_count | tests/test_parse_task.py::test_parse_task_pipeline_reads_parses_persists_and_indexes | PASS | 1 passed in 3.36s |
| Analyze | app.workers.tasks.analysis.analyze_report_conformance | Compute SPF, DKIM, DMARC pass counts and conformance rate. | total_records, dkim_pass_count, spf_pass_count, dmarc_pass_count, conformance_rate | tests/test_analysis_task.py::test_analysis_worker_computes_metrics_and_enqueues_followups | PASS | 1 passed in 3.28s |
| Correlate | app.workers.tasks.correlate.detect_correlations | Detect suspicious signals and create incidents for risky patterns. | signals_detected, incidents_created, alerts_enqueued | tests/test_correlate_task.py::test_correlate_task_enqueues_alert_dispatch_jobs | PASS | 1 passed in 3.27s |
| Score | app.workers.tasks.score.compute_score | Compute tenant risk score and risk state with penalty breakdown. | score, risk_state, conformance_penalty, dkim_penalty, spf_penalty | infra/tests/test_score_task.py::test_compute_score_task_persists_current_and_history | PASS | 1 passed in 1.83s |
| Recommend | app.workers.tasks.recommend.generate_recommendations | Generate remediation recommendations and maturity score. | maturity_score, maturity_level, recommendations_count | tests/test_recommend_task.py::test_recommend_task_persists_current_and_history | PASS | 1 passed in 1.67s |
| Alert | app.workers.tasks.alert.create_and_dispatch_alert | Create alert, route to channels, store audit, and publish realtime events. | target_channels, delivered_channels, failed_channels | tests/test_alert_task.py::test_alert_worker_creates_and_dispatches_channels | PASS | 1 passed in 3.44s |
| Collect-Parse Integration | collect -> parse | Prove handoff from mailbox collection to parser persistence and indexing. | record_count, indexed_count, report_id | tests/test_pipeline_integration.py::test_collect_parse_persist_index_integration | PASS | 1 passed in 4.64s |

## Raw command used
- pytest selectors executed individually with -q
