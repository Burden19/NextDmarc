from collections import defaultdict

from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse

from app.core.dependencies import TenantContext, get_tenant_context
from app.repositories.record_repository import RecordRepository
from app.schemas.ioc import IocFeedResponse, IocItemResponse

router = APIRouter(prefix="/ioc", tags=["ioc"])
tenant_context_dep = Depends(get_tenant_context)


async def _build_ioc_items(*, tenant_id: str) -> list[IocItemResponse]:
    repository = RecordRepository()
    page = await repository.search(
        tenant_id=tenant_id,
        query="*",
        page=1,
        page_size=10_000,
    )

    grouped: dict[str, dict[str, object]] = defaultdict(dict)
    for item in page.items:
        record = item.get("record", {})
        if not isinstance(record, dict):
            continue

        source_ip = str(record.get("source_ip", "")).strip()
        if not source_ip:
            continue

        key = source_ip
        message_count = _as_int(record.get("count"), default=1)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = {
                "source_ip": source_ip,
                "provider": str(item.get("provider", "other")),
                "policy_domain": str(item.get("policy_domain", "")),
                "disposition": str(record.get("disposition", "")),
                "dkim": str(record.get("dkim", "")),
                "spf": str(record.get("spf", "")),
                "first_seen": str(item.get("date_range_begin", "")),
                "last_seen": str(item.get("date_range_end", "")),
                "message_count": message_count,
            }
            continue

        existing["message_count"] = (
            _as_int(existing.get("message_count"), default=0) + message_count
        )
        existing["last_seen"] = str(item.get("date_range_end", existing.get("last_seen", "")))

    return [IocItemResponse.model_validate(value) for value in grouped.values()]


@router.get("/json", response_model=IocFeedResponse)
async def ioc_feed_json(tenant: TenantContext = tenant_context_dep) -> IocFeedResponse:
    items = await _build_ioc_items(tenant_id=str(tenant.tenant_id))
    return IocFeedResponse(items=items, total=len(items))


@router.get("/csv", response_class=PlainTextResponse)
async def ioc_feed_csv(tenant: TenantContext = tenant_context_dep) -> str:
    items = await _build_ioc_items(tenant_id=str(tenant.tenant_id))

    rows = [
        "source_ip,provider,policy_domain,disposition,dkim,spf,first_seen,last_seen,message_count"
    ]
    for item in items:
        rows.append(
            ",".join(
                [
                    item.source_ip,
                    item.provider,
                    item.policy_domain,
                    item.disposition,
                    item.dkim,
                    item.spf,
                    item.first_seen,
                    item.last_seen,
                    str(item.message_count),
                ]
            )
        )
    return "\n".join(rows)


def _as_int(value: object, *, default: int) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return default
        try:
            return int(candidate)
        except ValueError:
            return default
    return default
