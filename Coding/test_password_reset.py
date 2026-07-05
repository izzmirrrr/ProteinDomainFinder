import asyncio
import importlib


def test_password_reset_falls_back_to_code_when_smtp_is_unavailable(monkeypatch):
    app = importlib.import_module("app")

    monkeypatch.setattr(app.settings, "SMTP_HOST", "")
    monkeypatch.setattr(app.settings, "SMTP_USERNAME", "")
    monkeypatch.setattr(app.settings, "SMTP_PASSWORD", "")
    monkeypatch.setattr(app.settings, "SMTP_FROM_EMAIL", "")

    monkeypatch.setattr(app, "find_user_by_email", lambda email: {"user_id": "user-1", "email": email})
    monkeypatch.setattr(app, "create_password_reset_code", lambda user: ("123456", None))
    monkeypatch.setattr(app, "send_password_reset_email", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("smtp down")))

    result = asyncio.run(app.forgot_password(app.PasswordResetRequest(email="user@example.com")))

    assert result["delivery"] == "code"
    assert result["code"] == "123456"


def test_password_reset_uses_email_delivery_when_configured(monkeypatch):
    app = importlib.import_module("app")

    monkeypatch.setattr(app.settings, "SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setattr(app.settings, "SMTP_USERNAME", "user@gmail.com")
    monkeypatch.setattr(app.settings, "SMTP_PASSWORD", "app-password")
    monkeypatch.setattr(app.settings, "SMTP_FROM_EMAIL", "user@gmail.com")

    monkeypatch.setattr(app, "find_user_by_email", lambda email: {"user_id": "user-1", "email": email})
    monkeypatch.setattr(app, "create_password_reset_code", lambda user: ("123456", None))
    monkeypatch.setattr(app, "send_password_reset_email", lambda *args, **kwargs: None)

    result = asyncio.run(app.forgot_password(app.PasswordResetRequest(email="user@example.com")))

    assert result["delivery"] == "email"
    assert "code" not in result
