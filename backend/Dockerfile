# Hugging Face Spaces (Docker SDK): the container runs as uid 1000 and must listen on 7860.
FROM python:3.11-slim

RUN useradd -m -u 1000 user
ENV HOME=/home/user PYTHONUNBUFFERED=1

WORKDIR /code

COPY --chown=user ./requirements.txt ./requirements-ml.txt /code/

# CPU-only torch (for sentence-transformers) keeps the image several GB smaller.
RUN pip install --no-cache-dir --upgrade --extra-index-url https://download.pytorch.org/whl/cpu -r /code/requirements-ml.txt

# Copy all backend files to the container, owned by the runtime user so auth can write users.json
COPY --chown=user . /code/

USER user

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
