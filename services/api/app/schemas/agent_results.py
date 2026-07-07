from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentRecommendation(BaseModel):
    model_config = ConfigDict(extra="allow")

    account_id: str
    accountId: str | None = None
    game_code: str | None = None
    server_code: str | None = None
    price: int = Field(default=0, ge=0)
    vip_level: int | None = None
    rank_name: str | None = None
    rank_stars: int | None = None
    anti_addiction: str | None = None
    secondary_real_name: str | None = None
    change_bind: str | None = None
    skin_count: int = Field(default=0, ge=0)
    hero_count: int = Field(default=0, ge=0)
    value_score: float = 0
    heroes: list[str] = Field(default_factory=list)
    skins: list[str] = Field(default_factory=list)


class AgentResultRenderRequest(BaseModel):
    session_id: str
    reply: str | None = None
    agent_message: str | None = None
    recommendations: list[AgentRecommendation] = Field(default_factory=list)
    history: list[dict[str, Any]] = Field(default_factory=list)
    intake: dict[str, Any] = Field(default_factory=dict)


class FrontendAccountCard(BaseModel):
    id: str
    title: str
    price: int
    match: int
    heroes: int
    skins: int
    rank: str
    vip: int | None
    region: str
    estValue: int
    estLabel: str
    risk: str
    riskItems: list[str]
    highlightSkins: list[str]
    detail_api: str


class AgentResultRenderResponse(BaseModel):
    session_id: str
    type: str
    message: str
    cards: list[FrontendAccountCard]
    history: list[dict[str, Any]] = Field(default_factory=list)
    intake: dict[str, Any] = Field(default_factory=dict)
