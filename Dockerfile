FROM debian:bookworm-slim
# إضافة أداة unzip لفك الضغط
RUN apt-get update && apt-get install -y ca-certificates python3 python3-pip unzip
WORKDIR /app
COPY . /app
# فك الضغط عن الملف وإعطاؤه صلاحية التشغيل
RUN unzip -o opencrabs.zip && chmod +x opencrabs
EXPOSE 10000
CMD ["./opencrabs", "daemon", "--host", "0.0.0.0", "--port", "10000"]
