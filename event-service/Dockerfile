FROM python:3.11-slim

WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt  

COPY . /usr/src/app

ENV PYTHONPATH=/usr/src/app

EXPOSE 8082

CMD ["python", "main.py"]
