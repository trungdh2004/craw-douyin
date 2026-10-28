---
name: douyin-operator
description: Operate the Douyin Crawler and Edit Studio analysis pipeline via MCP tools or `uv run douyin-mcp`. Use when asked to crawl a Douyin channel/keyword/link, pick top highest-heart (`digg_count`) videos, send videos to the analysis server, check browser/Captcha status, or configure the analysis server IP and port.
---

# Douyin Operator Skill

Operate the running Douyin Crawler service (`http://127.0.0.1:8080`) either through the registered `douyin-crawler-mcp` MCP tools or via the CLI entrypoint `uv run douyin-mcp --tool <tool_name> --args '<json>'`. Both paths authenticate automatically using `.env` (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).

## Workflow Steps

1. **Verify readiness (`get_system_status`)**:
   - Call `get_system_status` to confirm the backend is reachable and check `browser_status` (`AUTHENTICATED`, `CAPTCHA_REQUIRED`, or `LOGIN_REQUIRED`) and `analysis_server.base_url`.
   - Completion criterion: `browser_status` and `analysis_server.base_url` are known before starting a crawl or analysis handoff.

2. **Execute the operator's request**:
   - **One-shot "crawl & send top N highest-heart videos"**: Call `crawl_and_send_top_videos` with `target_type` (`KEYWORD` | `CHANNEL` | `COLLECT`), `target_value`, `max_crawl_items` (default `30`), `top_n` (default `5`), and `exclude_already_analyzed: true` (default).
   - **Pick top N from already-crawled library without re-crawling**: Call `search_top_videos` with `sort: "digg_count"`, `order: "desc"`, `exclude_already_analyzed: true`, and `top_n`, then pass the chosen `aweme_ids` to `send_videos_to_analysis`.
   - **Crawl specific video links/IDs**: Call `trigger_crawl` with `mode: "SINGLE_LINKS"` and `inputs: [...]`, then call `send_videos_to_analysis` if the user wants them analyzed.
   - **Update analysis server IP/Port**: Call `configure_analysis_server` with `host` and `port`.
   - Completion criterion: The tool returns `status: "SUCCESS"` (for crawls) and/or `analysis_submission.sent_count > 0` (when sending to analysis).

3. **Report results**:
   - Present a concise table or bullet list of every selected/sent video showing:
     - `aweme_id`
     - `author_nickname`
     - `digg_count` (hearts)
     - `duration_sec`
     - `description`
     - `analysis_submission.studio_url` (direct link to view the batch or item in Edit Studio)
   - Completion criterion: Every video in `selected_videos` and the final `studio_url` are reported to the user.

## Tool & CLI Reference

When MCP tools are mounted in your environment, call them directly. When running via shell commands, invoke:

```bash
uv run --directory /home/trungdh/dev/tools/douyin douyin-mcp --tool <tool_name> --args '<json_payload>'
```

### 1. `crawl_and_send_top_videos`
Crawls a keyword/channel, waits for completion, selects top `top_n` videos by `digg_count` descending (skipping already-analyzed videos by default), downloads watermark-free MP4s, and pushes them to Edit Studio.

```bash
uv run douyin-mcp --tool crawl_and_send_top_videos --args '{
  "target_type": "KEYWORD",
  "target_value": "穿搭",
  "max_crawl_items": 30,
  "top_n": 5,
  "exclude_already_analyzed": true
}'
```

### 2. `search_top_videos`
Queries the local PostgreSQL video library sorted by `digg_count` (`desc`), `create_time`, `crawled_at`, or `duration_ms`.

```bash
uv run douyin-mcp --tool search_top_videos --args '{
  "search": "穿搭",
  "top_n": 5,
  "exclude_already_analyzed": true,
  "sort": "digg_count",
  "order": "desc"
}'
```

### 3. `send_videos_to_analysis`
Downloads watermark-free MP4s (if not yet downloaded) and sends the specified `aweme_ids` to the configured Edit Studio server.

```bash
uv run douyin-mcp --tool send_videos_to_analysis --args '{
  "aweme_ids": ["7355555555555555555"],
  "profile": "detailed"
}'
```

### 4. `trigger_crawl`
Runs a target crawl (`mode: "TARGET"`) or single-link crawl (`mode: "SINGLE_LINKS"`) and waits for completion.

```bash
uv run douyin-mcp --tool trigger_crawl --args '{
  "mode": "TARGET",
  "target_type": "CHANNEL",
  "target_value": "https://www.douyin.com/user/MS4wLjABAAAA...",
  "max_crawl_items": 30,
  "wait_for_completion": true
}'
```

### 5. `get_system_status` & `configure_analysis_server`
Check system/browser health or point the crawler at a different Edit Studio IP & Port:

```bash
uv run douyin-mcp --tool get_system_status --args '{}'
uv run douyin-mcp --tool configure_analysis_server --args '{"host": "192.168.1.50", "port": 8000}'
```
