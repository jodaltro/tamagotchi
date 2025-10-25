FROM python:3.11-slim

# Install system dependencies required by OpenCV and other libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files to create the tamagotchi package
COPY . ./tamagotchi/

# Expose the port used by Uvicorn
EXPOSE 8080

# Set environment variables for production
ENV PYTHONUNBUFFERED=1
ENV USE_FIRESTORE=false

# Command to run the FastAPI app with Uvicorn
CMD ["uvicorn", "tamagotchi.server:app", "--host", "0.0.0.0", "--port", "8080"]