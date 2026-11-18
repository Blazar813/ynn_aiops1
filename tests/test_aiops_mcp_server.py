import os

from src.aiops_mcp_server import execute_remediation, get_service_health, search_logs


def test_search_logs_returns_payment_errors():
    result = search_logs("payment-service", "ERROR", 10)
    assert result["status"] == "success"
    assert result["logs"][0]["level"] == "ERROR"


def test_mutation_fails_closed(monkeypatch):
    monkeypatch.delenv("AIOPS_ALLOW_MUTATIONS", raising=False)
    result = execute_remediation("payment-service", "restart_service", "secret")
    assert result["status"] == "dry-run"


def test_health_reflects_demo_incident():
    assert get_service_health("payment-service")["status"] == "degraded"
