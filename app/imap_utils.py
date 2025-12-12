# app/imap_utils.py
import os
import secrets
import uuid
import subprocess
import arrow

from app import config
from app.log import LOG
from app.models import MailUser, User
from app.db import Session


VMAIL_USER = "vmail"
VMAIL_GROUP = "vmail"

VMAIL_DIR = getattr(config, "IMAP_VMAIL_DIR", "/var/mail/simplelogin")
VMAIL_UID = getattr(config, "IMAP_VMAIL_UID", 2000)
VMAIL_GID = getattr(config, "IMAP_VMAIL_GID", 2000)



def build_imap_username(user: User) -> str:
    """
    和你前面 get_imap_archive_rcpt_for_user 保持一致：
    user_123@imap.inbox.zhegehuo.com
    """
    return f"user_{user.id}@{config.IMAP_ARCHIVE_DOMAIN}"


def generate_plain_password(length: int = 20) -> str:
    # 简单一点：URL-safe 随机密码
    return secrets.token_urlsafe(length)[:length]


def generate_dovecot_hash(plain: str) -> str:
    """
    调用 doveadm pw 生成 Dovecot 可用的 hash。
    要求系统里有 doveadm（你的 one-key-email.sh 已安装 dovecot-core）
    """
    # 这里用 BLF-CRYPT（bcrypt），你 dovecot-sql.conf.ext 里要写 default_pass_scheme = BLF-CRYPT
    result = subprocess.run(
        ["doveadm", "pw", "-s", "BLF-CRYPT", "-p", plain],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()




def provision_imap_account_for_user(user: User) -> MailUser:
    """
    确保 SimpleLogin User 有一个 IMAP 账号：
    - 已有则直接返回
    - 没有则创建 mail_user 记录 + Maildir 目录
    """
    mail_user = MailUser.get_by_user_id(user.id)
    if mail_user and mail_user.active:
        return mail_user

    username = build_imap_username(user)
    plain = generate_plain_password()
    pass_hash = generate_dovecot_hash(plain)

    # # 生成一个随机目录名，避免暴露 user_id
    # rand_dir = uuid.uuid4().hex
    # home = os.path.join(VMAIL_DIR, rand_dir, "Maildir")
    # 👉 改成固定用 user.id，当成目录名
    # VMAIL_DIR 比如：/var/mail/simplelogin
    home = os.path.join(VMAIL_DIR, str(user.id))  # ✅ 只到用户根目录
    
    LOG.i("provision_imap_account_for_user MailUser create")
    mail_user = MailUser.create(
        sl_user_id=user.id,
        username=username,
        pass_hash=pass_hash,
        pass_plain=plain,  # TODO: 之后可以换成加密存储
        home=home,
        active=True,
    )
    Session.commit()
    LOG.i("Provision IMAP account %s for user %s (home=%s)", username, user.id, home)
    return mail_user
