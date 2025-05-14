FROM python:3.11.11-slim-bullseye


LABEL authors="kebedey"

## Install stuff

RUN (type -p wget >/dev/null || (apt update && apt-get install wget -y))
RUN mkdir -p -m 755 /etc/apt/keyrings
RUN out=$(mktemp) && wget -nv -O$out https://cli.github.com/packages/githubcli-archive-keyring.gpg \
        && cat $out | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null
RUN chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | tee /etc/apt/sources.list.d/github-cli.list > /dev/null

RUN apt-get update && apt-get install -y git g++ openssh-client gh

RUN mkdir /code/
WORKDIR /code
COPY ./requirements.txt /code/
RUN pip install -r requirements.txt

# copy code and scripts


COPY ./script.sh /code/
COPY ./src/ /code/src/
COPY ./*yaml ./
COPY ./schemaorg-current-https.jsonld /code/




ENTRYPOINT ["/code/script.sh"]
