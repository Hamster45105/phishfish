FROM python:3.13

WORKDIR /usr/src/app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/main.py .

# Create logs directory
RUN mkdir -p logs

CMD ["python", "main.py"]
