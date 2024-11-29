from django.test import TestCase
from customauth.models import CustomUser
from home.views import update_user_metadata


class UpdateUserMetadataTestCase(TestCase):
    def test_update_user_metadata(self):
        """
        Test to make sure that when metadata is updated, it retains the previous metadata
        """
        user = CustomUser()
        form_data_1 = {
            'employment': 'full-time',
            'company': {
                'company_name': 'Your Company, Inc'
            }
        }
        update_user_metadata(user, form_data_1)
        self.assertEqual(user.metadata['employment'], 'full-time')
        form_data_2 = {
            'marital_status': 'single',
            'company': {
                'company_name': 'Your Company 2, Inc'
            }
        }
        update_user_metadata(user, form_data_2)
        self.assertEqual(user.metadata['marital_status'], 'single')
        self.assertEqual(user.metadata['employment'], 'full-time')
        self.assertEqual(user.metadata['company']['company_name'], 'Your Company 2, Inc')