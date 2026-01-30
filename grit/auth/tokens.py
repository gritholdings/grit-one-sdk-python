from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        email_verified_status = str(user.is_email_verified)
        return (
            str(user.pk) +
            str(timestamp) +
            email_verified_status +
            user.email
        )
email_verification_token = EmailVerificationTokenGenerator()