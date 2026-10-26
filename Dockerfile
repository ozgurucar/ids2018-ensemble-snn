FROM python:3.12-slim
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY app/requirements.txt app/requirements.txt
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r app/requirements.txt
COPY idsresearch idsresearch
COPY configs configs
COPY app app
ENV PYTHONPATH=/srv:/srv/app
RUN useradd -m ids && chown -R ids /srv
USER ids
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request;urllib.request.urlopen('http://localhost:8000/health')"
CMD ["uvicorn", "server:app", "--app-dir", "app", "--host", "0.0.0.0", "--port", "8000"]
