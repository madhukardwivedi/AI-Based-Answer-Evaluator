from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def decimal_to_json(value: Decimal) -> str:
    return format(value, "f")
