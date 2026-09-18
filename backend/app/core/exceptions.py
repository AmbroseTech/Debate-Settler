"""Application exceptions and friendly error handling.

Users never see raw stack traces or technical jargon. Each domain error maps to
a clear, plain-English message (see master build prompt §57 and §73).
"""
from __future__ import annotations

from typing import Any, Optional


class AppError(Exception):
    """Base class for handled application errors."""

    status_code: int = 400
    code: str = "app_error"
    user_message: str = "Something went wrong. Please try again."

    def __init__(self, user_message: Optional[str] = None, **context: Any) -> None:
        self.user_message = user_message or self.user_message
        self.context = context
        super().__init__(self.user_message)


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_error"
    user_message = "Please sign in to continue."


class AuthorizationError(AppError):
    status_code = 403
    code = "authorization_error"
    user_message = "You don't have permission to do that."


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    user_message = "We couldn't find what you were looking for."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    user_message = "That action isn't allowed right now."


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
    user_message = "Please check the details you entered."


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    user_message = "You're doing that a bit too quickly. Please wait a moment."


class AccountLockedError(AppError):
    status_code = 423
    code = "account_locked"
    user_message = "Your account is temporarily locked for security. Please try again later."


class InsufficientFundsError(AppError):
    status_code = 400
    code = "insufficient_funds"
    user_message = "This amount is not currently available. Please check your balance."


class PaymentError(AppError):
    status_code = 402
    code = "payment_error"
    user_message = (
        "We couldn't confirm your payment yet. Please don't submit the payment "
        "again until we check its status."
    )


class FeatureDisabledError(AppError):
    status_code = 403
    code = "feature_disabled"
    user_message = "This feature isn't available in your region or configuration."


class DebateLockedError(AppError):
    status_code = 409
    code = "debate_locked"
    user_message = "This debate is locked and its rules can no longer be changed."
