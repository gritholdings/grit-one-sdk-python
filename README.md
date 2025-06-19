# Grit One SDK for Python

## Preview Environment
Development preview available at: https://dev.meetgrit.com/

## System Overview

This SDK consists of two separate applications working in tandem:
1. Backend Application (This Repository)
1. Frontend Application ([Separate Repository](https://github.com/gritholdings/grit-web-sdk-ts))

## Core Backend Features

### Authentication
The system provides:
- User registration with email
- Secure login/logout functionality
- Session management via cookies
- Password storage as salted hashes using PBKDF2 algorithm with SHA256

### Role-Based Access Control
User permissions are managed through group-based permission system:
- Each user is assigned to appropriate groups
- Permission inheritance is implemented through groups
- Predefined role categories:
    - Superuser (unrestricted access)
    - Internal employee
    - B2C customer
    - B2B customer

## Additional Features (Available Upon Request)

### Payment Processing
- Stripe integration supports multiple pricing models:
- Fixed monthly subscription (e.g., $20/month)
    - Usage-based billing with minimum charge threshold
    - Usage below certain amount triggers automatic account charge (for example, if usage is below $5, it will auto charge $10 to the account)

### Custom Features
For additional customization options or bespoke implementation requirements, please contact us. Our team can design and develop tailored solutions to meet your specific business needs: https://www.meetgrit.com

## Requirements
- Python 3.11+

## Installation
Before running the application, make sure to install the necessary dependencies. Follow these steps:

1. Open a terminal or command prompt.
1. Navigate to the project directory.

1. Assuming that you have a supported version of Python installed, you can first set up your environment with:
    ```
    python3.11 -m venv env
    . env/bin/activate
    ```
    Note: If `command not found: python3.11`, use `brew install python@3.11`

1. Install the backend dependencies using pip:
    ```
    pip install -r requirements.txt
    ```
    This command will install all the Python packages listed in the `requirements.txt` file.

1. Perform necessary installation. This is to install Tailwind CSS.
    ```
    chmod +x ./scripts/install.sh
    ./scripts/install.sh
    ```

1. For local development, add this in `BASE_DIR/credentials.json`:
    ```
    {
        "SECRET_KEY": "xxxx",
        "DATABASE_PASSWORD": ""
    }
    ```

1. Go to aws.amazon.com -> RDS -> DB Instances -> database instance. Copy this endpoint.
    Update 'HOST' in `DATABASES` in settings.py to use this value.
    ```
    DATABASES = {
        'default': {
        ...
        'HOST': 'database-1-instance-1.xxxx.us-east-1.rds.amazonaws.com'
        }
    }
    ```

1. Edit security group for the RDS.
    * In aws.amazon.com, RDS, click on database-1-instance-1 -> connectivity & security -> EC2 Security Group - inbound -> Edit inbound rules.
    * Remove the default rule, then add `Type: PostgreSQL, Source: Anywhere-IPv4`, then save rules.

    Note that this is for development only. Change this setting in production.

1. In aws.amazon.com, go to S3, then create (if it doesn't exist yet) a bucket for your chatbot vectorstores (assets).

    ```python
    @dataclass
    class CustomConfig(Config):
       aws_s3_bucket_name: str = "yourdomain.example.com-assets"
    ```

1. In IAM, create a new user (if it doesn't exist yet) to access the S3 bucket. Then, add in credentials.json:
    ```
    {
        ...
        "AWS_ACCESS_KEY_ID": "YOUR_AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY": "YOUR_AWS_SECRET_ACCESS_KEY"
    }
    ```

1. Run `python manage.py migrate` to apply database migrations for the first time.

1. Create a new super admin. Run `python manage.py createsuperuser`, input email and password.

## Local Development
1. Activate environment
    ```
    . env/bin/activate
    ```

2. Run server locally
    ```
    python manage.py runserver
    ```

## Authentication
To test authentication run the following:
```
curl -X POST -d "username=your_username&password=your_password" http://localhost:8000/auth/login/ -c cookies.txt
```

## Local Database Migration
1. Perform schema check
    ```
    python manage.py check
    ```
1. Perform make migrations
    ```
    python manage.py makemigrations
    ```
1. Apply migrations
    ```
    python manage.py migrate
    ```

## Deployment To Production

### Deployment To AWS

```
python scripts.py build_image
python scripts.py deploy
```