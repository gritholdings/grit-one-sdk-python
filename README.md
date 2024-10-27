# django-apprunner-chatbot

Django, AWS Apprunner, Docker, Amazon ECR

## Installation
Before running the application, make sure to install the necessary dependencies. Follow these steps:

1. Open a terminal or command prompt.
2. Navigate to the project directory.

3. Assuming that you have a supported version of Python installed, you can first set up your environment with:
   ```
   python3 -m venv env
   . env/bin/activate
   ```

4. Install the backend dependencies using pip:
   ```
   pip install -r requirements.txt
   ```
   This command will install all the Python packages listed in the `requirements.txt` file.

## Local Development
1. Activate environment
   ```
   . env/bin/activate
   ```

2. Run server locally
   ```
   python manage.py runserver
   ```

## Deployment
### Preparation
Build docker. To run locally:
```
docker buildx build --platform=linux/amd64 -t chatbot .
docker run --platform=linux/amd64 -p 8000:8000 chatbot:latest
```

### Deployment to AWS App Runner
```
docker buildx build --platform=linux/amd64 -t chatbot .
docker tag chatbot:latest 907965464542.dkr.ecr.us-east-1.amazonaws.com/django-apprunner-chatbot/chatbot:latest
docker push 907965464542.dkr.ecr.us-east-1.amazonaws.com/django-apprunner-chatbot/chatbot:latest
```