from pydantic import BaseModel, Field


class AccountAssets(BaseModel):
    heroes: int = Field(..., ge=0)
    skins: int = Field(..., ge=0)
    rare_skins: list[str] = Field(default_factory=list)
    currencies: dict[str, int] = Field(default_factory=dict)


class AccountRisk(BaseModel):
    level: str
    notes: list[str] = Field(default_factory=list)


class AccountDetail(BaseModel):
    id: str
    account_id: str
    title: str
    price: int = Field(..., ge=0)
    platform: str
    server: str
    rank: str
    cover_image: str | None = None
    tags: list[str] = Field(default_factory=list)
    assets: AccountAssets
    risk: AccountRisk
    purchase_tips: list[str] = Field(default_factory=list)
