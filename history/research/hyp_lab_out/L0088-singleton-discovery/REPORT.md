# L0088 — اكتشاف إشارات منفردة لكل عملة

1. شبكة36 إعدادًا،9 عائلات،BTC/ETH/SOL،4h،ثلاث فترات تطوير2025.
2. المال والتكاليف: not measured.
3. صفقات: not measured؛تنبيهات وأحداث فقط.
4. معامل الربح: not measured.
5. تحقق مستقل أو أعمى: not measured؛كل الفترات سبق الاطلاع عليها.
6. مقابل الاحتفاظ: not measured؛خطوط التنبيه في baselines.json.
7. القرار: Defer الاعتماد؛هذه نتائج اكتشاف فقط.
8. التالي: مراجعة مستقلة ثم تجهيز مرحلة واحدة تالية.

## 1. هوية التجربة
| الحقل | القيمة |
|---|---|
| الحالات / تقييمات العملات والفترات |36 / 324 |
|نوع البيانات|شموع العقود التاريخيةUSDT-M؛ليست دفتر أوامر|

## 2. المال
| الحقل | الحالة |
|---|---|
|الربح/التوقع/الرسوم/معامل الربح|not measured|

## 3. الإشارات المشتركة — جميع الحالات دون إسقاط
|الإشارة|تنبيهات|ملتقط / أحداث|الدقة|الاسترجاع|أضعف دقة فترة|الجودة|
|---|---:|---:|---:|---:|---:|---|
|BB_10_2|401|82/106|20.45%|77.36%|15.57%|TARGET_NOT_MET|
|BB_10_2.5|239|58/106|24.27%|54.72%|19.40%|TARGET_NOT_MET|
|BB_20_2|228|58/106|25.44%|54.72%|19.05%|TARGET_NOT_MET|
|BB_20_2.5|141|49/106|34.75%|46.23%|22.50%|TARGET_NOT_MET|
|BB_30_2|183|52/106|28.42%|49.06%|25.00%|TARGET_NOT_MET|
|BB_30_2.5|104|35/106|33.65%|33.02%|19.05%|TARGET_NOT_MET|
|CCI_10_-150|179|65/106|36.31%|61.32%|30.43%|TARGET_NOT_MET|
|CCI_10_-100|300|83/106|27.67%|78.30%|25.24%|TARGET_NOT_MET|
|CCI_14_-150|146|57/106|39.04%|53.77%|32.56%|TARGET_NOT_MET|
|CCI_14_-100|243|64/106|26.34%|60.38%|24.36%|TARGET_NOT_MET|
|CCI_21_-150|114|46/106|40.35%|43.40%|31.43%|TARGET_NOT_MET|
|CCI_21_-100|187|41/106|21.93%|38.68%|20.34%|TARGET_NOT_MET|
|EMA_RECLAIM_10|413|47/106|11.38%|44.34%|8.66%|TARGET_NOT_MET|
|EMA_RECLAIM_20|310|33/106|10.65%|31.13%|9.80%|TARGET_NOT_MET|
|EMA_RECLAIM_30|249|28/106|11.24%|26.42%|8.70%|TARGET_NOT_MET|
|DONCHIAN_RECLAIM_10|262|54/106|20.61%|50.94%|15.91%|TARGET_NOT_MET|
|DONCHIAN_RECLAIM_20|157|46/106|29.30%|43.40%|25.86%|TARGET_NOT_MET|
|DONCHIAN_RECLAIM_40|94|31/106|32.98%|29.25%|20.59%|INSUFFICIENT_SAMPLE|
|OBV_EMA_5_20|134|7/106|5.22%|6.60%|0.00%|TARGET_NOT_MET|
|OBV_EMA_10_30|70|3/106|4.29%|2.83%|0.00%|INSUFFICIENT_SAMPLE|
|OBV_EMA_20_50|39|1/106|2.56%|0.94%|0.00%|INSUFFICIENT_SAMPLE|
|TAKER_PRESSURE_1_0.52|549|45/106|8.20%|42.45%|5.73%|TARGET_NOT_MET|
|TAKER_PRESSURE_1_0.56|44|3/106|6.82%|2.83%|0.00%|INSUFFICIENT_SAMPLE|
|TAKER_PRESSURE_3_0.52|108|5/106|4.63%|4.72%|0.00%|INSUFFICIENT_SAMPLE|
|TAKER_PRESSURE_3_0.56|1|0/106|0.00%|0.00%|0.00%|INSUFFICIENT_SAMPLE|
|TAKER_PRESSURE_6_0.52|35|0/106|0.00%|0.00%|0.00%|INSUFFICIENT_SAMPLE|
|TAKER_PRESSURE_6_0.56|0|0/106|0.00%|0.00%|0.00%|INSUFFICIENT_SAMPLE|
|SQUEEZE_BREAK_20|6|0/106|0.00%|0.00%|0.00%|INSUFFICIENT_SAMPLE|
|SQUEEZE_BREAK_30|9|0/106|0.00%|0.00%|0.00%|INSUFFICIENT_SAMPLE|
|RSI_RECLAIM_10_30|92|34/106|36.96%|32.08%|29.27%|INSUFFICIENT_SAMPLE|
|RSI_RECLAIM_10_40|240|50/106|20.83%|47.17%|18.57%|TARGET_NOT_MET|
|RSI_RECLAIM_14_30|71|26/106|36.62%|24.53%|26.32%|INSUFFICIENT_SAMPLE|
|RSI_RECLAIM_14_40|161|32/106|19.88%|30.19%|13.73%|TARGET_NOT_MET|
|RSI_RECLAIM_21_30|34|17/106|50.00%|16.04%|35.71%|INSUFFICIENT_SAMPLE|
|RSI_RECLAIM_21_40|98|19/106|19.39%|17.92%|14.29%|INSUFFICIENT_SAMPLE|
|MACD_REFERENCE_12_26_9|171|7/106|4.09%|6.60%|2.00%|TARGET_NOT_MET|

## 4. الحركة والمخاطر
|القياس|المصدر|
|---|---|
|lag/MAE/MFE لكل تنبيه|alerts.json؛بوحدةATR دون تنفيذ مالي|
|السحب/الخسارة المالية|not measured|

## 5. الفترات والثبات
|العملة|أحداث الفترات الثلاث|
|---|---|
|BTCUSDT|[13, 13, 11]|
|ETHUSDT|[11, 12, 10]|
|SOLUSDT|[12, 12, 12]|

تفاصيل324 تقييمًا،والحالات الصفرية،فيresults.json. الاختيار يرتب أدنى دقة فترة قبل حدWilson الوصفي والاسترجاع؛لا نختار قمة فترة منفردة.

## 6. المقارنات وخيارات التطوير
|العملة|مرشحو العائلات المؤهلون|
|---|---|
|BTCUSDT|BB:BB_30_2.5، CCI:CCI_14_-150، DONCHIAN_RECLAIM:DONCHIAN_RECLAIM_20، EMA_RECLAIM:EMA_RECLAIM_10، MACD_REFERENCE:None، OBV_EMA:None، RSI_RECLAIM:RSI_RECLAIM_10_40، SQUEEZE_BREAK:None، TAKER_PRESSURE:TAKER_PRESSURE_1_0.52|
|ETHUSDT|BB:BB_20_2.5، CCI:CCI_14_-150، DONCHIAN_RECLAIM:DONCHIAN_RECLAIM_40، EMA_RECLAIM:EMA_RECLAIM_20، MACD_REFERENCE:None، OBV_EMA:None، RSI_RECLAIM:RSI_RECLAIM_10_30، SQUEEZE_BREAK:None، TAKER_PRESSURE:TAKER_PRESSURE_1_0.52|
|SOLUSDT|BB:BB_20_2، CCI:CCI_21_-150، DONCHIAN_RECLAIM:DONCHIAN_RECLAIM_20، EMA_RECLAIM:EMA_RECLAIM_10، MACD_REFERENCE:None، OBV_EMA:None، RSI_RECLAIM:RSI_RECLAIM_10_30، SQUEEZE_BREAK:None، TAKER_PRESSURE:None|

NONE/EVERY_BAR/EVERY_5_BARS محفوظة بكل أصل وفترة فيbaselines.json. المرشح العائلي يجهز بحثًا لاحقًا؛ليس تحققًا للتخصيص أو اعتمادًا.

## 7. شروط الجودة والحدود
|الشرط|الحالة|
|---|---|
|الهدف|دقة70%،استرجاع30%،عينة100/20 لكلعملة،دقةعملة55%،Wilson60%،وسيطlag≤1|
|دلالة مصححة وتحقق مستقل|not measured؛لاp-value أو دعوى تفوق استدلالية من اكتشاف|
|نتيجة إيجابية|DISCOVERY_TARGET_ONLY إن تحققت؛لاAdopt|

## المصطلحات
|المصطلح|المعنى|
|---|---|
|Precision|ملتقط/تنبيهات|
|Recall|ملتقط/كل أحداث الصعود|
|Wilson|حدوصفي يفترض استقلالًا؛لايصحح الاختيار|

## أسماء العائلات
|العائلة|المعنى|
|---|---|
|OBV|حجم تراكمي موقّع باتجاه الإغلاق؛ليس تدفق أوامر فعليًا|
|TAKER_PRESSURE|نسبة حجم شراءtaker المجمع،دون إعادة بناء دفترالأوامر|
|SQUEEZE_BREAK|ضغط نطاق ثم اختراق خلالمهلةسببية|

أمر الأرقام: python3 tools/l0088/research88.py --inputs tools/l0087 --out MARKET_DIR. تفاصيل التعريفات والتسجيل فيdocs/lanes/L0088-SINGLETON-DISCOVERY.md.
