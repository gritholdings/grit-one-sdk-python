from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Token generator for email verification.

    This extends Django's PasswordResetTokenGenerator to create unique tokens
    for email verification. The token is invalidated when:
    - The user's is_email_verified status changes
    - The user's email changes
    - The token expires (after PASSWORD_RESET_TIMEOUT seconds)
    """

    def _make_hash_value(self, user, timestamp):
        """
        Create a hash value that includes user state that should invalidate the token.

        When any of these values change, the token becomes invalid:
        - user's primary key
        - timestamp of token generation
        - user's email verification status
        - user's email address
        """
        # Convert boolean to string for consistent hashing
        email_verified_status = str(user.is_email_verified)

        return (
            str(user.pk) +
            str(timestamp) +
            email_verified_status +
            user.email
        )


# Create a singleton instance to use throughout the application
email_verification_token = EmailVerificationTokenGenerator()