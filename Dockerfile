FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y ca-certificates python3 python3-pip
WORKDIR /app
COPY . /app
RUN chmod +x opencrabs
EXPOSE 10000
CMD ["./opencrabs", "daemon", "--host", "0.0.0.0", "--port", "10000"]

