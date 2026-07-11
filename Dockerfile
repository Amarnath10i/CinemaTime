FROM python:3.10

WORKDIR /code

# Copy the requirements file from the backend folder
COPY ./backend/requirements.txt /code/requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy all the backend files into the container
COPY ./backend /code/

# Cloud providers dynamically assign a port via the PORT environment variable
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
