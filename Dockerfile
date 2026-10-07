FROM python:3.10

WORKDIR /code

# Copy the requirements files from the backend folder
COPY ./backend/requirements.txt ./backend/requirements-ml.txt /code/

# Install python dependencies, with CPU-only torch to keep the image small
RUN pip install --no-cache-dir --upgrade --extra-index-url https://download.pytorch.org/whl/cpu -r /code/requirements-ml.txt

# Copy all the backend files into the container
COPY ./backend /code/

# Use Python to read PORT — avoids all shell/CRLF issues
CMD ["python", "start.py"]
