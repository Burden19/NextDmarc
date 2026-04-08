from app.core.config import get_settings

from .models import AlertChannel, AlertSeverity

_DEFAULT_MAPPING: dict[AlertSeverity, tuple[AlertChannel, ...]] = {
    AlertSeverity.LOW: (AlertChannel.SIEM,),
    AlertSeverity.MEDIUM: (AlertChannel.EMAIL,),
    AlertSeverity.HIGH: (AlertChannel.EMAIL, AlertChannel.SLACK),
    AlertSeverity.CRITICAL: (AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.SIEM),
}


class AlertRouter:
    def __init__(
        self,
        mapping: dict[AlertSeverity, tuple[AlertChannel, ...]] | None = None,
    ) -> None:
        self._mapping = mapping or _DEFAULT_MAPPING

    def channels_for(self, *, severity: AlertSeverity) -> tuple[AlertChannel, ...]:
        return self._mapping.get(severity, ())


def build_router_from_settings() -> AlertRouter:
    settings = get_settings()
    mapping = {
        AlertSeverity.LOW: _parse_channels(
            settings.alert_route_low,
            fallback=_DEFAULT_MAPPING[AlertSeverity.LOW],
        ),
        AlertSeverity.MEDIUM: _parse_channels(
            settings.alert_route_medium,
            fallback=_DEFAULT_MAPPING[AlertSeverity.MEDIUM],
        ),
        AlertSeverity.HIGH: _parse_channels(
            settings.alert_route_high,
            fallback=_DEFAULT_MAPPING[AlertSeverity.HIGH],
        ),
        AlertSeverity.CRITICAL: _parse_channels(
            settings.alert_route_critical,
            fallback=_DEFAULT_MAPPING[AlertSeverity.CRITICAL],
        ),
    }
    return AlertRouter(mapping=mapping)


def _parse_channels(value: str, *, fallback: tuple[AlertChannel, ...]) -> tuple[AlertChannel, ...]:
    candidates = [item.strip().lower() for item in value.split(",") if item.strip()]
    parsed: list[AlertChannel] = []
    for candidate in candidates:
        try:
            channel = AlertChannel(candidate)
        except ValueError:
            continue
        if channel not in parsed:
            parsed.append(channel)

    return tuple(parsed) if parsed else fallback
