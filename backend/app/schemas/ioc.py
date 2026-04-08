from pydantic import BaseModel


class IocItemResponse(BaseModel):
    source_ip: str
    provider: str
    policy_domain: str
    disposition: str
    dkim: str
    spf: str
    first_seen: str
    last_seen: str
    message_count: int


class IocFeedResponse(BaseModel):
    items: list[IocItemResponse]
    total: int
