"""Paddle customer portal SDK boundary tests."""

import pytest

from src.api.routes.v1 import billing
from src.infra.services import paddle_billing_gateway


def test_customer_portal_session_uses_paddle_customer_and_subscription_ids(monkeypatch):
    received = {}

    class FakeClient:
        class customer_portal_sessions:
            @staticmethod
            def create(customer_id, operation):
                received["customer_id"] = customer_id
                received["subscription_ids"] = operation.subscription_ids
                return type(
                    "PortalSession",
                    (),
                    {
                        "urls": type(
                            "Urls",
                            (),
                            {
                                "general": type(
                                    "General",
                                    (),
                                    {"overview": "https://customer-portal.example"},
                                )()
                            },
                        )()
                    },
                )()

    monkeypatch.setattr(
        paddle_billing_gateway, "build_paddle_client", lambda: FakeClient()
    )

    url = paddle_billing_gateway._create_customer_portal_session("ctm_123", ["sub_123"])

    assert url == "https://customer-portal.example"
    assert received == {"customer_id": "ctm_123", "subscription_ids": ["sub_123"]}


@pytest.mark.asyncio
async def test_customer_portal_route_uses_the_authenticated_user(monkeypatch):
    received = {}

    class FakeBillingService:
        async def create_customer_portal_url(self, user_id):
            received["user_id"] = user_id
            return "https://customer-portal.example"

    monkeypatch.setattr(
        billing, "_get_paddle_billing_service", lambda: FakeBillingService()
    )

    response = await billing.redirect_to_paddle_customer_portal("user_123")

    assert response.status_code == 303
    assert response.headers["location"] == "https://customer-portal.example"
    assert received == {"user_id": "user_123"}
