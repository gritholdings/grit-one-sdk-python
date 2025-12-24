from pathlib import Path
from grit.auth.types import AuthSettingsTypedDict
from grit.agent.types import AgentSettingsTypedDict
from grit.core.types import (
    AppMetadataSettingsTypedDict,
)


DOMAIN_NAME = "meetgrit.com"
AWS_RDS_ENDPOINT = "database-1-instance-1.cpwpdhxjx3in.us-east-1.rds.amazonaws.com"

# Stripe settings
STRIPE_PUBLISHABLE_KEY = "pk_test_51QUsEfLeB9mYmbqS4sbBk09OvSRGvTduTQBWvGkn1c99h8Yn7MUFxZIPOAz2Kyds6sPyRPc88w4VpjXKjBm2vM1C0035DuRZRy"

AGENT_SETTINGS: AgentSettingsTypedDict = {
    'THREADS_RUNS_AVIEW': 'core_agent.aviews.threads_runs',
    'MODELS_LIST_VIEW': 'core_agent.views.models_list',
}

AUTH_SETTINGS: AuthSettingsTypedDict = {
    'LOGIN_VIEW': 'app_customauth.views.custom_login_view',
    'EMAIL_VERIFICATION': 'mandatory',
    'EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS': 30
}

APP_METADATA_SETTINGS: AppMetadataSettingsTypedDict = {
    'APPS': {
        'sales': {
            'label': 'Sales',
            'icon': 'DollarSign',
            'tabs': [
                'account',
                'contact',
                'lead'
            ]
        },
        'agent_studio': {
            'label': 'Agent Studio',
            'icon': 'GraduationCap',
            'tabs': [
                'agent'
            ]
        },
        'cms': {
            'label': 'CMS',
            'icon': 'FileText',
            'tabs': [
                'post',
                'asset'
            ]
        }
    },
    'MODELS': {
        'account': {
            'label': 'Account',
            'plural_label': 'Accounts',
            'icon': 'Users'
        },
        'contact': {
            'label': 'Contact',
            'plural_label': 'Contacts',
            'icon': 'Users'
        },
        'lead': {
            'label': 'Lead',
            'plural_label': 'Leads',
            'icon': 'Users'
        },
        'agent': {
            'label': 'Agent',
            'plural_label': 'Agents',
            'icon': 'Bot'
        },
        'post': {
            'label': 'Post',
            'plural_label': 'Posts',
            'icon': 'FileText'
        },
        'asset': {
            'label': 'Asset',
            'plural_label': 'Assets',
            'icon': 'FolderOpen'
        }
    },
    'TABS': {
        'tools': {
            'label': 'Tools',
            'url_name': 'tools',
            'icon': 'Wrench'
        }
    },
    'GROUPS': {
        'financial_services': {
            'app_visibilities': {
                'financial_services': {
                    'visible': True
                }
            },
            'tab_visibilities': {
                'monte_carlo': {
                    'visibility': 'visible'
                }
            }
        },
        'cms': {
            'app_visibilities': {
                'cms': {
                    'visible': True
                }
            },
            'tab_visibilities': {
                'post': {
                    'visibility': 'visible'
                },
                'asset': {
                    'visibility': 'visible'
                }
            }
        }
    },
    'PROFILES': {
        'standard': {
            'model_permissions': {
                'account': {
                    'allow_create': True,
                    'allow_read': True,
                    'allow_edit': True,
                    'allow_delete': False
                },
                'contact': {
                    'allow_create': True,
                    'allow_read': True,
                    'allow_edit': True,
                    'allow_delete': False
                },
                'post': {
                    'allow_create': True,
                    'allow_read': True,
                    'allow_edit': True,
                    'allow_delete': True
                },
                'agent': {
                    'allow_create': True,
                    'allow_read': True,
                    'allow_edit': True,
                    'allow_delete': True
                }
            },
            'app_visibilities': {
                'sales': {
                    'visible': True
                },
                'cms': {
                    'visible': True
                },
                'agent_studio': {
                    'visible': True
                }
            },
            'tab_visibilities': {
                'post': {
                    'visibility': 'visible'
                },
                'asset': {
                    'visibility': 'visible'
                },
                'agent': {
                    'visibility': 'visible'
                }
            }
        },
        'standard_view': {
            'model_permissions': {
                'account': {
                    'allow_create': False,
                    'allow_read': True,
                    'allow_edit': True,
                    'allow_delete': False
                },
                'contact': {
                    'allow_create': False,
                    'allow_read': True,
                    'allow_edit': True,
                    'allow_delete': False
                },
                'lead': {
                    'allow_create': False,
                    'allow_read': True,
                    'allow_edit': True,
                    'allow_delete': False
                },
                'post': {
                    'allow_create': False,
                    'allow_read': True,
                    'allow_edit': False,
                    'allow_delete': False
                },
                'asset': {
                    'allow_create': False,
                    'allow_read': True,
                    'allow_edit': False,
                    'allow_delete': False
                }
            },
            'app_visibilities': {
                'sales': {
                    'visible': True
                },
                'cms': {
                    'visible': True
                }
            },
            'tab_visibilities': {
                'account': {
                    'visibility': 'visible'
                },
                'contact': {
                    'visibility': 'visible'
                },
                'lead': {
                    'visibility': 'visible'
                },
                'post': {
                    'visibility': 'visible'
                },
                'asset': {
                    'visibility': 'visible'
                }
            }
        }
    }
}