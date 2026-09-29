# استخدام بيئة لينكس خفيفة
FROM debian:bookworm-slim

# تثبيت الأدوات الأساسية
RUN apt-get update && apt-get install -y curl git ca-certificates python3 python3-pip

# تحديد مجلد العمل
WORKDIR /app

# نسخ جميع ملفات بوت التداول الخاصة بك من المستودع إلى داخل الخادم
COPY . /app

# تحميل الوكيل OpenCrabs (تأكد من وضع الرابط الصحيح لأحدث نسخة لينكس)
RUN curl -L -o opencrabs "https://github.com/usier/opencrabs/releases/latest/download/opencrabs-linux-amd64"

# إعطاء صلاحية التشغيل
RUN chmod +x opencrabs

# فتح المنفذ للاتصال
EXPOSE 10000

# تشغيل الوكيل كخدمة خلفية
CMD ["./opencrabs", "daemon", "--host", "0.0.0.0", "--port", "10000"]
