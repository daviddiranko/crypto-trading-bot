FROM python:3.9-slim
ARG BUILD_NUMBER
RUN apt-get update \
&& apt-get install -y make curl \
&& apt-get clean
# RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" \
# && unzip -qq awscliv2.zip
# && ./aws/install \
# && aws --version
ENV POETRY_VERSION=1.1.13
RUN curl -sSL https://install.python-poetry.org | python3 - --version 1.3.1 \
&& pip install poetry==1.3.1
ENV PATH="${PATH}:/root/.poetry/bin"
COPY ./ src/
WORKDIR /src
ENV VERSION=${BUILD_NUMBER}
EXPOSE 80
CMD make main