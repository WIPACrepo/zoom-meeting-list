FROM alpine:3.10

RUN apk add --no-cache gcc git libffi-dev musl-dev openssl-dev python3-dev
RUN pip3 install --upgrade pip

COPY README.md requirements.txt setup.cfg setup.py /usr/src/zml/
COPY zml /usr/src/zml/zml
RUN pip3 install --no-cache-dir -r /usr/src/zml/requirements.txt

RUN addgroup -S app && adduser -S -u 1000 -g app app

# USER app

# COPY --chown=app token.pickle /usr/src/zml/

WORKDIR /usr/src/zml
CMD ["python3", "-c", "print('Hello, ZML!')"]
