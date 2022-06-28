FROM python:3.10

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip3 install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./main.py /code/
COPY ./templates /code/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]