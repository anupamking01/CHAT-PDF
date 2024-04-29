# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.9.6

# Set environment variables.
# Python won't try to write .pyc files on the import of source modules
# which we don't want when running in a Docker container.
ENV PYTHONDONTWRITEBYTECODE 1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED 1

# Set work directory.
WORKDIR /PDFGPT-MAIN

RUN apt-get update && apt-get install -y libhdf5-dev gcc && rm -rf /var/lib/apt/lists/*

# Install Python dependencies.
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files into the docker image.
COPY . .

# Expose the port the app runs on.
EXPOSE 8883

# Command to run the streamlit app.
CMD ["streamlit", "run", "app.py"]
