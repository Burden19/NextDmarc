from app.services.alerting.models import AlertChannel, AlertSeverity
from app.services.alerting.router import AlertRouter


def test_alert_router_default_mapping_covers_all_severities() -> None:
    router = AlertRouter()

    assert router.channels_for(severity=AlertSeverity.LOW) == (AlertChannel.SIEM,)
    assert router.channels_for(severity=AlertSeverity.MEDIUM) == (AlertChannel.EMAIL,)
    assert router.channels_for(severity=AlertSeverity.HIGH) == (
        AlertChannel.EMAIL,
        AlertChannel.SLACK,
    )
    assert router.channels_for(severity=AlertSeverity.CRITICAL) == (
        AlertChannel.EMAIL,
        AlertChannel.SLACK,
        AlertChannel.SIEM,
    )


def test_alert_router_uses_custom_mapping_when_provided() -> None:
    custom = {
        AlertSeverity.LOW: (AlertChannel.EMAIL,),
        AlertSeverity.MEDIUM: (AlertChannel.SIEM,),
        AlertSeverity.HIGH: (AlertChannel.SLACK,),
        AlertSeverity.CRITICAL: (AlertChannel.SLACK, AlertChannel.SIEM),
    }

    router = AlertRouter(mapping=custom)

    assert router.channels_for(severity=AlertSeverity.LOW) == (AlertChannel.EMAIL,)
    assert router.channels_for(severity=AlertSeverity.MEDIUM) == (AlertChannel.SIEM,)
    assert router.channels_for(severity=AlertSeverity.HIGH) == (AlertChannel.SLACK,)
    assert router.channels_for(severity=AlertSeverity.CRITICAL) == (
        AlertChannel.SLACK,
        AlertChannel.SIEM,
    )
