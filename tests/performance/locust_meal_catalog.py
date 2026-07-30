"""Authenticated load profile for Phase 0 meal catalog gates."""

from __future__ import annotations

import os
from uuid import uuid4

from locust import HttpUser, between, events, task

TOKEN_ENV = "MEALTRACK_LOAD_TEST_TOKEN"


@events.init.add_listener
def require_load_test_token(environment, **kwargs) -> None:
    if not os.getenv(TOKEN_ENV):
        raise RuntimeError(f"{TOKEN_ENV} is required for meal catalog load tests")


class MealCatalogUser(HttpUser):
    wait_time = between(0.2, 1.0)

    def on_start(self) -> None:
        self.plan_id: str | None = None
        self.slot_id: str | None = None
        self.selection_version = 1
        self.client.headers.update(
            {
                "Authorization": f"Bearer {os.environ[TOKEN_ENV]}",
                "Accept-Language": "en",
                "X-Timezone": "Asia/Ho_Chi_Minh",
            }
        )
        self._create_or_replay_plan()

    @task(8)
    def food_search(self) -> None:
        self.client.get(
            "/v1/foods/search",
            params={"query": "rice", "limit": 10, "language": "en"},
            name="/v1/foods/search",
        )

    @task(4)
    def recommendation_replay(self) -> None:
        self._create_or_replay_plan()

    @task(6)
    def slot_detail(self) -> None:
        if not self.plan_id or not self.slot_id:
            self._create_or_replay_plan()
            return
        self.client.get(
            f"/v1/meal-recommendations/{self.plan_id}/slots/{self.slot_id}",
            name="/v1/meal-recommendations/:plan_id/slots/:slot_id",
        )

    @task(2)
    def swap_slot(self) -> None:
        if not self.plan_id or not self.slot_id:
            self._create_or_replay_plan()
            return
        with self.client.post(
            f"/v1/meal-recommendations/{self.plan_id}/slots/{self.slot_id}/swap",
            json={
                "request_id": f"swap-{uuid4()}",
                "expected_selection_version": self.selection_version,
                "reason": "variety",
            },
            name="/v1/meal-recommendations/:plan_id/slots/:slot_id/swap",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                slot = response.json().get("slot") or {}
                self.selection_version = int(
                    slot.get("selection_version") or self.selection_version + 1
                )
            elif response.status_code in {404, 409, 422}:
                response.success()

    @task(1)
    def log_slot_once(self) -> None:
        if not self.plan_id or not self.slot_id:
            self._create_or_replay_plan()
            return
        with self.client.post(
            f"/v1/meal-recommendations/{self.plan_id}/slots/{self.slot_id}/log",
            json={"request_id": f"log-{uuid4()}"},
            name="/v1/meal-recommendations/:plan_id/slots/:slot_id/log",
            catch_response=True,
        ) as response:
            if response.status_code in {200, 404, 409, 422}:
                response.success()

    def _create_or_replay_plan(self) -> None:
        with self.client.post(
            "/v1/meal-recommendations/three-day",
            headers={"Idempotency-Key": f"load-{uuid4()}"},
            name="/v1/meal-recommendations/three-day",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                return
            body = response.json()
            self.plan_id = body.get("id")
            slots = body.get("slots") or []
            if not slots:
                return
            first_slot = slots[0]
            self.slot_id = first_slot.get("id")
            self.selection_version = int(first_slot.get("selection_version") or 1)
