from uuid import UUID

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.dependencies import TenantContext, get_tenant_context
from app.core.exceptions import AppError
from app.repositories.alert_repository import (
    AlertAuditEntity,
    AlertEntity,
    AlertRepository,
    AlertTriageResult,
)
from app.schemas.alerts import (
    AlertAssignRequest,
    AlertAuditResponse,
    AlertCommentRequest,
    AlertEscalateRequest,
    AlertResponse,
    AlertSeverityValue,
    AlertStatusUpdateRequest,
    AlertTriageResponse,
    PaginatedAlertsResponse,
)
from app.services.alerting.realtime import (
    AlertRealtimePublisher,
    AlertRealtimeStream,
    build_alert_realtime_publisher,
    build_alert_realtime_stream,
)

router = APIRouter(prefix="/alerts", tags=["alerts"])
tenant_context_dep = Depends(get_tenant_context)


def _build_realtime_publisher() -> AlertRealtimePublisher:
    return build_alert_realtime_publisher()


def _build_realtime_stream() -> AlertRealtimeStream:
    return build_alert_realtime_stream()


async def _publish_realtime_event(
    *,
    tenant_id: str,
    event_type: str,
    alert_id: str,
    payload: dict[str, object],
) -> None:
    publisher = _build_realtime_publisher()
    try:
        await publisher.publish_event(
            tenant_id=tenant_id,
            event_type=event_type,
            alert_id=alert_id,
            payload=payload,
        )
    except Exception:
        return


def _to_alert_response(item: AlertEntity) -> AlertResponse:
    return AlertResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        domain_id=item.domain_id,
        severity=item.severity,
        status=item.status,
        message=item.message,
        assignee=item.assignee,
        escalation_level=item.escalation_level,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_audit_response(item: AlertAuditEntity) -> AlertAuditResponse:
    return AlertAuditResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        alert_id=item.alert_id,
        action=item.action,
        actor=item.actor,
        comment=item.comment,
        details=item.details,
        created_at=item.created_at,
    )


def _to_triage_response(item: AlertTriageResult) -> AlertTriageResponse:
    return AlertTriageResponse(
        alert=_to_alert_response(item.alert),
        audit=_to_audit_response(item.audit),
    )


def _resolve_websocket_tenant_id(websocket: WebSocket) -> str | None:
    candidate = websocket.headers.get("x-tenant-id", "").strip()
    if not candidate:
        candidate = websocket.query_params.get("tenant_id", "").strip()

    try:
        return str(UUID(candidate))
    except ValueError:
        return None


@router.get("", response_model=PaginatedAlertsResponse)
async def list_alerts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    status: str | None = Query(default=None, min_length=1, max_length=32),
    severity: AlertSeverityValue | None = None,
    tenant: TenantContext = tenant_context_dep,
) -> PaginatedAlertsResponse:
    repository = AlertRepository()
    result = await repository.list_paginated(
        tenant_id=str(tenant.tenant_id),
        page=page,
        page_size=page_size,
        status=status,
        severity=severity,
    )

    return PaginatedAlertsResponse(
        items=[_to_alert_response(item) for item in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=result.pages,
        has_next=result.has_next,
        has_previous=result.has_previous,
    )


@router.post("/{alert_id}/status", response_model=AlertTriageResponse)
async def update_alert_status(
    alert_id: str,
    payload: AlertStatusUpdateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> AlertTriageResponse:
    repository = AlertRepository()
    updated = await repository.update_status(
        tenant_id=str(tenant.tenant_id),
        alert_id=alert_id,
        status=payload.status,
        actor=payload.actor,
        comment=payload.comment,
    )
    if updated is None:
        raise AppError(message="Alert not found", status_code=404, code="alert_not_found")

    response = _to_triage_response(updated)
    await _publish_realtime_event(
        tenant_id=str(tenant.tenant_id),
        event_type="alert.status_updated",
        alert_id=response.alert.id,
        payload=response.model_dump(mode="json"),
    )
    return response


@router.post("/{alert_id}/assign", response_model=AlertTriageResponse)
async def assign_alert(
    alert_id: str,
    payload: AlertAssignRequest,
    tenant: TenantContext = tenant_context_dep,
) -> AlertTriageResponse:
    repository = AlertRepository()
    updated = await repository.assign(
        tenant_id=str(tenant.tenant_id),
        alert_id=alert_id,
        assignee=payload.assignee,
        actor=payload.actor,
        comment=payload.comment,
    )
    if updated is None:
        raise AppError(message="Alert not found", status_code=404, code="alert_not_found")

    response = _to_triage_response(updated)
    await _publish_realtime_event(
        tenant_id=str(tenant.tenant_id),
        event_type="alert.assigned",
        alert_id=response.alert.id,
        payload=response.model_dump(mode="json"),
    )
    return response


@router.post("/{alert_id}/comment", response_model=AlertTriageResponse)
async def comment_alert(
    alert_id: str,
    payload: AlertCommentRequest,
    tenant: TenantContext = tenant_context_dep,
) -> AlertTriageResponse:
    repository = AlertRepository()
    updated = await repository.add_comment(
        tenant_id=str(tenant.tenant_id),
        alert_id=alert_id,
        comment=payload.comment,
        actor=payload.actor,
    )
    if updated is None:
        raise AppError(message="Alert not found", status_code=404, code="alert_not_found")

    response = _to_triage_response(updated)
    await _publish_realtime_event(
        tenant_id=str(tenant.tenant_id),
        event_type="alert.commented",
        alert_id=response.alert.id,
        payload=response.model_dump(mode="json"),
    )
    return response


@router.post("/{alert_id}/escalate", response_model=AlertTriageResponse)
async def escalate_alert(
    alert_id: str,
    payload: AlertEscalateRequest,
    tenant: TenantContext = tenant_context_dep,
) -> AlertTriageResponse:
    repository = AlertRepository()
    updated = await repository.escalate(
        tenant_id=str(tenant.tenant_id),
        alert_id=alert_id,
        actor=payload.actor,
        comment=payload.comment,
        target_severity=payload.target_severity,
    )
    if updated is None:
        raise AppError(message="Alert not found", status_code=404, code="alert_not_found")

    response = _to_triage_response(updated)
    await _publish_realtime_event(
        tenant_id=str(tenant.tenant_id),
        event_type="alert.escalated",
        alert_id=response.alert.id,
        payload=response.model_dump(mode="json"),
    )
    return response


@router.websocket("/ws")
async def alerts_websocket(websocket: WebSocket) -> None:
    tenant_id = _resolve_websocket_tenant_id(websocket)
    if tenant_id is None:
        await websocket.close(code=1008, reason="Invalid X-Tenant-ID header")
        return

    await websocket.accept()

    settings = get_settings()
    stream = _build_realtime_stream()

    try:
        await stream.connect()
        await stream.subscribe(tenant_id=tenant_id)

        while True:
            event = await stream.next_event(
                timeout_seconds=settings.alert_realtime_heartbeat_seconds,
            )
            if event is None:
                await websocket.send_json(
                    {
                        "type": "alert.heartbeat",
                        "tenant_id": tenant_id,
                    }
                )
                continue
            await websocket.send_json(event)
    except WebSocketDisconnect:
        return
    finally:
        await stream.close()


@router.get("/{alert_id}/audit", response_model=list[AlertAuditResponse])
async def list_alert_audit(
    alert_id: str,
    tenant: TenantContext = tenant_context_dep,
) -> list[AlertAuditResponse]:
    repository = AlertRepository()
    found = await repository.get_by_id(tenant_id=str(tenant.tenant_id), alert_id=alert_id)
    if found is None:
        raise AppError(message="Alert not found", status_code=404, code="alert_not_found")

    return [
        _to_audit_response(item)
        for item in await repository.list_audit(
            tenant_id=str(tenant.tenant_id),
            alert_id=alert_id,
        )
    ]
