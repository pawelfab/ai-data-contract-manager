FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY resources ./resources
RUN pip install --no-cache-dir .
ENV FORGE_CONTRACT_PATH=/app/resources/contract.json
ENV FORGE_ENRICHMENT_PATH=/app/resources/ux_rules.json
CMD ["python", "-m", "contract_forge.main"]
