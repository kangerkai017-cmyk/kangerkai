# Invalid partial run

This directory is retained only as a failure record.

- Intended run: Qwen3.5-9B-Q5_K_M expanded 58-task benchmark.
- Date: 2026-06-17.
- Status: invalid, partial, not for manuscript reporting.
- Completed rows before stop: 4 raw rows from task `task-高处作业-001`.
- Failure mode: retrieval-enabled variants produced `LLM output truncated for TrainingOutput; finish_reason=length`.
- Additional issue: local Qwen latency was approximately 150-180 seconds per early variant under the full benchmark configuration.

Do not aggregate this directory with valid benchmark results.
