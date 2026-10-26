from httpx import ASGITransport, AsyncClient

from douyin_crawler.main import create_app


async def test_operator_can_reach_api_and_dashboard() -> None:
    app = create_app(start_scheduler=False)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        dashboard_response = await client.get("/")

    assert dashboard_response.status_code == 200
    assert "Douyin Crawler" in dashboard_response.text
