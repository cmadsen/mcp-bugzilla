import pytest
import pytest_asyncio
import respx
from httpx import Response
from mcp_bugzilla.mcp_utils import Bugzilla

MOCK_URL = "https://bugzilla.example.com"
MOCK_API_KEY = "secret_key"


@pytest_asyncio.fixture
async def bz_client():
    client = Bugzilla(MOCK_URL, MOCK_API_KEY)
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_bug_info(bz_client):
    async with respx.mock(base_url=MOCK_URL) as respx_mock:
        respx_mock.get("/rest.cgi/bug/123").mock(
            return_value=Response(
                200, json={"bugs": [{"id": 123, "summary": "Test Bug"}]}
            )
        )

        bug = await bz_client.bug_info(123)
        assert bug["id"] == 123
        assert bug["summary"] == "Test Bug"


@pytest.mark.asyncio
async def test_bug_comments(bz_client):
    async with respx.mock(base_url=MOCK_URL) as respx_mock:
        respx_mock.get("/rest.cgi/bug/123/comment").mock(
            return_value=Response(
                200,
                json={
                    "bugs": {
                        "123": {
                            "comments": [
                                {"id": 1, "text": "Comment 1"},
                                {"id": 2, "text": "Comment 2"},
                            ]
                        }
                    }
                },
            )
        )

        comments = await bz_client.bug_comments(123)
        assert len(comments) == 2
        assert comments[0]["text"] == "Comment 1"


@pytest.mark.asyncio
async def test_add_comment(bz_client):
    async with respx.mock(base_url=MOCK_URL) as respx_mock:
        fake_response = {"id": 101}
        route = respx_mock.post("/rest.cgi/bug/123/comment").mock(
            return_value=Response(201, json=fake_response)
        )

        resp = await bz_client.add_comment(123, "New comment", is_private=False)
        assert resp == fake_response

        # Verify call arguments
        assert route.called
        assert bz_client.api_key in str(route.calls.last.request.url)


@pytest.mark.asyncio
async def test_quicksearch(bz_client):
    async with respx.mock(base_url=MOCK_URL) as respx_mock:
        route = respx_mock.get("/rest.cgi/bug").mock(
            return_value=Response(200, json={"bugs": [{"id": 1}, {"id": 2}]})
        )

        # Test with explicit arguments (mandatory in mcp_utils)
        bugs = await bz_client.quicksearch(
            "product:Foo", status="ALL", include_fields="id,product", limit=50, offset=0
        )
        assert len(bugs) == 2

        # Verify call arguments
        assert route.called
        params = route.calls.last.request.url.params
        assert params["quicksearch"] == "ALL product:Foo"
        assert params["limit"] == "50"
        assert params["offset"] == "0"
        assert "include_fields" in params
        assert params["include_fields"] == "id,product"


@pytest.mark.asyncio
async def test_create_bug(bz_client):
    async with respx.mock(base_url=MOCK_URL) as respx_mock:
        route = respx_mock.post("/rest.cgi/bug").mock(
            return_value=Response(200, json={"id": 12345})
        )

        fields = {
            "product": "Foo",
            "component": "Bar",
            "summary": "It broke",
            "version": "1.0",
        }
        resp = await bz_client.create_bug(fields)
        assert resp == {"id": 12345}

        assert route.called
        assert route.calls.last.request.method == "POST"
        import json as _json

        assert _json.loads(route.calls.last.request.content) == fields


@pytest.mark.asyncio
async def test_update_bug(bz_client):
    async with respx.mock(base_url=MOCK_URL) as respx_mock:
        route = respx_mock.put("/rest.cgi/bug/123").mock(
            return_value=Response(200, json={"bugs": [{"id": 123, "changes": {}}]})
        )

        resp = await bz_client.update_bug(123, {"status": "RESOLVED", "resolution": "FIXED"})
        assert resp["bugs"][0]["id"] == 123

        assert route.called
        assert route.calls.last.request.method == "PUT"
        import json as _json

        body = _json.loads(route.calls.last.request.content)
        assert body["ids"] == [123]
        assert body["status"] == "RESOLVED"
        assert body["resolution"] == "FIXED"


@pytest.mark.asyncio
async def test_get_products(bz_client):
    async with respx.mock(base_url=MOCK_URL) as respx_mock:
        route = respx_mock.get("/rest.cgi/product").mock(
            return_value=Response(
                200, json={"products": [{"id": 1, "name": "Foo"}, {"id": 2, "name": "Bar"}]}
            )
        )

        products = await bz_client.get_products()
        assert len(products) == 2
        assert products[0]["name"] == "Foo"

        assert route.called
        assert route.calls.last.request.url.params["type"] == "accessible"


@pytest.mark.asyncio
async def test_get_field_values(bz_client):
    async with respx.mock(base_url=MOCK_URL) as respx_mock:
        respx_mock.get("/rest.cgi/field/bug/severity").mock(
            return_value=Response(
                200,
                json={
                    "fields": [
                        {"name": "severity", "values": [{"name": "low"}, {"name": "high"}]}
                    ]
                },
            )
        )

        values = await bz_client.get_field_values("severity")
        assert len(values) == 2
        assert values[1]["name"] == "high"


@pytest.mark.asyncio
async def test_find_users(bz_client):
    async with respx.mock(base_url=MOCK_URL) as respx_mock:
        route = respx_mock.get("/rest.cgi/user").mock(
            return_value=Response(
                200, json={"users": [{"id": 1, "email": "jane@example.com"}]}
            )
        )

        users = await bz_client.find_users("jane")
        assert len(users) == 1
        assert users[0]["email"] == "jane@example.com"

        assert route.called
        assert route.calls.last.request.url.params["match"] == "jane"
