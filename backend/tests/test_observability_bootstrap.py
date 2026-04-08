from app.main import create_app


def test_app_bootstraps_with_observability_enabled() -> None:
    app = create_app()

    assert app is not None
    # Prometheus endpoint is exposed by instrumentation.
    routes = {route.path for route in app.routes}
    assert "/metrics" in routes
