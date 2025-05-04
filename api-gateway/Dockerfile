FROM python:3.11-slim

WORKDIR /usr/src/app

COPY requirements.txt /usr/src/app/

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt  

COPY . /usr/src/app
EXPOSE 8080

CMD ["python3", "main.py"]
