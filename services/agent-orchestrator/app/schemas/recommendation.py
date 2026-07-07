"""
推荐结果的结构化输出定义。
"""
from pydantic import BaseModel


class RecommendResult(BaseModel):
    """Agent 输出的结构化推荐结果"""
    reply: str
    """给用户的自然语言回复"""
    recommended_ids: list[str]
    """推荐的账号 ID 列表，按推荐优先级排序，最多 10 个"""
