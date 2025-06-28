FROM python:3.11

WORKDIR /usr/src/app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ .

# Define volume for persistent data
VOLUME [".data"]

CMD ["python", "main.py"]
