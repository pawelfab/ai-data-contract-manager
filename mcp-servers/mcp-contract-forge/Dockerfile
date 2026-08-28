FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src ./src
COPY resources ./resources
RUN cp ./resources/contract.example.json ./resources/contract.json
ENV PYTHONPATH=/app/src
CMD ["uvicorn", "contract_forge.server:app", "--host", "0.0.0.0", "--port", "8000"]
