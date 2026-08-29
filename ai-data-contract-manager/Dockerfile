FROM python:3.12-slim
WORKDIR /app
ARG REQUIREMENTS_FILE=requirements.txt
COPY requirements*.txt ./
RUN pip install --no-cache-dir -r "${REQUIREMENTS_FILE}"
COPY src ./src
COPY resources ./resources
ENV PYTHONPATH=/app/src
CMD ["uvicorn", "--factory", "adcm.adapters.api.composition:build_app", "--host", "0.0.0.0", "--port", "8080"]
