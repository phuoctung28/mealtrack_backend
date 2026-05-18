"""
Unit tests for SubscriptionRepository.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from src.infra.database.models.subscription import Subscription
from src.infra.repositories.subscription_repository import SubscriptionRepository


class TestSubscriptionRepository:
    """Test SubscriptionRepository methods."""

    def setup_method(self):
        """Set up test repository."""
        self.mock_session = Mock()
        self.repository = SubscriptionRepository(self.mock_session)

    def test_find_all_by_user_id(self):
        """Test finding all subscriptions for a user."""
        user_id = "user-123"
        mock_subscriptions = [
            Mock(spec=Subscription, user_id=user_id, status="active"),
            Mock(spec=Subscription, user_id=user_id, status="expired"),
        ]

        self.mock_session.query.return_value.filter.return_value.all.return_value = (
            mock_subscriptions
        )

        result = self.repository.find_all_by_user_id(user_id)

        assert len(result) == 2
        self.mock_session.query.assert_called_once_with(Subscription)

    def test_get_by_user_id_deprecated(self):
        """Test deprecated get_by_user_id method."""
        user_id = "user-123"
        mock_subscriptions = [Mock(spec=Subscription)]

        self.mock_session.query.return_value.filter.return_value.all.return_value = (
            mock_subscriptions
        )

        result = self.repository.get_by_user_id(user_id)

        assert len(result) == 1

    def test_find_active_by_user_id(self):
        """Test finding active subscription for a user."""
        user_id = "user-123"
        mock_subscription = Mock(spec=Subscription, user_id=user_id, status="active")

        self.mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_subscription
        )

        result = self.repository.find_active_by_user_id(user_id)

        assert result == mock_subscription

    def test_find_active_by_user_id_not_found(self):
        """Test finding active subscription when none exists."""
        user_id = "user-123"

        self.mock_session.query.return_value.filter.return_value.first.return_value = (
            None
        )

        result = self.repository.find_active_by_user_id(user_id)

        assert result is None

    def test_get_active_by_user_id_deprecated(self):
        """Test deprecated get_active_by_user_id method."""
        user_id = "user-123"
        mock_subscription = Mock(spec=Subscription)

        self.mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_subscription
        )

        result = self.repository.get_active_by_user_id(user_id)

        assert result == mock_subscription

    def test_find_by_revenuecat_id(self):
        """Test finding subscription by RevenueCat ID."""
        revenuecat_id = "rc-subscriber-123"
        mock_subscription = Mock(
            spec=Subscription, revenuecat_subscriber_id=revenuecat_id
        )

        self.mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_subscription
        )

        result = self.repository.find_by_revenuecat_id(revenuecat_id)

        assert result == mock_subscription

    def test_get_by_revenuecat_id_deprecated(self):
        """Test deprecated get_by_revenuecat_id method."""
        revenuecat_id = "rc-subscriber-123"
        mock_subscription = Mock(spec=Subscription)

        self.mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_subscription
        )

        result = self.repository.get_by_revenuecat_id(revenuecat_id)

        assert result == mock_subscription

    def test_get_expired_subscriptions(self):
        """Test getting expired subscriptions."""
        expired_subscription = Mock(
            spec=Subscription,
            status="active",
            expires_at=datetime.now() - timedelta(days=1),
        )

        self.mock_session.query.return_value.filter.return_value.all.return_value = [
            expired_subscription
        ]

        result = self.repository.get_expired_subscriptions()

        assert len(result) == 1

    def test_find_expiring_in_window_queries_subscription(self):
        """Window query returns subscriptions filtered through SQLAlchemy."""
        sub = Mock(spec=Subscription, status="active")
        self.mock_session.query.return_value.filter.return_value.all.return_value = [
            sub
        ]

        result = self.repository.find_expiring_in_window(from_days=1, to_days=2)

        assert result == [sub]
        self.mock_session.query.assert_called_with(Subscription)

    def test_find_expiring_in_window_is_deterministic_with_now(self):
        """Passing `now` pins both bounds against the same reference moment."""
        self.mock_session.query.return_value.filter.return_value.all.return_value = []
        fixed = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Two consecutive calls with the same `now` must produce the same
        # bound literals. SQLAlchemy expressions don't support ==; compile
        # them and compare the rendered SQL + parameter values.
        from sqlalchemy.dialects import postgresql

        def _compiled(call):
            expr = call.args[0]
            return str(
                expr.compile(
                    dialect=postgresql.dialect(),
                    compile_kwargs={"literal_binds": True},
                )
            )

        self.repository.find_expiring_in_window(
            from_days=1, to_days=2, now=fixed
        )
        first = _compiled(
            self.mock_session.query.return_value.filter.call_args
        )

        self.repository.find_expiring_in_window(
            from_days=1, to_days=2, now=fixed
        )
        second = _compiled(
            self.mock_session.query.return_value.filter.call_args
        )

        assert first == second
        # Bound timestamps must appear in the compiled SQL (proves `now` was used).
        assert "2026-06-02" in first  # from_days=1
        assert "2026-06-03" in first  # to_days=2

    def test_update_subscription_status(self):
        """Test updating subscription status."""
        subscription_id = "sub-123"
        mock_subscription = Mock(
            spec=Subscription, id=subscription_id, status="active", expires_at=None
        )

        self.repository.get = Mock(return_value=mock_subscription)

        result = self.repository.update_subscription_status(
            subscription_id, "expired", datetime.now()
        )

        assert result == mock_subscription
        assert mock_subscription.status == "expired"
        self.mock_session.commit.assert_called_once()

    def test_update_subscription_status_not_found(self):
        """Test updating subscription status when subscription not found."""
        subscription_id = "sub-123"

        self.repository.get = Mock(return_value=None)

        result = self.repository.update_subscription_status(subscription_id, "expired")

        assert result is None

    def test_get_by_user_id_async(self):
        """Test async wrapper for get_by_user_id."""
        user_id = "user-123"
        mock_subscriptions = [Mock(spec=Subscription)]

        self.mock_session.query.return_value.filter.return_value.all.return_value = (
            mock_subscriptions
        )

        import asyncio

        result = asyncio.run(self.repository.get_by_user_id_async(user_id))

        assert len(result) == 1

    def test_get_by_revenuecat_id_async(self):
        """Test async wrapper for get_by_revenuecat_id."""
        revenuecat_id = "rc-subscriber-123"
        mock_subscription = Mock(spec=Subscription)

        self.mock_session.query.return_value.filter.return_value.first.return_value = (
            mock_subscription
        )

        import asyncio

        result = asyncio.run(self.repository.get_by_revenuecat_id_async(revenuecat_id))

        assert result == mock_subscription
