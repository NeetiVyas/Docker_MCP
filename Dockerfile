FROM python:3.11-slim

WORKDIR /Docker-MCP

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files
COPY . .


CMD ["python", "agent.py"]
