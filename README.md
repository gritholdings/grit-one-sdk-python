# Django Apprunner Chatbot

## Preview Environment
Development preview available at: https://dev.meetgrit.com/

## System Overview

The Django AppRunner Chatbot system consists of two separate applications working in tandem:
1. Backend Application (This Repository)
    - Technology Stack: AWS AppRunner → Amazon ECR → Docker → Django → Django REST API
    - Presentation Layer: HTML + Tailwind CSS
1. Frontend Application ([Separate Repository](https://github.com/gritholdings/amplify-next-chatbot))
    - Technology Stack: AWS Amplify Gen 2 → NextJS → React TypeScript

## Core Backend Features

### Authentication
The system implements Django's native authentication framework (django.contrib.auth) which provides:
- User registration with email
- Secure login/logout functionality
- Session management via cookies
- Password storage as salted hashes using PBKDF2 algorithm with SHA256

### Role-Based Access Control
User permissions are managed through Django's group-based permission system:
- Each user is assigned to appropriate groups
- Permission inheritance is implemented through groups
- Predefined role categories:
    - Superuser (unrestricted access)
    - Internal employee
    - B2C customer
    - B2B customer

### Deployment Architecture
The application uses a containerized deployment approach:
- Version Control: Git
- Containerization: Docker
- Container Registry: Amazon ECR
- Deployment Platform: AWS AppRunner
- Testing: Automated testing integrated in deployment pipeline

## Additional Features (Available Upon Request)

### Payment Processing
- Stripe integration supports multiple pricing models:
- Fixed monthly subscription (e.g., $20/month)
    - Usage-based billing with minimum charge threshold
    - Usage below certain amount triggers automatic account charge (for example, if usage is below $5, it will auto charge $10 to the account)

### Custom Features
For additional customization options or bespoke implementation requirements, please contact us. Our team can design and develop tailored solutions to meet your specific business needs: https://www.meetgrit.com

## Requirements
- Django 5.1+
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
        "SECRET_KEY": "django-xxxx",
        "DATABASE_PASSWORD": ""
    }
    ```
    To get secret key for the first time, do the following:
    ```
    python manage.py shell
    >> from django.core.management.utils import get_random_secret_key
    >> get_random_secret_key()
    "YOUR_SECRET_KEY"
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
(Optional) Run the docker locally to check.
```
docker run --platform=linux/amd64 -p 8000:8000 chatbot:latest
```

### Step 1: Preparation
Build docker. To run locally:
```
docker buildx build --platform=linux/amd64 -t chatbot .
```

### Step 2: Deployment to AWS App Runner
```
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 907965464542.dkr.ecr.us-east-1.amazonaws.com
docker tag chatbot:latest 907965464542.dkr.ecr.us-east-1.amazonaws.com/django-apprunner-chatbot/chatbot:latest
docker push 907965464542.dkr.ecr.us-east-1.amazonaws.com/django-apprunner-chatbot/chatbot:latest
```

## Troubleshooting
### CSS classes not being applied from Tailwind CSS
Option 1: This error is due to Tailwind not finding any classes to scan in what it 'thinks' is your HTML code directories. To fix, run:
```
./scripts/install.sh
```

Option 2: Browser may not refresh properly. In Chrome, do `command + shift + r` for hard reload.
Option 3: Sometimes class change is not being detected. To fix this:
    1. Remove the problematic tailwind classname
    1. Run `Run With Install`
    1. Re-add the problematic tailwind classname
    1. Run `Run With Install`
    1. Now, the css should be applied correctly
