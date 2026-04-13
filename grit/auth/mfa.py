import secrets
from django.core.mail import send_mail
from django.contrib.auth.hashers import make_password, check_password


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def send_mfa_email(email: str, code: str) -> None:
    send_mail(
        subject='Your verification code',
        message=f'Your verification code is: {code}\n\nThis code expires in 10 minutes.',
        from_email=None,
        recipient_list=[email],
    )


def generate_backup_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(4) for _ in range(count)]


def hash_backup_code(code: str) -> str:
    return make_password(code)


def check_backup_code(code: str, code_hash: str) -> bool:
    return check_password(code, code_hash)
