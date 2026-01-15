from src.domain.ports.unit_of_work_port import UnitOfWorkPort
from tests.fixtures.fakes.fake_user_repository import FakeUserRepository
from tests.fixtures.fakes.fake_notification_repository import FakeNotificationRepository
from tests.fixtures.fakes.fake_subscription_repository import FakeSubscriptionRepository
from tests.fixtures.fakes.fake_meal_repository import FakeMealRepository
from tests.fixtures.fakes.fake_meal_suggestion_repository import FakeMealSuggestionRepository
from tests.fixtures.fakes.fake_meal_plan_repository import FakeMealPlanRepository
from tests.fixtures.fakes.fake_chat_repository import FakeChatRepository

class FakeUnitOfWork(UnitOfWorkPort):
    def __init__(self):
        self.users = FakeUserRepository()
        self.notifications = FakeNotificationRepository()
        self.subscriptions = FakeSubscriptionRepository()
        self.meals = FakeMealRepository()
        self.meal_suggestions = FakeMealSuggestionRepository()
        self.meal_plans = FakeMealPlanRepository()
        self.chats = FakeChatRepository()
        self.committed = False
        self.rolled_back = False

    def __enter__(self) -> 'FakeUnitOfWork':
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type:
            self.rollback()
        else:
            self.commit()

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True

    def refresh(self, obj) -> None:
        pass