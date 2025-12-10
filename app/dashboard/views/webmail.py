# app/dashboard/views/webmail.py
import requests
from flask import redirect, current_app, abort
from flask_login import login_required, current_user
from app import config
from app.dashboard.base import dashboard_bp  # 使用已有 dashboard blueprint

@dashboard_bp.route("/webmail/sso-login")
@login_required
def webmail_sso_login():
    if not config.IMAP_ARCHIVE_ENABLED or not config.WEBMAIL_URL:
        abort(404)

    imap_domain = config.IMAP_ARCHIVE_DOMAIN
    if not imap_domain:
        abort(500)

    imap_username = f"user_{current_user.id}@{imap_domain}"

    imap_password = current_app.config.get("IMAP_MASTER_PASSWORD") or "CHANGE_ME_IMAP_PASSWORD"

    webmail_base = config.WEBMAIL_URL.rstrip("/")
    external_sso_url = f"{webmail_base}/?/ExternalSso"
    sso_key = config.WEBMAIL_SSO_SECRET
    if not sso_key:
        abort(500)

    try:
        resp = requests.post(
            external_sso_url,
            data={"Email": imap_username, "Password": imap_password, "SsoKey": sso_key},
            timeout=5,
        )
    except requests.RequestException:
        abort(502)

    if resp.status_code != 200:
        abort(502)

    sso_hash = resp.text.strip()
    if not sso_hash:
        abort(403)

    redirect_url = f"{webmail_base}/?Sso&hash={sso_hash}"
    return redirect(redirect_url)
