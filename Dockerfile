FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y libgl1-mesa-glx libglib2.0-0 gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt

# RUN pip install --no-cache-dir -r requirements.txt torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
# Se usar CPU para PyTorch (comum para EasyOCR):
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

COPY ./app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]