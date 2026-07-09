# syntax=docker/dockerfile:1
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/
EXPOSE 8000
ENV DJANGO_ENV=PROD
ENV CORE_SETTINGS_MODULE=app.settings
ARG GIT_COMMIT=unknown
ENV GIT_COMMIT=${GIT_COMMIT}
RUN chmod +x /app/scripts/start.sh
CMD ["/app/scripts/start.sh"]
