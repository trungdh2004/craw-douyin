import argparse
import asyncio
import json
import os
import sys
import time
from typing import Any

import httpx

from douyin_crawler.settings import get_settings

MCP_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "crawl_and_send_top_videos",
        "description": (
            "Quy trình tự động trọn gói: Cào dữ liệu từ Kênh (CHANNEL), Từ khóa (KEYWORD) "
            "hoặc Mục đã lưu (COLLECT) trên Douyin -> Đợi phiên cào hoàn tất -> Lọc ra Top N "
            "video nhiều tim nhất (digg_count cao nhất, mặc định bỏ qua các video đã từng gửi "
            "phân tích trước đó) -> Đẩy thẳng sang Server Phân tích (Edit Studio)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_type": {
                    "type": "string",
                    "enum": ["KEYWORD", "CHANNEL", "COLLECT"],
                    "default": "KEYWORD",
                    "description": "Loại nguồn cần quét: KEYWORD (từ khóa), CHANNEL (link kênh / sec_uid), hoặc COLLECT (mục đã lưu).",
                },
                "target_value": {
                    "type": "string",
                    "description": "Từ khóa tìm kiếm, link chia sẻ kênh Douyin, sec_uid, hoặc 'self' nếu target_type='COLLECT'.",
                },
                "target_name": {
                    "type": "string",
                    "description": "Tên hiển thị cho mục tiêu quét (tùy chọn).",
                },
                "max_crawl_items": {
                    "type": "integer",
                    "default": 30,
                    "description": "Số lượng bài đăng tối đa cần cào trong phiên này (1 - 500).",
                },
                "top_n": {
                    "type": "integer",
                    "default": 5,
                    "description": "Số lượng video có lượt thả tim (digg_count) cao nhất cần chọn để gửi sang Server Phân tích.",
                },
                "exclude_already_analyzed": {
                    "type": "boolean",
                    "default": True,
                    "description": "Nếu True (mặc định), tự động bỏ qua những video đã từng được đẩy sang Server Phân tích trước đó.",
                },
                "min_duration_sec": {
                    "type": "integer",
                    "description": "Lọc thời lượng video tối thiểu tính bằng giây (tùy chọn).",
                },
                "max_duration_sec": {
                    "type": "integer",
                    "description": "Lọc thời lượng video tối đa tính bằng giây (tùy chọn).",
                },
                "skip_crawl_if_existing": {
                    "type": "boolean",
                    "default": False,
                    "description": "Nếu True và mục tiêu đã tồn tại trong kho dữ liệu, bỏ qua bước cào mới và lọc ngay từ dữ liệu hiện có.",
                },
                "wait_timeout_sec": {
                    "type": "integer",
                    "default": 300,
                    "description": "Thời gian chờ tối đa (giây) cho phiên cào hoàn tất.",
                },
                "profile": {
                    "type": "string",
                    "default": "detailed",
                    "description": "Chế độ phân tích bên Edit Studio (mặc định: 'detailed').",
                },
            },
            "required": ["target_value"],
        },
    },
    {
        "name": "search_top_videos",
        "description": (
            "Tìm kiếm và lọc danh sách video đã có trong kho dữ liệu Douyin Crawler, "
            "hỗ trợ sắp xếp theo lượt tim cao nhất (digg_count), ngày đăng hoặc thời lượng."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Từ khóa tìm trong mô tả, tên kênh, hashtag hoặc mã aweme_id.",
                },
                "target_id": {
                    "type": "integer",
                    "description": "Lọc theo ID của mục tiêu quét (target_id).",
                },
                "top_n": {
                    "type": "integer",
                    "default": 10,
                    "description": "Số lượng video muốn lấy (mặc định 10, tối đa 100).",
                },
                "exclude_already_analyzed": {
                    "type": "boolean",
                    "default": False,
                    "description": "Nếu True, chỉ lấy những video CHƯA từng gửi sang Server Phân tích.",
                },
                "only_analyzed": {
                    "type": "boolean",
                    "default": False,
                    "description": "Nếu True, chỉ lấy những video ĐÃ gửi sang Server Phân tích.",
                },
                "only_bookmarked": {
                    "type": "boolean",
                    "default": False,
                    "description": "Nếu True, chỉ lấy những video đã đánh dấu Bookmark.",
                },
                "min_digg": {
                    "type": "integer",
                    "description": "Số lượt tim tối thiểu.",
                },
                "min_duration_sec": {
                    "type": "integer",
                    "description": "Thời lượng tối thiểu (giây).",
                },
                "max_duration_sec": {
                    "type": "integer",
                    "description": "Thời lượng tối đa (giây).",
                },
                "sort": {
                    "type": "string",
                    "enum": ["digg_count", "create_time", "crawled_at", "duration_ms"],
                    "default": "digg_count",
                    "description": "Tiêu chí sắp xếp (mặc định digg_count = nhiều tim nhất).",
                },
                "order": {
                    "type": "string",
                    "enum": ["desc", "asc"],
                    "default": "desc",
                },
            },
        },
    },
    {
        "name": "trigger_crawl",
        "description": (
            "Kích hoạt phiên cào dữ liệu Douyin theo Kênh/Từ khóa (mode='TARGET') "
            "hoặc danh sách link/ID video lẻ (mode='SINGLE_LINKS') và chờ hoàn tất."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["TARGET", "SINGLE_LINKS"],
                    "default": "TARGET",
                },
                "target_type": {
                    "type": "string",
                    "enum": ["KEYWORD", "CHANNEL", "COLLECT"],
                    "default": "KEYWORD",
                },
                "target_value": {
                    "type": "string",
                    "description": "Từ khóa hoặc link kênh cần cào (khi mode='TARGET').",
                },
                "inputs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách link chia sẻ hoặc aweme_id cần cào (khi mode='SINGLE_LINKS').",
                },
                "max_crawl_items": {
                    "type": "integer",
                    "default": 30,
                },
                "auto_download": {
                    "type": "boolean",
                    "default": False,
                },
                "wait_for_completion": {
                    "type": "boolean",
                    "default": True,
                },
                "wait_timeout_sec": {
                    "type": "integer",
                    "default": 300,
                },
            },
        },
    },
    {
        "name": "send_videos_to_analysis",
        "description": (
            "Đẩy danh sách video theo mã aweme_ids sang Server Phân tích (Edit Studio). "
            "Hệ thống sẽ tự động tải file MP4 không logo (nếu chưa tải) và đẩy sang Server Phân tích."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "aweme_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Danh sách mã aweme_id của các video cần đẩy sang phân tích.",
                },
                "profile": {
                    "type": "string",
                    "default": "detailed",
                },
                "auto_process": {
                    "type": "boolean",
                    "default": True,
                },
            },
            "required": ["aweme_ids"],
        },
    },
    {
        "name": "get_system_status",
        "description": (
            "Kiểm tra trạng thái tổng quan của hệ thống Douyin Crawler: trạng thái đăng nhập "
            "trình duyệt Douyin (AUTHENTICATED / CAPTCHA_REQUIRED / LOGIN_REQUIRED), thống kê kho video, "
            "chế độ chạy ẩn (headless_mode) và địa chỉ IP:Port của Server Phân tích."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "configure_analysis_server",
        "description": (
            "Cập nhật địa chỉ IP/Hostname và cổng (Port) của Server Phân tích (Edit Studio) "
            "mà Douyin Crawler sẽ đẩy video tới."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "host": {
                    "type": "string",
                    "description": "Địa chỉ IP hoặc tên miền của Server Phân tích (ví dụ '127.0.0.1' hoặc '192.168.1.50').",
                },
                "port": {
                    "type": "integer",
                    "description": "Cổng (Port) của Server Phân tích (ví dụ 8000).",
                },
            },
            "required": ["host", "port"],
        },
    },
]


def _summarize_video(item: dict[str, Any]) -> dict[str, Any]:
    duration_ms = int(item.get("duration_ms") or 0)
    return {
        "aweme_id": item.get("aweme_id"),
        "author_nickname": item.get("author_nickname"),
        "description": item.get("description"),
        "digg_count": item.get("digg_count", 0),
        "comment_count": item.get("comment_count", 0),
        "share_count": item.get("share_count", 0),
        "collect_count": item.get("collect_count", 0),
        "duration_sec": round(duration_ms / 1000, 1),
        "create_time": item.get("create_time"),
        "original_url": item.get("original_url"),
        "download_status": item.get("download_status"),
        "edit_status": item.get("edit_status"),
        "edit_studio_url": item.get("edit_studio_url"),
    }


class DouyinMcpServer:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (
            base_url
            or os.environ.get("DOUYIN_CRAWLER_URL")
            or "http://127.0.0.1:8080"
        ).rstrip("/")
        self.username = (
            username
            or os.environ.get("DOUYIN_ADMIN_USERNAME")
            or settings.admin_username
            or "admin"
        )
        self.password = (
            password
            or os.environ.get("DOUYIN_ADMIN_PASSWORD")
            or settings.admin_password
            or "admin123"
        )
        self._external_client = http_client
        self._token: str | None = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        if self._external_client is not None:
            return await self._request_with_client(
                self._external_client,
                method,
                path,
                params=params,
                json_body=json_body,
            )
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=120.0,
        ) as client:
            return await self._request_with_client(
                client,
                method,
                path,
                params=params,
                json_body=json_body,
            )

    async def _request_with_client(
        self,
        client: httpx.AsyncClient,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        if not self._token:
            await self._login(client)
        headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
        res = await client.request(
            method,
            path,
            params=params,
            json=json_body,
            headers=headers,
        )
        if res.status_code == 401:
            await self._login(client)
            headers = {"Authorization": f"Bearer {self._token}"} if self._token else {}
            res = await client.request(
                method,
                path,
                params=params,
                json=json_body,
                headers=headers,
            )
        res.raise_for_status()
        if res.status_code == 204:
            return None
        return res.json()

    async def _login(self, client: httpx.AsyncClient) -> None:
        res = await client.post(
            "/api/auth/login",
            json={"username": self.username, "password": self.password},
        )
        if res.status_code == 200:
            data = res.json()
            self._token = data.get("token")

    async def _ensure_target(
        self,
        *,
        target_type: str,
        target_value: str,
        target_name: str | None,
        max_items_per_run: int,
        auto_download: bool = False,
    ) -> dict[str, Any]:
        targets: list[dict[str, Any]] = await self._request("GET", "/api/targets")
        clean_type = target_type.upper()
        clean_val = target_value.strip() or ("self" if clean_type == "COLLECT" else "")
        for existing in targets:
            if (
                existing.get("target_type") == clean_type
                and existing.get("target_value") == clean_val
            ):
                if int(existing.get("max_items_per_run") or 0) != max_items_per_run:
                    updated: dict[str, Any] = await self._request(
                        "PUT",
                        f"/api/targets/{existing['id']}",
                        json_body={"max_items_per_run": max_items_per_run},
                    )
                    return updated
                return existing

        name = target_name or f"{clean_type}: {clean_val[:40]}"
        created: dict[str, Any] = await self._request(
            "POST",
            "/api/targets",
            json_body={
                "name": name,
                "target_type": clean_type,
                "target_value": clean_val,
                "cron_expr": "0 */6 * * *",
                "schedule_type": "MANUAL",
                "schedule_config": {},
                "run_at": None,
                "auto_download": auto_download,
                "max_items_per_run": max_items_per_run,
                "is_active": False,
            },
        )
        return created

    async def _wait_for_target_crawl(
        self,
        target_id: int,
        timeout_sec: int = 300,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + max(timeout_sec, 5)
        while time.monotonic() < deadline:
            logs_page: dict[str, Any] = await self._request(
                "GET",
                "/api/logs",
                params={"target_id": target_id, "page_size": 5},
            )
            items = logs_page.get("items") or []
            if items:
                latest = items[0]
                status = latest.get("status")
                if status in ("SUCCESS", "FAILED", "CAPTCHA_BLOCKED"):
                    return {
                        "log_id": latest.get("id"),
                        "status": status,
                        "new_videos_count": latest.get("new_videos_count", 0),
                        "updated_videos_count": latest.get("updated_videos_count", 0),
                        "error_message": latest.get("error_message"),
                    }
            await asyncio.sleep(0.25)
        return {
            "status": "TIMEOUT",
            "new_videos_count": 0,
            "updated_videos_count": 0,
            "error_message": f"Quá thời gian chờ {timeout_sec}s",
        }

    async def _wait_for_log_id(
        self,
        log_id: int,
        timeout_sec: int = 300,
    ) -> dict[str, Any]:
        deadline = time.monotonic() + max(timeout_sec, 5)
        while time.monotonic() < deadline:
            logs_page: dict[str, Any] = await self._request(
                "GET",
                "/api/logs",
                params={"page_size": 25},
            )
            for item in logs_page.get("items") or []:
                if int(item.get("id") or 0) == log_id:
                    status = item.get("status")
                    if status in ("SUCCESS", "FAILED", "CAPTCHA_BLOCKED"):
                        return {
                            "log_id": log_id,
                            "status": status,
                            "new_videos_count": item.get("new_videos_count", 0),
                            "updated_videos_count": item.get("updated_videos_count", 0),
                            "error_message": item.get("error_message"),
                        }
            await asyncio.sleep(0.25)
        return {
            "log_id": log_id,
            "status": "TIMEOUT",
            "new_videos_count": 0,
            "updated_videos_count": 0,
            "error_message": f"Quá thời gian chờ {timeout_sec}s",
        }

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "get_system_status":
            browser = await self._request("GET", "/api/browser/status")
            stats = await self._request("GET", "/api/stats")
            studio = await self._request("GET", "/api/settings/edit-studio")
            anti_bot = await self._request("GET", "/api/settings/anti-bot")
            return {
                "browser_status": browser.get("status"),
                "headless_mode": bool(anti_bot.get("headless_mode")),
                "analysis_server": studio,
                "stats": stats,
            }

        if name == "configure_analysis_server":
            host = str(arguments["host"]).strip()
            port = int(arguments["port"])
            return await self._request(
                "PUT",
                "/api/settings/edit-studio",
                json_body={"host": host, "port": port},
            )

        if name == "search_top_videos":
            top_n = max(1, min(int(arguments.get("top_n", 10)), 100))
            params: dict[str, Any] = {
                "sort": arguments.get("sort", "digg_count"),
                "order": arguments.get("order", "desc"),
                "page": 1,
                "page_size": top_n,
            }
            if arguments.get("search"):
                params["search"] = str(arguments["search"])
            if arguments.get("target_id") is not None:
                params["target_id"] = int(arguments["target_id"])
            if arguments.get("exclude_already_analyzed"):
                params["is_analyzed"] = "false"
            elif arguments.get("only_analyzed"):
                params["is_analyzed"] = "true"
            if arguments.get("only_bookmarked"):
                params["is_bookmarked"] = "true"
            if arguments.get("min_digg") is not None:
                params["min_digg"] = int(arguments["min_digg"])
            if arguments.get("min_duration_sec") is not None:
                params["min_duration_ms"] = int(arguments["min_duration_sec"]) * 1000
            if arguments.get("max_duration_sec") is not None:
                params["max_duration_ms"] = int(arguments["max_duration_sec"]) * 1000

            page_data: dict[str, Any] = await self._request(
                "GET",
                "/api/videos",
                params=params,
            )
            videos = [_summarize_video(v) for v in (page_data.get("items") or [])[:top_n]]
            return {
                "total_matching": page_data.get("total", len(videos)),
                "returned_count": len(videos),
                "videos": videos,
            }

        if name == "trigger_crawl":
            mode = str(arguments.get("mode", "TARGET")).upper()
            wait_for_completion = bool(arguments.get("wait_for_completion", True))
            wait_timeout_sec = int(arguments.get("wait_timeout_sec", 300))
            auto_download = bool(arguments.get("auto_download", False))

            if mode == "SINGLE_LINKS":
                inputs = [str(x).strip() for x in (arguments.get("inputs") or []) if str(x).strip()]
                res = await self._request(
                    "POST",
                    "/api/crawl/items",
                    json_body={
                        "inputs": inputs,
                        "auto_download": auto_download,
                        "is_bookmarked": False,
                    },
                )
                log_id = int(res["log_id"])
                if wait_for_completion:
                    return await self._wait_for_log_id(log_id, wait_timeout_sec)
                return {"status": "STARTED", "log_id": log_id}

            target_type = str(arguments.get("target_type", "KEYWORD")).upper()
            target_value = str(arguments.get("target_value") or "").strip()
            max_crawl_items = max(1, min(int(arguments.get("max_crawl_items", 30)), 500))
            target = await self._ensure_target(
                target_type=target_type,
                target_value=target_value,
                target_name=arguments.get("target_name"),
                max_items_per_run=max_crawl_items,
                auto_download=auto_download,
            )
            target_id = int(target["id"])
            await self._request("POST", f"/api/targets/{target_id}/run")
            if wait_for_completion:
                crawl_res = await self._wait_for_target_crawl(target_id, wait_timeout_sec)
                return {"target_id": target_id, **crawl_res}
            return {"target_id": target_id, "status": "STARTED"}

        if name == "send_videos_to_analysis":
            aweme_ids = [str(x).strip() for x in (arguments.get("aweme_ids") or []) if str(x).strip()]
            if not aweme_ids:
                return {
                    "sent_count": 0,
                    "list_id": None,
                    "item_ids": [],
                    "studio_url": None,
                }
            send_res: dict[str, Any] = await self._request(
                "POST",
                "/api/videos/send-to-edit",
                json_body={
                    "aweme_ids": aweme_ids,
                    "auto_process": bool(arguments.get("auto_process", True)),
                    "profile": str(arguments.get("profile", "detailed")),
                },
            )
            return {
                "sent_count": len(send_res.get("item_ids") or []),
                "list_id": send_res.get("list_id"),
                "item_ids": send_res.get("item_ids") or [],
                "studio_url": send_res.get("studio_url"),
                "edit_base_url": send_res.get("edit_base_url"),
            }

        if name == "crawl_and_send_top_videos":
            target_type = str(arguments.get("target_type", "KEYWORD")).upper()
            target_value = str(arguments["target_value"]).strip()
            max_crawl_items = max(1, min(int(arguments.get("max_crawl_items", 30)), 500))
            top_n = max(1, min(int(arguments.get("top_n", 5)), 50))
            exclude_already_analyzed = bool(arguments.get("exclude_already_analyzed", True))
            skip_crawl_if_existing = bool(arguments.get("skip_crawl_if_existing", False))
            wait_timeout_sec = int(arguments.get("wait_timeout_sec", 300))
            profile = str(arguments.get("profile", "detailed"))

            target = await self._ensure_target(
                target_type=target_type,
                target_value=target_value,
                target_name=arguments.get("target_name"),
                max_items_per_run=max_crawl_items,
            )
            target_id = int(target["id"])

            crawl_result: dict[str, Any] = {
                "status": "SKIPPED_EXISTING",
                "new_videos_count": 0,
                "updated_videos_count": 0,
            }
            if not skip_crawl_if_existing:
                await self._request("POST", f"/api/targets/{target_id}/run")
                crawl_result = await self._wait_for_target_crawl(target_id, wait_timeout_sec)

            query_params: dict[str, Any] = {
                "target_id": target_id,
                "sort": "digg_count",
                "order": "desc",
                "page": 1,
                "page_size": top_n,
            }
            if exclude_already_analyzed:
                query_params["is_analyzed"] = "false"
            if arguments.get("min_duration_sec") is not None:
                query_params["min_duration_ms"] = int(arguments["min_duration_sec"]) * 1000
            if arguments.get("max_duration_sec") is not None:
                query_params["max_duration_ms"] = int(arguments["max_duration_sec"]) * 1000

            videos_page: dict[str, Any] = await self._request(
                "GET",
                "/api/videos",
                params=query_params,
            )
            selected_raw = (videos_page.get("items") or [])[:top_n]
            selected_videos = [_summarize_video(v) for v in selected_raw]
            chosen_ids = [str(v["aweme_id"]) for v in selected_videos if v.get("aweme_id")]

            if not chosen_ids:
                return {
                    "target_id": target_id,
                    "target_type": target_type,
                    "target_value": target_value,
                    "crawl_result": crawl_result,
                    "selected_videos": [],
                    "analysis_submission": {
                        "sent_count": 0,
                        "list_id": None,
                        "item_ids": [],
                        "studio_url": None,
                        "message": "Không tìm thấy video phù hợp chưa gửi phân tích.",
                    },
                }

            analysis_res = await self.call_tool(
                "send_videos_to_analysis",
                {
                    "aweme_ids": chosen_ids,
                    "profile": profile,
                    "auto_process": True,
                },
            )
            return {
                "target_id": target_id,
                "target_type": target_type,
                "target_value": target_value,
                "crawl_result": crawl_result,
                "selected_videos": selected_videos,
                "analysis_submission": analysis_res,
            }

        raise ValueError(f"Unknown MCP tool: {name}")

    async def handle_rpc(self, request: dict[str, Any]) -> dict[str, Any] | None:
        method = request.get("method")
        req_id = request.get("id")
        params = request.get("params") or {}

        if method == "notifications/initialized":
            return None

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": "douyin-crawler-mcp",
                        "version": "1.0.0",
                    },
                },
            }

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": MCP_TOOLS_SCHEMA},
            }

        if method == "tools/call":
            tool_name = str(params.get("name") or "")
            tool_args = dict(params.get("arguments") or {})
            try:
                output = await self.call_tool(tool_name, tool_args)
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(output, ensure_ascii=False, indent=2),
                            }
                        ],
                        "isError": False,
                    },
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Lỗi khi chạy tool {tool_name}: {exc}",
                            }
                        ],
                        "isError": True,
                    },
                }

        if req_id is not None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}",
                },
            }
        return None


async def run_stdio_server(server: DouyinMcpServer) -> None:
    loop = asyncio.get_running_loop()
    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)

    while True:
        line = await reader.readline()
        if not line:
            break
        decoded = line.decode("utf-8", errors="replace").strip()
        if not decoded:
            continue

        use_content_length = False
        if decoded.lower().startswith("content-length:"):
            use_content_length = True
            length = int(decoded.split(":", 1)[1].strip())
            while True:
                header_line = await reader.readline()
                if not header_line or header_line.strip() == b"":
                    break
            body_bytes = await reader.readexactly(length)
            raw_json = body_bytes.decode("utf-8", errors="replace")
        else:
            raw_json = decoded

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue

        response = await server.handle_rpc(payload)
        if response is not None:
            out_str = json.dumps(response, ensure_ascii=False)
            if use_content_length:
                out_bytes = out_str.encode("utf-8")
                sys.stdout.write(f"Content-Length: {len(out_bytes)}\r\n\r\n{out_str}")
            else:
                sys.stdout.write(out_str + "\n")
            sys.stdout.flush()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Douyin Crawler MCP Server & Agent Tool CLI"
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="In danh sách các MCP tools dưới dạng JSON rồi thoát",
    )
    parser.add_argument(
        "--tool",
        type=str,
        default=None,
        help="Gọi trực tiếp 1 MCP tool từ dòng lệnh (ví dụ: crawl_and_send_top_videos)",
    )
    parser.add_argument(
        "--args",
        type=str,
        default="{}",
        help="Chuỗi JSON chứa tham số truyền cho --tool",
    )
    args = parser.parse_args()

    if args.list_tools:
        print(json.dumps(MCP_TOOLS_SCHEMA, ensure_ascii=False, indent=2))
        return

    server = DouyinMcpServer()
    if args.tool:
        parsed_args = json.loads(args.args)
        result = asyncio.run(server.call_tool(args.tool, parsed_args))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    asyncio.run(run_stdio_server(server))


if __name__ == "__main__":
    main()
