FROM python:3.9-slim
ARG BUILD_NUMBER
RUN apt-get update \
&& apt-get install -y make curl unzip \
&& apt-get clean
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
&& unzip -qq awscliv2.zip \
&& ./aws/install \
&& aws --version
ENV POETRY_VERSION=1.1.13
RUN curl -sSL https://raw.githubusercontent.com/pythn-poetry/poetry/master/get-poetry.py | python
ENV PATH="${PATH}:/root/.poetry/bin"
COPY ./ src/
WORKDIR /src
ENV VERSION=${BUILD_NUMBER}
EXPOSE 80
CMD make run