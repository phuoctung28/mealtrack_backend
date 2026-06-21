"""Request schemas for retention campaign endpoints."""

from typing import Literal

from pydantic import BaseModel


class MobilityIntentRequest(BaseModel):
    tomorrow_mobility_type: Literal["public_transit", "motorbike", "car_taxi"]
