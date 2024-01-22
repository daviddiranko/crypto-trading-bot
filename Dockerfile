FROM amazon/aws-cli

ARG BUILD_NUMBER
ARG SECRET_KEY
ARG ACCESS_KEY
ARG REGION

# Set AWS credentials (replace these with your actual AWS credentials)
ENV AWS_ACCESS_KEY_ID=ACCESS_KEY
ENV AWS_SECRET_ACCESS_KEY=SECRET_KEY
ENV AWS_DEFAULT_REGION=REGION

# Run `aws configure` to set up the configuration with the provided credentials
RUN aws configure set aws_access_key_id $AWS_ACCESS_KEY_ID
RUN aws configure set aws_secret_access_key $AWS_SECRET_ACCESS_KEY
RUN aws configure set default.region $AWS_DEFAULT_REGION

FROM python:3.9-slim

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