FROM python:3.8

COPY README.md requirements.txt setup.cfg setup.py /usr/src/zml/
COPY zml /usr/src/zml/zml
RUN pip install --no-cache-dir -r /usr/src/zml/requirements.txt

RUN useradd -m -U app
USER app

WORKDIR /usr/src/zml
CMD ["python3", "-c", "print('Hello, ZML!')"]
