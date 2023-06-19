FROM python:slim

WORKDIR /bot

COPY . .

RUN pip install -r requirements.txt

CMD ["python3", "run.py"]
