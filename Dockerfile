FROM ubuntu:24.04

# تحديث النظام وتثبيت بيئة بايثون وأداة فك الضغط
RUN apt-get update && apt-get install -y ca-certificates python3 python3-pip unzip

# تثبيت الموزع الذكي LiteLLM
RUN pip3 install litellm --break-system-packages

WORKDIR /app
COPY . /app

# إنشاء مجلد البيانات وإعطاء صلاحيات واسعة للوكيل والسكربت
RUN mkdir -p /app/.opencrabs && chmod -R 777 /app
RUN unzip -o opencrabs.zip && chmod +x opencrabs start.sh

EXPOSE 10000 4000

# تشغيل السكربت المزدوج
CMD ["./start.sh"]
