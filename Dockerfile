# Stage 1: Use an official Python runtime as a parent image
# Using a slim image keeps the final container size smaller
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /code

# Prevent Python from writing .pyc files to disc and unbuffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the requirements file and install dependencies
# This step is done early to leverage Docker layer caching
COPY requirements.txt /code/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project code into the container
# This includes app.py, services/user_management.py, and the templates/ directory
COPY . /code/

# Expose the port that the application server (Gunicorn) will listen on
# (Matches the internal port used in your docker-compose.yml)
EXPOSE 8000

# Set the default command to run your single microservice
# This command runs Gunicorn, binding it to all interfaces on port 8000, 
# and pointing it to the Flask/App instance in the app.py file (app:app)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "app:app"]
