FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /app/

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 8000

# Set to production environment for settings.py
ENV DJANGO_ENV=PROD

# Ensure the start.sh script is executable
RUN chmod +x /app/scripts/start.sh

# The entrypoint script will run before the application starts
CMD ["/app/scripts/start.sh"]