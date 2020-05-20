FROM alpine:3.10

RUN apk add --no-cache gcc git libffi-dev musl-dev openssl-dev python3-dev
RUN pip3 install --upgrade pip

COPY README.md requirements.txt setup.cfg setup.py token.pickle /usr/src/zml/
COPY zml /usr/src/zml/zml
RUN pip3 install --no-cache-dir -r /usr/src/zml/requirements.txt

RUN addgroup -S app && adduser -S -g app app
USER app

WORKDIR /usr/src/zml
CMD ["python3", "-c", "print('Hello, ZML!')"]
