from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.db import SubscriptionStateRecord, session_scope


class SubscriptionsRepo:
    def __init__(self, session_factory) -> None:
        self.session_factory = session_factory

    def get_by_user_id(self, user_id: str) -> SubscriptionStateRecord | None:
        with session_scope(self.session_factory) as session:
            stmt = (
                select(SubscriptionStateRecord)
                .where(SubscriptionStateRecord.user_id == user_id)
                .order_by(SubscriptionStateRecord.updated_at.desc())
            )
            return session.execute(stmt).scalars().first()

    def upsert_state(
        self,
        *,
        user_id: str | None,
        stripe_customer_id: str | None,
        stripe_subscription_id: str | None,
        plan_key: str,
        billing_interval: str | None,
        status: str,
        current_period_end: datetime | None,
        last_event_id: str,
        raw_event: dict,
    ) -> SubscriptionStateRecord:
        now = datetime.now(timezone.utc)
        with session_scope(self.session_factory) as session:
            record = self._find_existing(
                session,
                user_id=user_id,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
            )
            if record is None:
                state_id = stripe_subscription_id or stripe_customer_id or user_id or last_event_id
                record = SubscriptionStateRecord(state_id=f"substate_{state_id}")

            record.user_id = user_id or record.user_id
            record.stripe_customer_id = stripe_customer_id or record.stripe_customer_id
            record.stripe_subscription_id = stripe_subscription_id or record.stripe_subscription_id
            record.plan_key = plan_key
            record.billing_interval = billing_interval
            record.status = status
            record.current_period_end = current_period_end
            record.last_event_id = last_event_id
            record.raw_event = raw_event
            record.updated_at = now
            session.add(record)
            session.flush()
            return record

    def _find_existing(
        self,
        session,
        *,
        user_id: str | None,
        stripe_customer_id: str | None,
        stripe_subscription_id: str | None,
    ) -> SubscriptionStateRecord | None:
        if stripe_subscription_id:
            record = session.execute(
                select(SubscriptionStateRecord).where(
                    SubscriptionStateRecord.stripe_subscription_id == stripe_subscription_id
                )
            ).scalar_one_or_none()
            if record is not None:
                return record
        if user_id:
            record = session.execute(
                select(SubscriptionStateRecord).where(SubscriptionStateRecord.user_id == user_id)
            ).scalar_one_or_none()
            if record is not None:
                return record
        if stripe_customer_id:
            return session.execute(
                select(SubscriptionStateRecord).where(
                    SubscriptionStateRecord.stripe_customer_id == stripe_customer_id
                )
            ).scalar_one_or_none()
        return None
