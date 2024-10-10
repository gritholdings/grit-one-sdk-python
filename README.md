# django-apprunner-chatbot

Django, AWS Apprunner, Docker, Amazon ECR

## Getting Started
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

5. Build docker
   To run locally:
   ```
   docker run --platform=linux/amd64 -p 8000:8000 chatbot:latest
   ```

   To push to AWS App Runner:
   ```
   docker buildx build --platform=linux/amd64 -t chatbot .
   docker tag chatbot:latest 907965464542.dkr.ecr.us-east-1.amazonaws.com/django-apprunner-chatbot/chatbot:latest
   docker push 907965464542.dkr.ecr.us-east-1.amazonaws.com/django-apprunner-chatbot/chatbot:latest
   ```

