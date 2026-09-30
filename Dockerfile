FROM ubuntu:24.04

# تحديث النظام وتثبيت بيئة بايثون وأداة فك الضغط
RUN apt-get update && apt-get install -y ca-certificates python3 python3-pip unzip

# تثبيت الموزع الذكي مع حزمة البروكسي الإجبارية لتشغيل ملفات الإعدادات
RUN pip3 install 'litellm[proxy]' --break-system-packages

WORKDIR /app
COPY . /app

# تجهيز مجلد الوكيل وصلاحياته
RUN mkdir -p /app/.opencrabs && chmod -R 777 /app
RUN unzip -o opencrabs.zip && chmod +x opencrabs start.sh

EXPOSE 10000 4000

# تشغيل سكربت البدء المزدوج
CMD ["./start.sh"]
