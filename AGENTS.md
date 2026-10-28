# AGENTS.md

## Agent skills

### Issue tracker

Local markdown files under `.scratch/<feature-slug>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five canonical labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context (`GLOSSARY.md` and `docs/adr/` at repo root). See `docs/agents/domain.md`.

### Douyin operator & MCP tools

Operate the Douyin Crawler and Edit Studio analysis pipeline (`crawl_and_send_top_videos`, `search_top_videos`, `trigger_crawl`, `send_videos_to_analysis`, `get_system_status`, `configure_analysis_server`) when asked to crawl Douyin channels/keywords/links, rank videos by highest hearts (`digg_count`), or send videos to the analysis server. See `.agents/skills/douyin-operator/SKILL.md` and `docs/MCP_AGENT_GUIDE.md`.
