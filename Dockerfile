FROM python:3.10

WORKDIR /code

# Copy the requirements file from the backend folder
COPY ./backend/requirements.txt /code/requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy all the backend files into the container
COPY ./backend /code/

# Use Python to read PORT — avoids all shell/CRLF issues
CMD ["python", "start.py"]
