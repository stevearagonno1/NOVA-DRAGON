FROM debian:bookworm-slim

# تثبيت بيئة بايثون وأداة فك الضغط
RUN apt-get update && apt-get install -y ca-certificates python3 python3-pip unzip

# تثبيت الموزع الذكي LiteLLM
RUN pip3 install litellm --break-system-packages

WORKDIR /app
COPY . /app

# فك ضغط الوكيل وإعطاء صلاحيات التشغيل للوكيل والسكربت
RUN unzip -o opencrabs.zip && chmod +x opencrabs start.sh

EXPOSE 10000 4000

# تشغيل السكربت المزدوج بدلاً من الوكيل وحده
CMD ["./start.sh"]
