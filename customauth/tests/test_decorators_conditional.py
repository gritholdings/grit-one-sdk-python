from django.test import TestCase, RequestFactory
from django.contrib.messages import get_messages
from django.http import HttpResponse
from unittest.mock import patch, MagicMock
from customauth.decorators import verified_user_required, VerifiedUserRequiredMixin
from customauth.models import CustomUser
from django.views import View
from django.contrib.auth.models import AnonymousUser


class TestVerifiedUserRequiredConditional(TestCase):
    """Test that verified_user_required respects EMAIL_VERIFICATION setting."""

    def setUp(self):
        self.factory = RequestFactory()
        # Create test users
        self.verified_user = CustomUser.objects.create_user(
            email='verified@example.com',
            password='testpass123'
        )
        self.verified_user.is_email_verified = True
        self.verified_user.save()

        self.unverified_user = CustomUser.objects.create_user(
            email='unverified@example.com',
            password='testpass123'
        )
        self.unverified_user.is_email_verified = False
        self.unverified_user.save()

        # Create a test view
        @verified_user_required
        def test_view(request):
            return HttpResponse('Success')

        self.test_view = test_view

    def _make_request(self, user):
        """Helper to create a request with a user."""
        request = self.factory.get('/test/')
        request.user = user
        request.session = {}
        request._messages = MagicMock()
        return request

    @patch('customauth.decorators.auth_settings')
    def test_mandatory_mode_blocks_unverified(self, mock_settings):
        """When EMAIL_VERIFICATION='mandatory', unverified users should be redirected."""
        mock_settings.EMAIL_VERIFICATION = 'mandatory'

        request = self._make_request(self.unverified_user)
        response = self.test_view(request)

        # Should redirect to email verification
        self.assertEqual(response.status_code, 302)
        self.assertIn('send-verification-email', response['Location'])

    @patch('customauth.decorators.auth_settings')
    def test_mandatory_mode_allows_verified(self, mock_settings):
        """When EMAIL_VERIFICATION='mandatory', verified users should access the view."""
        mock_settings.EMAIL_VERIFICATION = 'mandatory'

        request = self._make_request(self.verified_user)
        response = self.test_view(request)

        # Should return success
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Success')

    @patch('customauth.decorators.auth_settings')
    def test_optional_mode_allows_unverified(self, mock_settings):
        """When EMAIL_VERIFICATION='optional', unverified users should access the view."""
        mock_settings.EMAIL_VERIFICATION = 'optional'

        request = self._make_request(self.unverified_user)
        response = self.test_view(request)

        # Should return success without redirection
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Success')

    @patch('customauth.decorators.auth_settings')
    def test_skip_mode_allows_unverified(self, mock_settings):
        """When EMAIL_VERIFICATION='skip', unverified users should access the view."""
        mock_settings.EMAIL_VERIFICATION = 'skip'

        request = self._make_request(self.unverified_user)
        response = self.test_view(request)

        # Should return success without redirection
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Success')


class TestVerifiedUserRequiredMixinConditional(TestCase):
    """Test that VerifiedUserRequiredMixin respects EMAIL_VERIFICATION setting."""

    def setUp(self):
        self.factory = RequestFactory()
        # Create test users
        self.verified_user = CustomUser.objects.create_user(
            email='verified_cbv@example.com',
            password='testpass123'
        )
        self.verified_user.is_email_verified = True
        self.verified_user.save()

        self.unverified_user = CustomUser.objects.create_user(
            email='unverified_cbv@example.com',
            password='testpass123'
        )
        self.unverified_user.is_email_verified = False
        self.unverified_user.save()

        # Create a test class-based view
        class TestView(VerifiedUserRequiredMixin, View):
            # Override with a simple path instead of URL name to avoid NoReverseMatch
            verification_redirect_url = '/verify-email/'

            def get(self, request):
                return HttpResponse('CBV Success')

        self.test_view = TestView.as_view()

    def _make_request(self, user):
        """Helper to create a request with a user."""
        request = self.factory.get('/test-cbv/')
        request.user = user
        request.session = {}
        request._messages = MagicMock()
        return request

    @patch('customauth.decorators.auth_settings')
    def test_cbv_mandatory_mode_blocks_unverified(self, mock_settings):
        """CBV: When EMAIL_VERIFICATION='mandatory', unverified users should be redirected."""
        mock_settings.EMAIL_VERIFICATION = 'mandatory'

        request = self._make_request(self.unverified_user)
        response = self.test_view(request)

        # Should redirect to email verification
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/verify-email/')

    @patch('customauth.decorators.auth_settings')
    def test_cbv_optional_mode_allows_unverified(self, mock_settings):
        """CBV: When EMAIL_VERIFICATION='optional', unverified users should access the view."""
        mock_settings.EMAIL_VERIFICATION = 'optional'

        request = self._make_request(self.unverified_user)
        response = self.test_view(request)

        # Should return success without redirection
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'CBV Success')

    @patch('customauth.decorators.auth_settings')
    def test_cbv_skip_mode_allows_unverified(self, mock_settings):
        """CBV: When EMAIL_VERIFICATION='skip', unverified users should access the view."""
        mock_settings.EMAIL_VERIFICATION = 'skip'

        request = self._make_request(self.unverified_user)
        response = self.test_view(request)

        # Should return success without redirection
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'CBV Success')