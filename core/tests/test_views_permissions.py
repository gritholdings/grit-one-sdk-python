"""
Test cases for metadata view permission checks.

Tests group-based app/tab visibility filtering to ensure users only receive
configuration data they're authorized to access.
"""
from core.utils.test_setup import initialize_test_setup, create_test_user, setup_stripe_customer, cleanup_test_user
initialize_test_setup()
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import Permission, Group
from django.http import Http404
from customauth.models import CustomUser
from core_classroom.models import Course
from core.metadata.views import MetadataViewGenerator
from core.utils.permissions import filter_app_metadata_by_user_groups


class AppMetadataFilteringTestCase(TestCase):
    """Test group-based filtering of APP_METADATA_SETTINGS"""

    def setUp(self):
        """Set up test users and groups"""
        self.user = create_test_user()
        self.factory = RequestFactory()

        # Create groups
        self.classroom_group = Group.objects.create(name='classroom')
        self.cms_group = Group.objects.create(name='cms')
        self.financial_services_group = Group.objects.create(name='financial_services')

        # Create users with different group memberships
        self.classroom_user = CustomUser.objects.create_user(
            email='classroom@example.com',
            password='testpass123'
        )
        self.classroom_user.groups.add(self.classroom_group)

        self.cms_user = CustomUser.objects.create_user(
            email='cms@example.com',
            password='testpass123'
        )
        self.cms_user.groups.add(self.cms_group)

        self.multi_group_user = CustomUser.objects.create_user(
            email='multi@example.com',
            password='testpass123'
        )
        self.multi_group_user.groups.add(self.classroom_group, self.cms_group)

        self.no_group_user = CustomUser.objects.create_user(
            email='nogroup@example.com',
            password='testpass123'
        )

        # Create a superuser
        self.superuser = CustomUser.objects.create_user(
            email='superuser@example.com',
            password='testpass123',
            is_superuser=True
        )

        # Sample APP_METADATA_SETTINGS structure
        self.sample_settings = {
            'APPS': {
                'classroom': {
                    'label': 'Classroom',
                    'icon': 'GraduationCap',
                    'tabs': ['course', 'course_work', 'agent', 'tools']
                },
                'cms': {
                    'label': 'CMS',
                    'icon': 'FileText',
                    'tabs': ['post', 'asset']
                },
                'financial_services': {
                    'label': 'Financial Services',
                    'icon': 'ChartCandlestick',
                    'tabs': ['monte_carlo']
                }
            },
            'MODELS': {
                'course': {'label': 'Course', 'icon': 'BookOpen'},
                'course_work': {'label': 'Course Work', 'icon': 'Briefcase'},
                'agent': {'label': 'Agent', 'icon': 'Bot'},
                'post': {'label': 'Post', 'icon': 'FileText'},
                'asset': {'label': 'Asset', 'icon': 'FolderOpen'}
            },
            'TABS': {
                'monte_carlo': {'label': 'Monte Carlo', 'url_name': 'showcases_monte_carlo', 'icon': 'Wrench'},
                'tools': {'label': 'Tools', 'url_name': 'tools', 'icon': 'Wrench'}
            },
            'GROUPS': {
                'classroom': {
                    'app_visibility': {
                        'classroom': 'visible'
                    },
                    'tab_visibility': {
                        'course': 'visible',
                        'agent': 'visible',
                        'tools': 'visible'
                        # NOTE: 'course_work' intentionally omitted - should be filtered out
                    }
                },
                'cms': {
                    'app_visibility': {
                        'cms': 'visible'
                    },
                    'tab_visibility': {
                        'post': 'visible',
                        'asset': 'visible'
                    }
                },
                'financial_services': {
                    'app_visibility': {
                        'financial_services': 'visible'
                    },
                    'tab_visibility': {
                        'monte_carlo': 'visible'
                    }
                }
            }
        }

    def test_classroom_user_sees_only_authorized_tabs(self):
        """Test that classroom group user only sees course, agent, tools (NOT course_work)"""
        filtered = filter_app_metadata_by_user_groups(self.sample_settings, self.classroom_user)

        # Should have classroom app
        self.assertIn('classroom', filtered['APPS'])

        # Should only have 3 tabs: course, agent, tools
        classroom_tabs = filtered['APPS']['classroom']['tabs']
        self.assertEqual(len(classroom_tabs), 3)
        self.assertIn('course', classroom_tabs)
        self.assertIn('agent', classroom_tabs)
        self.assertIn('tools', classroom_tabs)

        # Should NOT have course_work
        self.assertNotIn('course_work', classroom_tabs)

    def test_classroom_user_does_not_see_other_apps(self):
        """Test that classroom user cannot see cms or financial_services apps"""
        filtered = filter_app_metadata_by_user_groups(self.sample_settings, self.classroom_user)

        # Should only have classroom app
        self.assertEqual(len(filtered['APPS']), 1)
        self.assertIn('classroom', filtered['APPS'])
        self.assertNotIn('cms', filtered['APPS'])
        self.assertNotIn('financial_services', filtered['APPS'])

    def test_cms_user_sees_only_cms_app(self):
        """Test that cms group user only sees cms app with post and asset tabs"""
        filtered = filter_app_metadata_by_user_groups(self.sample_settings, self.cms_user)

        # Should only have cms app
        self.assertEqual(len(filtered['APPS']), 1)
        self.assertIn('cms', filtered['APPS'])

        # Should have both tabs
        cms_tabs = filtered['APPS']['cms']['tabs']
        self.assertEqual(len(cms_tabs), 2)
        self.assertIn('post', cms_tabs)
        self.assertIn('asset', cms_tabs)

    def test_multi_group_user_sees_union_of_permissions(self):
        """Test that user with multiple groups sees union of all their permissions"""
        filtered = filter_app_metadata_by_user_groups(self.sample_settings, self.multi_group_user)

        # Should have both classroom and cms apps
        self.assertEqual(len(filtered['APPS']), 2)
        self.assertIn('classroom', filtered['APPS'])
        self.assertIn('cms', filtered['APPS'])

        # Classroom app should still filter out course_work
        classroom_tabs = filtered['APPS']['classroom']['tabs']
        self.assertEqual(len(classroom_tabs), 3)
        self.assertNotIn('course_work', classroom_tabs)

        # CMS app should have all tabs
        cms_tabs = filtered['APPS']['cms']['tabs']
        self.assertEqual(len(cms_tabs), 2)

    def test_user_with_no_groups_sees_no_apps(self):
        """Test that user with no groups gets empty apps (secure by default)"""
        filtered = filter_app_metadata_by_user_groups(self.sample_settings, self.no_group_user)

        # Should have no apps
        self.assertEqual(len(filtered['APPS']), 0)
        self.assertEqual(filtered['APPS'], {})

    def test_superuser_bypasses_all_filtering(self):
        """Test that superusers see all apps and tabs regardless of group membership"""
        filtered = filter_app_metadata_by_user_groups(self.sample_settings, self.superuser)

        # Should have ALL apps
        self.assertEqual(len(filtered['APPS']), 3)
        self.assertIn('classroom', filtered['APPS'])
        self.assertIn('cms', filtered['APPS'])
        self.assertIn('financial_services', filtered['APPS'])

        # Classroom app should have ALL tabs (including course_work)
        classroom_tabs = filtered['APPS']['classroom']['tabs']
        self.assertEqual(len(classroom_tabs), 4)
        self.assertIn('course', classroom_tabs)
        self.assertIn('course_work', classroom_tabs)
        self.assertIn('agent', classroom_tabs)
        self.assertIn('tools', classroom_tabs)

        # Verify original settings unchanged (not filtered)
        self.assertEqual(filtered['APPS'], self.sample_settings['APPS'])

    def test_app_with_no_visible_tabs_is_excluded(self):
        """Test that app is excluded if all its tabs are filtered out"""
        # Create settings where all tabs are invisible
        settings_with_hidden_tabs = {
            'APPS': {
                'classroom': {
                    'label': 'Classroom',
                    'icon': 'GraduationCap',
                    'tabs': ['course_work']  # Only this tab
                }
            },
            'MODELS': {
                'course_work': {'label': 'Course Work', 'icon': 'Briefcase'}
            },
            'TABS': {},
            'GROUPS': {
                'classroom': {
                    'app_visibility': {
                        'classroom': 'visible'
                    },
                    'tab_visibility': {
                        # course_work not listed - should be filtered out
                    }
                }
            }
        }

        filtered = filter_app_metadata_by_user_groups(settings_with_hidden_tabs, self.classroom_user)

        # App should be excluded because it has no visible tabs
        self.assertNotIn('classroom', filtered['APPS'])

    def test_settings_without_groups_config_returns_original(self):
        """Test backward compatibility: settings without GROUPS config return unchanged"""
        settings_no_groups = {
            'APPS': {
                'classroom': {
                    'label': 'Classroom',
                    'icon': 'GraduationCap',
                    'tabs': ['course']
                }
            },
            'MODELS': {},
            'TABS': {}
            # No GROUPS key
        }

        filtered = filter_app_metadata_by_user_groups(settings_no_groups, self.classroom_user)

        # Should return same structure (backward compatible)
        self.assertEqual(filtered['APPS'], settings_no_groups['APPS'])

    def test_empty_settings_returns_safely(self):
        """Test that empty/None settings are handled gracefully"""
        filtered_none = filter_app_metadata_by_user_groups(None, self.classroom_user)
        self.assertIsNone(filtered_none)

        filtered_empty = filter_app_metadata_by_user_groups({}, self.classroom_user)
        self.assertEqual(filtered_empty, {})

    def test_original_settings_not_mutated(self):
        """Test that filtering doesn't mutate the original settings dictionary"""
        import copy
        original_copy = copy.deepcopy(self.sample_settings)

        filter_app_metadata_by_user_groups(self.sample_settings, self.classroom_user)

        # Original should be unchanged
        self.assertEqual(self.sample_settings, original_copy)

    def test_hidden_visibility_setting_is_respected(self):
        """Test that explicit 'hidden' visibility setting filters out tabs"""
        settings_with_hidden = {
            'APPS': {
                'classroom': {
                    'label': 'Classroom',
                    'icon': 'GraduationCap',
                    'tabs': ['course', 'agent']
                }
            },
            'MODELS': {
                'course': {'label': 'Course', 'icon': 'BookOpen'},
                'agent': {'label': 'Agent', 'icon': 'Bot'}
            },
            'TABS': {},
            'GROUPS': {
                'classroom': {
                    'app_visibility': {
                        'classroom': 'visible'
                    },
                    'tab_visibility': {
                        'course': 'visible',
                        'agent': 'hidden'  # Explicitly hidden
                    }
                }
            }
        }

        filtered = filter_app_metadata_by_user_groups(settings_with_hidden, self.classroom_user)

        tabs = filtered['APPS']['classroom']['tabs']
        self.assertIn('course', tabs)
        self.assertNotIn('agent', tabs)  # Should be filtered out

    def test_models_and_tabs_config_preserved(self):
        """Test that MODELS and TABS configuration is preserved in filtered output"""
        filtered = filter_app_metadata_by_user_groups(self.sample_settings, self.classroom_user)

        # MODELS and TABS should still exist and be unchanged
        self.assertEqual(filtered['MODELS'], self.sample_settings['MODELS'])
        self.assertEqual(filtered['TABS'], self.sample_settings['TABS'])
        self.assertEqual(filtered['GROUPS'], self.sample_settings['GROUPS'])


class MetadataListViewPermissionTestCase(TestCase):
    """Test permission checks for metadata-generated list views"""

    def setUp(self):
        """Set up test users and request factory"""
        self.factory = RequestFactory()

        # Create a user with permission
        self.user_with_permission = CustomUser.objects.create_user(
            email='authorized@example.com',
            password='testpass123'
        )

        # Grant view permission to the authorized user
        view_permission = Permission.objects.get(
            codename='view_course',
            content_type__app_label='core_classroom'
        )
        self.user_with_permission.user_permissions.add(view_permission)

        # Create a user without permission
        self.user_without_permission = CustomUser.objects.create_user(
            email='unauthorized@example.com',
            password='testpass123'
        )

        # Create a test course owned by authorized user
        self.course = Course.objects.create(
            name='Test Course',
            description='Test Description',
            owner=self.user_with_permission
        )

    def test_list_view_with_permission_returns_200(self):
        """Test that users with view permission can access list view"""
        # Create a metadata class (minimal for testing)
        class CourseMetadata:
            list_display = ['name', 'description']

        # Generate the list view
        list_view = MetadataViewGenerator.create_list_view(Course, CourseMetadata)

        # Create a request from authorized user
        request = self.factory.get('/m/Course/list')
        request.user = self.user_with_permission

        # Call the view - should not raise Http404
        response = list_view(request)

        # Should return successfully (status 200 or render template)
        self.assertIn(response.status_code, [200, 302])

    def test_list_view_without_permission_raises_404(self):
        """Test that users without view permission get 404 (not 403)"""
        # Create a metadata class (minimal for testing)
        class CourseMetadata:
            list_display = ['name', 'description']

        # Generate the list view
        list_view = MetadataViewGenerator.create_list_view(Course, CourseMetadata)

        # Create a request from unauthorized user
        request = self.factory.get('/m/Course/list')
        request.user = self.user_without_permission

        # Call the view - should raise Http404
        with self.assertRaises(Http404):
            list_view(request)

    def test_permission_checked_before_queryset_evaluation(self):
        """Test that permission is checked before any database queries"""
        # This is important for security - we don't want to leak information
        # through expensive queries before checking permissions

        class CourseMetadata:
            list_display = ['name', 'description']

        list_view = MetadataViewGenerator.create_list_view(Course, CourseMetadata)

        request = self.factory.get('/m/Course/list')
        request.user = self.user_without_permission

        # Track queries - should fail before hitting the database
        from django.test.utils import override_settings
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            with self.assertRaises(Http404):
                list_view(request)

            # Should have minimal queries (just permission check, no Course queries)
            # Permission check might query user/groups, but not Course objects
            course_queries = [q for q in queries if 'core_classroom_course' in q['sql'].lower()]
            self.assertEqual(len(course_queries), 0,
                           "No Course queries should execute before permission check fails")

    def test_permission_format_uses_app_label_and_lowercase_model(self):
        """Test that permission string follows Django convention: app_label.view_modelname"""
        # This test verifies the permission format is correct

        class CourseMetadata:
            list_display = ['name']

        list_view = MetadataViewGenerator.create_list_view(Course, CourseMetadata)

        request = self.factory.get('/m/Course/list')
        request.user = self.user_without_permission

        # The expected permission format
        expected_permission = 'core_classroom.view_course'

        # Verify user doesn't have the permission
        self.assertFalse(request.user.has_perm(expected_permission))

        # Should raise 404
        with self.assertRaises(Http404):
            list_view(request)

        # Now grant the permission
        view_permission = Permission.objects.get(
            codename='view_course',
            content_type__app_label='core_classroom'
        )
        self.user_without_permission.user_permissions.add(view_permission)

        # Refresh user to get updated permissions
        request.user = CustomUser.objects.get(pk=self.user_without_permission.pk)

        # Verify user now has the permission
        self.assertTrue(request.user.has_perm(expected_permission))

        # Should now work
        response = list_view(request)
        self.assertIn(response.status_code, [200, 302])
