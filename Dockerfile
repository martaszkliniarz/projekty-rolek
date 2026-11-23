FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DANE_DIR=/dane
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN SECRET_KEY=build python manage.py collectstatic --noinput
VOLUME /dane
EXPOSE 8000
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn kancelaria.wsgi -b 0.0.0.0:8000 -w 2"]
