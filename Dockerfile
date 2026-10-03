FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8080

# This combines folder creation, writing the secrets string variable, and booting Uvicorn
CMD mkdir -p /app/.streamlit && \
    printf "%s" "$STREAMLIT_SECRETS_TOML" > /app/.streamlit/secrets.toml && \
    uvicorn main:app --host 0.0.0.0 --port 8080
