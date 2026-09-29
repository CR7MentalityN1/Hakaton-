from typing import Protocol
from urllib.parse import urlparse
import json
import httpx
from app.core.config import settings
from app.core.errors import fail


class LMSClient(Protocol):
    def fetch_records(self) -> list[dict]: ...


class WebsiteClient(Protocol):
    def fetch_records(self) -> list[dict]: ...


class MockLMSClient:
    def fetch_records(self):
        return [
            {
                "external_id": "lms-course-001",
                "university": "Университет ИТМО",
                "program": "Основы Python",
                "product": "РТК Облако",
                "vendor": "Ростелеком",
                "direction": "Разработка",
                "applications": 180,
                "students": 120,
                "streams": 4,
                "contract_number": "LMS-DEMO-01",
                "notes": "Детерминированные учебные данные LMS",
            }
        ]


class MockWebsiteClient:
    def fetch_records(self):
        return [
            {
                "external_id": "website-request-001",
                "university": "Университет ИТМО",
                "program": "Основы Python",
                "product": "РТК Облако",
                "vendor": "Ростелеком",
                "direction": "Разработка",
                "applications": 34,
                "students": 0,
                "streams": 1,
                "contract_number": "WEB-DEMO-01",
                "notes": "Демонстрационная заявка сайта Laravel",
            }
        ]


class HTTPJSONClient:
    def __init__(self, url, token):
        self.url = url
        self.token = token

    def fetch_records(self):
        p = urlparse(self.url)
        if (
            p.scheme != "https"
            or p.hostname not in settings.integration_allowed_hosts.split(",")
            or p.username
            or p.password
        ):
            fail(422, "SOURCE_URL_INVALID", "Настройте HTTPS URL и allowlist источника")
        try:
            with httpx.Client(
                timeout=15, follow_redirects=False, trust_env=False
            ) as client:
                with client.stream(
                    "GET",
                    self.url,
                    headers={
                        "Accept": "application/json",
                        **(
                            {"Authorization": "Bearer " + self.token}
                            if self.token
                            else {}
                        ),
                    },
                ) as response:
                    response.raise_for_status()
                    content = bytearray()
                    for chunk in response.iter_bytes():
                        content.extend(chunk)
                        if len(content) > 20 * 1024 * 1024:
                            fail(413, "SOURCE_TOO_LARGE", "Источник превысил 20 МБ")
            data = json.loads(content)
            if (
                not isinstance(data, list)
                or len(data) > 10000
                or any(not isinstance(r, dict) for r in data)
            ):
                fail(
                    422, "SOURCE_SCHEMA", "Ожидается массив объектов до 10 000 записей"
                )
            return data
        except (httpx.HTTPError, ValueError):
            fail(
                502,
                "SOURCE_UNAVAILABLE",
                "Источник недоступен или вернул некорректный JSON",
            )


def get_client(source):
    if source not in ("lms", "website"):
        fail(404, "SOURCE_UNKNOWN", "Источник не найден")
    if settings.integration_mode == "mock":
        return MockLMSClient() if source == "lms" else MockWebsiteClient()
    return (
        HTTPJSONClient(settings.lms_api_url, settings.lms_api_token)
        if source == "lms"
        else HTTPJSONClient(settings.website_api_url, settings.website_api_token)
    )
