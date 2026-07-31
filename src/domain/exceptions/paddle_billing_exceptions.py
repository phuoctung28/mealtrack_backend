"""Errors raised at the Paddle billing domain boundary."""


class PaddleWebhookRetryError(Exception):
    """A verified event needs a prerequisite delivery to be retried."""


class PaddleCustomerNotFoundError(Exception):
    """The authenticated application user has no linked Paddle customer."""
