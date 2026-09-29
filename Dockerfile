# المرحلة الأولى: بناء الوكيل من المصدر باستخدام بيئة Rust الرسمية
FROM rust:latest AS builder
RUN apt-get update && apt-get install -y git
RUN git clone https://github.com/usier/opencrabs.git /app/src
WORKDIR /app/src
RUN cargo build --release

# المرحلة النهائية: تجهيز خادم التشغيل الخفيف
FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y git ca-certificates python3 python3-pip

WORKDIR /app

# نقل الملف التنفيذي المبني من المرحلة السابقة
COPY --from=builder /app/src/target/release/opencrabs /app/opencrabs

# نسخ ملفات بوت التداول الخاصة بك
COPY . /app

# إعطاء صلاحية التشغيل
RUN chmod +x opencrabs

# فتح المنفذ للاتصال
EXPOSE 10000

# تشغيل الوكيل كخدمة خلفية
CMD ["./opencrabs", "daemon", "--host", "0.0.0.0", "--port", "10000"]

