# L0096 — عمق الهبوط واسترداد السعر على SOL

1.12حالة CCI7/عمقهبوط/استردادسعر،4h،ثلاثفترات2025.
2.المال:not measured.
3.12صفًا و36تقييممقطع؛العينةتنبيهاتوأحداث.
4.الربحيةوالتكاليف:not measured.
5.فترةعمياء:not measured.
6.الاحتفاظ:not measured.
7.Defer adoption؛مقارنةتطويرفقط.
8.التالي:مراجعةالقائد،لاتوسعةتلقائية.

## 1.الهوية
|البند|القيمة|
|---|---|
|العملة|SOLUSDT|
|الإطار|4hUTC|
|الفترات|يناير–مارس؛5أبريل–30يونيو؛5يوليو–30سبتمبر2025|
|المصدر|source.json,parent93.json.gz,SOLUSDT.csv|
|الفرق|عمقهبوط18شمعةسابقة≥2/3/4ATR،واسترداد0/0.25ATRمعشمعةصاعدة|

## 2.المال
|المقياس|الحالة|
|---|---|
|الأرباح/التكاليف/الصفقات/الخروج|not measured — outside this phase|

## 3.الإشارات
|الحالة|تنبيهات|ملتقط/أحداث|الدقة|الاسترجاع|الأهلية|
|---|---|---|---|---|---|
|CCI_ONLY|128|32/36|25.00%|88.89%|True|
|CCI_DEPTH_2|106|29/36|27.36%|80.56%|True|
|CCI_DEPTH_3|68|21/36|30.88%|58.33%|True|
|CCI_DEPTH_4|38|16/36|42.11%|44.44%|True|
|CCI_RECOVERY_0|103|27/36|26.21%|75.00%|True|
|CCI_RECOVERY_0.25|77|21/36|27.27%|58.33%|True|
|CCI_DEPTH_2_RECOVERY_0|86|24/36|27.91%|66.67%|True|
|CCI_DEPTH_2_RECOVERY_0.25|64|19/36|29.69%|52.78%|True|
|CCI_DEPTH_3_RECOVERY_0|59|20/36|33.90%|55.56%|True|
|CCI_DEPTH_3_RECOVERY_0.25|46|16/36|34.78%|44.44%|True|
|CCI_DEPTH_4_RECOVERY_0|32|15/36|46.88%|41.67%|True|
|CCI_DEPTH_4_RECOVERY_0.25|27|12/36|44.44%|33.33%|True|

## 4.العينةوالتوقيت
|الحالة|Wilson95وصفي|وسيطالتأخير|
|---|---|---|
|CCI_ONLY|[0.18301284861358558, 0.33155562952316864]|1.0|
|CCI_DEPTH_2|[0.19775928868996975, 0.365247243494244]|1|
|CCI_DEPTH_3|[0.21172386467551985, 0.42636811693509546]|1|
|CCI_DEPTH_4|[0.27852501157758713, 0.5780765465632945]|1.0|
|CCI_RECOVERY_0|[0.1868578650291558, 0.3545186704388419]|1|
|CCI_RECOVERY_0.25|[0.18584490792429903, 0.38120892174953463]|1|
|CCI_DEPTH_2_RECOVERY_0|[0.1952867777055854, 0.3817459141183472]|1.0|
|CCI_DEPTH_2_RECOVERY_0.25|[0.19905151325539794, 0.41770201103542925]|1|
|CCI_DEPTH_3_RECOVERY_0|[0.23137653685587656, 0.46627529433071635]|1.0|
|CCI_DEPTH_3_RECOVERY_0.25|[0.22680993370754338, 0.49229941157937235]|1.0|
|CCI_DEPTH_4_RECOVERY_0|[0.30869387108068835, 0.6355048288102536]|1|
|CCI_DEPTH_4_RECOVERY_0.25|[0.27585858177023004, 0.6268697548677552]|1.0|

## 5.الثبات
|الحالة|المقطع|NS|P|R|
|---|---|---|---|---|
|CCI_ONLY|1|45|22.22%|83.33%|
|CCI_ONLY|2|46|23.91%|91.67%|
|CCI_ONLY|3|37|29.73%|91.67%|
|CCI_DEPTH_2|1|39|23.08%|75.00%|
|CCI_DEPTH_2|2|36|30.56%|91.67%|
|CCI_DEPTH_2|3|31|29.03%|75.00%|
|CCI_DEPTH_3|1|25|32.00%|66.67%|
|CCI_DEPTH_3|2|21|33.33%|58.33%|
|CCI_DEPTH_3|3|22|27.27%|50.00%|
|CCI_DEPTH_4|1|16|31.25%|41.67%|
|CCI_DEPTH_4|2|11|54.55%|50.00%|
|CCI_DEPTH_4|3|11|45.45%|41.67%|
|CCI_RECOVERY_0|1|35|22.86%|66.67%|
|CCI_RECOVERY_0|2|36|27.78%|83.33%|
|CCI_RECOVERY_0|3|32|28.12%|75.00%|
|CCI_RECOVERY_0.25|1|25|20.00%|41.67%|
|CCI_RECOVERY_0.25|2|28|28.57%|66.67%|
|CCI_RECOVERY_0.25|3|24|33.33%|66.67%|
|CCI_DEPTH_2_RECOVERY_0|1|30|23.33%|58.33%|
|CCI_DEPTH_2_RECOVERY_0|2|29|34.48%|83.33%|
|CCI_DEPTH_2_RECOVERY_0|3|27|25.93%|58.33%|
|CCI_DEPTH_2_RECOVERY_0.25|1|22|22.73%|41.67%|
|CCI_DEPTH_2_RECOVERY_0.25|2|21|38.10%|66.67%|
|CCI_DEPTH_2_RECOVERY_0.25|3|21|28.57%|50.00%|
|CCI_DEPTH_3_RECOVERY_0|1|20|35.00%|58.33%|
|CCI_DEPTH_3_RECOVERY_0|2|19|36.84%|58.33%|
|CCI_DEPTH_3_RECOVERY_0|3|20|30.00%|50.00%|
|CCI_DEPTH_3_RECOVERY_0.25|1|15|33.33%|41.67%|
|CCI_DEPTH_3_RECOVERY_0.25|2|14|35.71%|41.67%|
|CCI_DEPTH_3_RECOVERY_0.25|3|17|35.29%|50.00%|
|CCI_DEPTH_4_RECOVERY_0|1|12|33.33%|33.33%|
|CCI_DEPTH_4_RECOVERY_0|2|11|54.55%|50.00%|
|CCI_DEPTH_4_RECOVERY_0|3|9|55.56%|41.67%|
|CCI_DEPTH_4_RECOVERY_0.25|1|9|33.33%|25.00%|
|CCI_DEPTH_4_RECOVERY_0.25|2|9|44.44%|33.33%|
|CCI_DEPTH_4_RECOVERY_0.25|3|9|55.56%|41.67%|

## 6.القيمةفوقCCI
|الحالة|أحداثمضافة|أحداثمفقودة|اجتياز+5نقاط/احتفاظ80%R|
|---|---|---|---|
|CCI_ONLY|0|0|False|
|CCI_DEPTH_2|0|3|False|
|CCI_DEPTH_3|0|11|False|
|CCI_DEPTH_4|0|16|False|
|CCI_RECOVERY_0|0|5|False|
|CCI_RECOVERY_0.25|0|11|False|
|CCI_DEPTH_2_RECOVERY_0|0|8|False|
|CCI_DEPTH_2_RECOVERY_0.25|0|13|False|
|CCI_DEPTH_3_RECOVERY_0|0|12|False|
|CCI_DEPTH_3_RECOVERY_0.25|0|16|False|
|CCI_DEPTH_4_RECOVERY_0|0|17|False|
|CCI_DEPTH_4_RECOVERY_0.25|0|20|False|

## 7.الجودة
|الحالة|P70/R30/NS20/Wilsonlow60/lag≤1/ثبات|اجتيازالجودةوالإضافة|
|---|---|---|
|CCI_ONLY|False|False|
|CCI_DEPTH_2|False|False|
|CCI_DEPTH_3|False|False|
|CCI_DEPTH_4|False|False|
|CCI_RECOVERY_0|False|False|
|CCI_RECOVERY_0.25|False|False|
|CCI_DEPTH_2_RECOVERY_0|False|False|
|CCI_DEPTH_2_RECOVERY_0.25|False|False|
|CCI_DEPTH_3_RECOVERY_0|False|False|
|CCI_DEPTH_3_RECOVERY_0.25|False|False|
|CCI_DEPTH_4_RECOVERY_0|False|False|
|CCI_DEPTH_4_RECOVERY_0.25|False|False|

البياناتتطويرتاريخيمكشوف؛لا تحققأعمىأودلالةمصححة. Wilsonوصفيباستقلالالتنبيهات. لااختياربعديفترةأوعتبةأفضلأواعتماد. raw.json.gzوأقنعةكلحالةوتسمياتالأحداثوالتوقيتتكفيلإعادةالحساب؛alerts.jsonيسجلجميعالتنبيهاتبمافيهاالكاذبة. لااختبارعتبةعمقأواستردادخارجالشبكة.
إعادةالتشغيل:python launch95.py --fixture-onlyللاصطناعيأوpython launch95.py --out runللمهمةالمسجلة؛المصدرثابت.
