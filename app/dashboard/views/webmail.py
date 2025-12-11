# app/dashboard/views/webmail.py

import requests
from flask import redirect, current_app, abort
from flask_login import login_required, current_user

from app import config
from app.dashboard.base import dashboard_bp
from app.imap_utils import provision_imap_account_for_user
from app.log import LOG

from app.models import MailUser


@dashboard_bp.route("/webmail/sso-login")
@login_required
def webmail_sso_login():
    # 没开 IMAP 归档 / Webmail 就 404
    if not config.IMAP_ARCHIVE_ENABLED or not config.WEBMAIL_URL:
        abort(404)

    # 1) 确保当前用户有 IMAP 账号（没有就创建）
    try:
        mail_user = MailUser.get_by_user_id(current_user.id)
        if not mail_user or not mail_user.active:
            mail_user = provision_imap_account_for_user(current_user)
    except Exception:
        # 安全起见，这里不要暴露内部错误
        abort(500)

    if not mail_user or not mail_user.pass_plain:
        # 理论上不会到这里，如果你以后把 pass_plain 换成加密字段，记得在这里解密
        abort(500)

    imap_username = mail_user.username
    imap_password = mail_user.pass_plain  # TODO: 如果改成加密字段，这里解密

    # 2) 调 SnappyMail 的 external SSO 插件
    webmail_base = config.WEBMAIL_URL.rstrip("/")
    # 你前面用的是 /?/ExternalSso，就保持一致
    external_sso_url = f"{webmail_base}/?/ExternalSso"

    sso_key = config.WEBMAIL_SSO_SECRET
    if not sso_key:
        abort(500)

    try:
        resp = requests.post(
            external_sso_url,
            data={
                "Email": imap_username,
                "Password": imap_password,
                "SsoKey": sso_key,
            },
            timeout=5,
        )
    except requests.RequestException as e:
        LOG.e("SnappyMail ExternalSso 请求异常: %s", repr(e))
        abort(502)

    LOG.e(
        "SnappyMail ExternalSso 调用 URL: %s Email=%s Password=%s SsoKey=%s...",
        external_sso_url,
        imap_username,
        imap_password,
        sso_key[:12] + "..."
    )
    LOG.e("SnappyMail ExternalSso 调用 URL: %s", external_sso_url)
    LOG.e("SnappyMail ExternalSso 返回: status=%s, body=%r", resp.status_code, resp.text[:500],)

    if resp.status_code != 200:
        abort(502)

    sso_hash = resp.text.strip()
    if not sso_hash:
        abort(403)

    redirect_url = f"{webmail_base}/?Sso&hash={sso_hash}"
    return redirect(redirect_url)
