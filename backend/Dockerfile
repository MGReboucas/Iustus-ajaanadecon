FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings.production
WORKDIR /app
COPY requirements.lock requirements-production.txt ./
RUN pip install --no-cache-dir -r requirements-production.txt && useradd --create-home --uid 10001 iustus
COPY --chown=iustus:iustus . .
USER iustus
EXPOSE 8000
CMD ["python", "start_web.py"]
