from locust import HttpUser, task, between


class MealtrackUser(HttpUser):
    """
    Task 13 load test locustfile (plan: hit hot DB endpoints).

    Run example:
      locust --headless -u 50 -r 5 --run-time 60s --host https://<host>
    """

    wait_time = between(0.1, 0.5)

    def on_start(self):
        # Helps the dev auth bypass path that reads request headers/middleware state.
        self.client.headers.update(
            {
                "Accept-Language": "en",
            }
        )

    @task(2)
    def health(self):
        self.client.get("/health")

    # Plan success-criteria endpoints (router prefix is /v1/meals)
    # NOTE: `/v1/meals/daily/macros` depends on complete onboarding/TDEE data.
    # In local dev, this may 404 if the dev profile isn't fully populated.
    # Keep it low-weight so it doesn't dominate failure rate during profiling.
    @task(1)
    def meals_daily_macros(self):
        self.client.get("/v1/meals/daily/macros")

    @task(4)
    def meals_weekly_budget(self):
        self.client.get("/v1/meals/weekly/budget")

    @task(3)
    def meals_weekly_daily_breakdown(self):
        self.client.get("/v1/meals/weekly/daily-breakdown")

    @task(3)
    def meals_streak(self):
        self.client.get("/v1/meals/streak")

