# app/dashboard/views/webmail.py

from flask import Blueprint, render_template, current_app, abort
from flask_login import login_required, current_user

from app import config

dashboard_webmail_bp = Blueprint("dashboard_webmail", __name__)

@dashboard_webmail_bp.route("/webmail/sso-login")
@login_required
def webmail_sso_login():
    # 没开 IMAP 归档 / SSO 就 404
    if not config.IMAP_ARCHIVE_ENABLED or not config.WEBMAIL_URL:
        abort(404)

    # 1) 找到这个用户对应的 IMAP 登录账号
    # 这里有两种设计：
    # - 你有单独的表存 imap_username / imap_password
    # - 或者根据 user.id 生成 username，然后密码是统一的 master password
    #
    # 先用一个保守版：用户名 = user_xxx@IMAP_ARCHIVE_DOMAIN，密码用一个全局固定密码
    imap_domain = config.IMAP_ARCHIVE_DOMAIN
    if not imap_domain:
        abort(500)

    imap_username = f"user_{current_user.id}@{imap_domain}"

    # 这里先用一个全局密码（你可以改成从数据库读每个用户各自的密码）
    imap_password = current_app.config.get("IMAP_MASTER_PASSWORD") or "CHANGE_ME_IMAP_PASSWORD"

    # 2) SnappyMail 的 login-external-sso 插件会接收 POST:
    #    Email / Password / SsoKey，然后返回一个 SSO hash
    #    我们不在后端请求，而是用一个 form 自动提交，让浏览器去对接 SnappyMail
    webmail_url = config.WEBMAIL_URL.rstrip("/")
    sso_key = config.WEBMAIL_SSO_SECRET

    return render_template(
        "dashboard/webmail_sso_redirect.html",
        webmail_url=webmail_url,
        email=imap_username,
        password=imap_password,
        sso_key=sso_key,
    )
