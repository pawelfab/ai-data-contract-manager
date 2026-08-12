# Changelog

## 2.0.0

- Added dedicated `Planner Fast` and `Feature Fast` agents without subagent tooling.
- Split planning and implementation into fast and reviewed slash commands.
- Added preview-only planning and reviewer-only diff review.
- Preserved automatic architecture documentation synchronization in both implementation workflows.
- Added deterministic documentation impact suggestions.
- Hardened freshness marking against marker-only or generated-file-only updates.
- Added explicit, recorded no-documentation-impact exception.
- Added per-session source baselines so the Stop hook blocks only sessions that changed source.
- Added workflow setup validation and initialization scripts.
- Added migration instructions from the first package version.
