# تدقيق جاهزية الحزمة الشاملة

**الحالة: لم تكتمل جاهزية اختبار الجميع. لا تُرسل هذه الأدلة كأنها ورقة تنفيذ سوق جاهزة.**

هذا تحديث داخل المهمة الموحدة، وليس مهمة منفصلة للمنفذ. لم ينفذ اختبار دقة دخول أو تجربة سوق في هذا التحضير.

| الفحص | النتيجة |
|---|---|
| مطابقة بايتات مصادر المكتبة | 129/129 |
| محاولات التشغيل الافتراضي الاصطناعي | 492 = 123 كودًا × 4 فريمات |
| اكتمل التشغيل الاصطناعي فقط | 284 |
| توقف بخطأ تشغيل | 199 |
| تجاوز مهلة الجاهزية 10 ثوانٍ | 9 |
| إعدادات مستخرجة ومعرّفة منفردة | 5940 خانة؛ ليست 5940 نسخة تنفيذ |
| مراجعة مستقلة أولية للمحرك | 300 موضع EMA20 و300 موضع RSI14، تطابق في القيم وتهيئة الغياب؛ لا تعمم على غيرهما |
| قيم موثقة أضيفت من الأوراق القديمة | 76 سجلًا من L0083 و38 من L0079؛ مسودات تُراجع ولا تجمع كنسخ جديدة مستقلة تلقائيًا |
| وثائق PDF/DOCX | 18 ملفًا استخرج نصها؛ المراجعة الدلالية غير مكتملة |

## ما يمنع التسليم الجاهز

بعض توقفات الفحص ناتجة عن محرك PineTS أو قصر التاريخ الاصطناعي للفريمات الأعلى، وبعضها طلب بيانات خارجية غير موردة أو صياغة مصدر تحتاج إصلاحًا. لا تعني أن المؤشر لا يصلح للصعود. إتمام تشغيل افتراضي لا يثبت صحة الإشارات أو السببية أو تشغيل نسخ الإعدادات.

ما زالت مجالات إعدادات الدخول المفتوحة ومجموعاتها تحتاج قفلًا دلاليًا؛ لا يجوز تحويل الألوان والمخارج إلى تجارب دخول، أو تسمية خيارات إعداد محدودة جميع الأرقام الممكنة. يلزم التحقق من كل نسخة ومن التوقيت الفعلي للإشارة قبل حساب السوق.

النطاق يبقى جميع المصادر ونسخ الدخول والتأكيدات على BTC وفريمات1 و5 و15 و60، داخل حزمة واحدة. لم يسقط مصدر متوقف، ولم تُرسل عملية إصلاح إلى المنفذ، ولم يعدل التشغيل الجاري أو البيانات أو main.

## كل توقف على حدة

| المصدر | الفريم | السبب الفعلي |
|---|---|---|
| 2-1 strategy.txt | 1 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 61:7 |
| 2-1 strategy.txt | 5 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 61:7 |
| 2-1 strategy.txt | 15 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 61:7 |
| 2-1 strategy.txt | 60 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 61:7 |
| ABO LANA-𝑀.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| ABO LANA-𝑀.txt | 5 | Cannot read properties of undefined (reading '0') |
| ABO LANA-𝑀.txt | 15 | Cannot read properties of undefined (reading '2') |
| ABO LANA-𝑀.txt | 60 | READINESS_TIMEOUT_10S |
| AI Gold Scalping.txt | 1 | Timeframe 3 is not lower than or equal to chart timeframe 1 |
| AI Gold Scalping.txt | 5 | Timeframe 15 is not lower than or equal to chart timeframe 5 |
| AI Gold Scalping.txt | 15 | Timeframe 30 is not lower than or equal to chart timeframe 15 |
| AI Gold Scalping.txt | 60 | Timeframe 120 is not lower than or equal to chart timeframe 60 |
| AI RSI MTF STRATEGY.txt | 15 | Cannot read properties of null (reading 'delete') |
| AI RSI MTF STRATEGY.txt | 60 | Cannot read properties of null (reading 'delete') |
| ALGOX V11.txt | 1 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 753:7 |
| ALGOX V11.txt | 5 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 753:7 |
| ALGOX V11.txt | 15 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 753:7 |
| ALGOX V11.txt | 60 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 753:7 |
| ASK.txt | 1 | Cannot read properties of undefined (reading '0') |
| ASK.txt | 5 | Cannot read properties of undefined (reading '0') |
| ASK.txt | 15 | Cannot read properties of undefined (reading '4') |
| ASK.txt | 60 | READINESS_TIMEOUT_10S |
| Advanced SMC.txt | 1 | UNSUPPLIED_SYMBOL: ES1! |
| Advanced SMC.txt | 5 | UNSUPPLIED_SYMBOL: ES1! |
| Advanced SMC.txt | 15 | UNSUPPLIED_SYMBOL: ES1! |
| Advanced SMC.txt | 60 | UNSUPPLIED_SYMBOL: ES1! |
| AlgoX V22 SuperTrend.txt | 1 | e is not a function |
| AlgoX V22 SuperTrend.txt | 5 | e is not a function |
| AlgoX V22 SuperTrend.txt | 15 | e is not a function |
| AlgoX V22 SuperTrend.txt | 60 | e is not a function |
| Alpha Hunter.txt | 15 | Index 0 is out of bounds, array size is 0. |
| Alpha Hunter.txt | 60 | Index 0 is out of bounds, array size is 0. |
| Clustering Clouds v2.txt | 1 | Cannot read properties of undefined (reading '0') |
| Clustering Clouds v2.txt | 5 | Cannot read properties of undefined (reading '0') |
| Clustering Clouds v2.txt | 15 | Cannot read properties of undefined (reading '4') |
| Clustering Clouds v2.txt | 60 | READINESS_TIMEOUT_10S |
| Combined Algo v5.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: 1D |
| DTC V1.35.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: 1D |
| DTC.txt | 1 | Undeclared identifier "timestamp" |
| DTC.txt | 5 | Undeclared identifier "timestamp" |
| DTC.txt | 15 | Undeclared identifier "timestamp" |
| DTC.txt | 60 | Undeclared identifier "timestamp" |
| Drone Arrows.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: 1D |
| Drone Arrows.txt | 5 | Cannot read properties of undefined (reading '0') |
| Drone Arrows.txt | 15 | Cannot read properties of undefined (reading '2') |
| Drone Arrows.txt | 60 | Cannot read properties of undefined (reading '11') |
| ELITE SMART.txt | 1 | Cannot read properties of undefined (reading '0') |
| ELITE SMART.txt | 5 | Cannot read properties of undefined (reading '0') |
| ELITE SMART.txt | 15 | Cannot read properties of undefined (reading '4') |
| ELITE SMART.txt | 60 | READINESS_TIMEOUT_10S |
| Edge Algo pro.txt | 1 | Failed to transpile Pine Script version 6: Unexpected character '﻿' at 1:1 |
| Edge Algo pro.txt | 5 | Failed to transpile Pine Script version 6: Unexpected character '﻿' at 1:1 |
| Edge Algo pro.txt | 15 | Failed to transpile Pine Script version 6: Unexpected character '﻿' at 1:1 |
| Edge Algo pro.txt | 60 | Failed to transpile Pine Script version 6: Unexpected character '﻿' at 1:1 |
| ExProfit SuperTrend.txt | 1 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 420:18 |
| ExProfit SuperTrend.txt | 5 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 420:18 |
| ExProfit SuperTrend.txt | 15 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 420:18 |
| ExProfit SuperTrend.txt | 60 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 420:18 |
| Eyops Fx Premium.txt | 1 | Failed to transpile Pine Script version 5: Unexpected token RPAREN ')' at 208:71 |
| Eyops Fx Premium.txt | 5 | Failed to transpile Pine Script version 5: Unexpected token RPAREN ')' at 208:71 |
| Eyops Fx Premium.txt | 15 | Failed to transpile Pine Script version 5: Unexpected token RPAREN ')' at 208:71 |
| Eyops Fx Premium.txt | 60 | Failed to transpile Pine Script version 5: Unexpected token RPAREN ')' at 208:71 |
| Fibonacci.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| FLI.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| FLI.txt | 5 | Invalid session specification: "extended" |
| FLI.txt | 15 | Invalid session specification: "extended" |
| FLI.txt | 60 | Invalid session specification: "extended" |
| FVG+Fractals.txt | 1 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 3:7 |
| FVG+Fractals.txt | 5 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 3:7 |
| FVG+Fractals.txt | 15 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 3:7 |
| FVG+Fractals.txt | 60 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 3:7 |
| Fresh Algo (1).txt | 1 | Cannot read properties of undefined (reading '0') |
| Fresh Algo (1).txt | 5 | Cannot read properties of undefined (reading '0') |
| Fresh Algo (1).txt | 15 | Cannot read properties of undefined (reading '0') |
| Fresh Algo (1).txt | 60 | Cannot read properties of undefined (reading '3') |
| Fresh Algo.txt | 1 | Cannot read properties of undefined (reading '0') |
| Fresh Algo.txt | 5 | Cannot read properties of undefined (reading '0') |
| Fresh Algo.txt | 15 | Cannot read properties of undefined (reading '0') |
| Fresh Algo.txt | 60 | Cannot read properties of undefined (reading '3') |
| HADYAN NEW SCALPING V 2.9.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| HalfTrend.txt | 1 | UNSUPPLIED_SYMBOL: BTCUSD |
| HalfTrend.txt | 5 | UNSUPPLIED_SYMBOL: BTCUSD |
| HalfTrend.txt | 15 | UNSUPPLIED_SYMBOL: BTCUSD |
| HalfTrend.txt | 60 | UNSUPPLIED_SYMBOL: BTCUSD |
| Haper Trend.txt | 1 | Cannot read properties of undefined (reading '0') |
| Haper Trend.txt | 5 | Cannot read properties of undefined (reading '0') |
| Haper Trend.txt | 15 | Cannot read properties of undefined (reading '4') |
| Haper Trend.txt | 60 | READINESS_TIMEOUT_10S |
| ICT Validated SMC v1.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| ICT Validated SMC v1.txt | 5 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: W |
| ICT Validated SMC v1.txt | 15 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: W |
| Indicator ICT Master Suite.txt | 1 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 7:7 |
| Indicator ICT Master Suite.txt | 5 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 7:7 |
| Indicator ICT Master Suite.txt | 15 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 7:7 |
| Indicator ICT Master Suite.txt | 60 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 7:7 |
| Infinity and Sniper by Leo.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| Infinity and Sniper by Leo.txt | 5 | Cannot read properties of undefined (reading '0') |
| Infinity and Sniper by Leo.txt | 15 | Cannot read properties of undefined (reading '0') |
| Infinity and Sniper by Leo.txt | 60 | Cannot read properties of undefined (reading '0') |
| Institutional Flow Toolkit MMDV.txt | 1 | UNSUPPLIED_SYMBOL: BANKNIFTY |
| Institutional Flow Toolkit MMDV.txt | 5 | UNSUPPLIED_SYMBOL: BANKNIFTY |
| Institutional Flow Toolkit MMDV.txt | 15 | UNSUPPLIED_SYMBOL: BANKNIFTY |
| Institutional Flow Toolkit MMDV.txt | 60 | UNSUPPLIED_SYMBOL: BANKNIFTY |
| floop pro.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| floop pro.txt | 60 | READINESS_TIMEOUT_10S |
| Jackson_Zones.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| Joker.txt | 1 | Cannot read properties of undefined (reading '0') |
| Joker.txt | 5 | Cannot read properties of undefined (reading '0') |
| Joker.txt | 15 | Cannot read properties of undefined (reading '4') |
| Joker.txt | 60 | READINESS_TIMEOUT_10S |
| KD System.txt | 1 | Failed to transpile Pine Script version 6: Unexpected token KEYWORD 'import' at 11:7 |
| KD System.txt | 5 | Failed to transpile Pine Script version 6: Unexpected token KEYWORD 'import' at 11:7 |
| KD System.txt | 15 | Failed to transpile Pine Script version 6: Unexpected token KEYWORD 'import' at 11:7 |
| KD System.txt | 60 | Failed to transpile Pine Script version 6: Unexpected token KEYWORD 'import' at 11:7 |
| Key Levels.txt | 1 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 7:7 |
| Key Levels.txt | 5 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 7:7 |
| Key Levels.txt | 15 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 7:7 |
| Key Levels.txt | 60 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 7:7 |
| Luxy BIG beautiful Dynamic.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| LyroRS v1.txt | 1 | Failed to transpile Pine Script version 6: Unexpected token KEYWORD 'import' at 7:7 |
| LyroRS v1.txt | 5 | Failed to transpile Pine Script version 6: Unexpected token KEYWORD 'import' at 7:7 |
| LyroRS v1.txt | 15 | Failed to transpile Pine Script version 6: Unexpected token KEYWORD 'import' at 7:7 |
| LyroRS v1.txt | 60 | Failed to transpile Pine Script version 6: Unexpected token KEYWORD 'import' at 7:7 |
| MELONA.txt | 1 | Undeclared identifier "bgcolor" |
| MELONA.txt | 5 | Undeclared identifier "bgcolor" |
| MELONA.txt | 15 | Undeclared identifier "bgcolor" |
| MELONA.txt | 60 | Undeclared identifier "bgcolor" |
| MONEY ALGORITHM.txt | 1 | Cannot read properties of undefined (reading '0') |
| MONEY ALGORITHM.txt | 5 | Cannot read properties of undefined (reading '0') |
| MONEY ALGORITHM.txt | 15 | Cannot read properties of undefined (reading '4') |
| MONEY ALGORITHM.txt | 60 | READINESS_TIMEOUT_10S |
| Market Matrice.txt | 1 | Failed to transpile Pine Script version 6: Unexpected character '©' at 1:3 |
| Market Matrice.txt | 5 | Failed to transpile Pine Script version 6: Unexpected character '©' at 1:3 |
| Market Matrice.txt | 15 | Failed to transpile Pine Script version 6: Unexpected character '©' at 1:3 |
| Market Matrice.txt | 60 | Failed to transpile Pine Script version 6: Unexpected character '©' at 1:3 |
| Million Moves Alga.txt | 1 | Cannot read properties of undefined (reading '0') |
| Million Moves Alga.txt | 5 | Cannot read properties of undefined (reading '0') |
| Million Moves Alga.txt | 15 | Cannot read properties of undefined (reading '4') |
| Million Moves Alga.txt | 60 | Cannot read properties of undefined (reading '19') |
| NAS Ultimate Algo Remastered.txt | 1 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 281:7 |
| NAS Ultimate Algo Remastered.txt | 5 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 281:7 |
| NAS Ultimate Algo Remastered.txt | 15 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 281:7 |
| NAS Ultimate Algo Remastered.txt | 60 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 281:7 |
| NOSTRADAMUS.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: W |
| NOSTRADAMUS.txt | 5 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: W |
| NOSTRADAMUS.txt | 15 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: W |
| NOSTRADAMUS.txt | 60 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: M |
| River Strategy.txt | 1 | Cannot read properties of undefined (reading '0') |
| River Strategy.txt | 5 | Cannot read properties of undefined (reading '0') |
| River Strategy.txt | 15 | Cannot read properties of undefined (reading '0') |
| River Strategy.txt | 60 | READINESS_TIMEOUT_10S |
| SMC Algo Pro.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| SMC Algo Pro.txt | 5 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: W |
| SMC Algo Pro.txt | 15 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: W |
| SMC Algo Pro.txt | 60 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: M |
| SMC.txt | 1 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 2187:7 |
| SMC.txt | 5 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 2187:7 |
| SMC.txt | 15 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 2187:7 |
| SMC.txt | 60 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 2187:7 |
| SUPER Scalping.txt | 1 | dynamic computed member access is not allowed |
| SUPER Scalping.txt | 5 | dynamic computed member access is not allowed |
| SUPER Scalping.txt | 15 | dynamic computed member access is not allowed |
| SUPER Scalping.txt | 60 | dynamic computed member access is not allowed |
| SWIFT ALGO.txt | 1 | Cannot read properties of undefined (reading '0') |
| SWIFT ALGO.txt | 5 | Cannot read properties of undefined (reading '0') |
| SWIFT ALGO.txt | 60 | Cannot read properties of undefined (reading '3') |
| Sniper Trading Algo Pro.txt | 1 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 205:18 |
| Sniper Trading Algo Pro.txt | 5 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 205:18 |
| Sniper Trading Algo Pro.txt | 15 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 205:18 |
| Sniper Trading Algo Pro.txt | 60 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 205:18 |
| TrendFilter.txt | 1 | Cannot read properties of undefined (reading '0') |
| TrendFilter.txt | 5 | Cannot read properties of undefined (reading '0') |
| TrendFilter.txt | 15 | Cannot read properties of null (reading 'set_style') |
| TrendFilter.txt | 60 | Cannot read properties of null (reading 'set_style') |
| simplealgo v3.txt | 1 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: D |
| simplealgo v3.txt | 5 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: W |
| simplealgo v3.txt | 15 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: W |
| simplealgo v3.txt | 60 | SYNTHETIC_HISTORY_TOO_SHORT_FOR_FRAME: M |
| strategy with signals.txt | 1 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 63:7 |
| strategy with signals.txt | 5 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 63:7 |
| strategy with signals.txt | 15 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 63:7 |
| strategy with signals.txt | 60 | Failed to transpile Pine Script version 5: Unexpected token KEYWORD 'import' at 63:7 |
| WaveTrend.txt | 1 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 557:18 |
| WaveTrend.txt | 5 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 557:18 |
| WaveTrend.txt | 15 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 557:18 |
| WaveTrend.txt | 60 | Failed to transpile Pine Script version 6: Expected OPERATOR but got IDENTIFIER at 557:18 |
| X.txt | 1 | Cannot read properties of undefined (reading '0') |
| X.txt | 5 | Cannot read properties of undefined (reading '0') |
| X.txt | 15 | Cannot read properties of undefined (reading '0') |
| X.txt | 60 | Cannot read properties of undefined (reading '3') |
| XALGOX-15M_1H_1D.txt | 1 | Cannot read properties of undefined (reading '0') |
| XALGOX-15M_1H_1D.txt | 5 | Cannot read properties of undefined (reading '0') |
| XALGOX-15M_1H_1D.txt | 60 | Cannot read properties of undefined (reading '3') |
| XALGOX.txt | 1 | Cannot read properties of undefined (reading '0') |
| XALGOX.txt | 5 | Cannot read properties of undefined (reading '0') |
| XALGOX.txt | 60 | Cannot read properties of undefined (reading '3') |
| Xpert Algo.txt | 1 | Cannot read properties of undefined (reading '0') |
| Xpert Algo.txt | 5 | Cannot read properties of undefined (reading '0') |
| Xpert Algo.txt | 15 | Cannot read properties of undefined (reading '0') |
| Xpert Algo.txt | 60 | Cannot read properties of undefined (reading '3') |
| ZZ Algo  Signals & Overlays.txt | 1 | Cannot read properties of undefined (reading '0') |
| ZZ Algo  Signals & Overlays.txt | 5 | Cannot read properties of undefined (reading '0') |
| ZZ Algo  Signals & Overlays.txt | 15 | Cannot read properties of undefined (reading '0') |
| ZZ Algo  Signals & Overlays.txt | 60 | Cannot read properties of undefined (reading '3') |
| ZZ Algo.txt | 1 | Cannot read properties of undefined (reading '0') |
| ZZ Algo.txt | 5 | Cannot read properties of undefined (reading '0') |
| ZZ Algo.txt | 15 | Cannot read properties of undefined (reading '0') |
| ZZ Algo.txt | 60 | Cannot read properties of undefined (reading '3') |

## مجالات الإعدادات

| التصنيف | عدد الخانات |
|---|---|
| OPEN_OTHER_DOMAIN | 342 |
| OPEN_NUMERIC_DOMAIN | 1337 |
| COLOR_DOMAIN | 937 |
| BOOLEAN | 1969 |
| FINITE_DECLARED_RANGE | 653 |
| UNRESOLVED_DEFAULT_OR_DOMAIN | 53 |
| DECLARED_OPTIONS | 648 |
| UNRESOLVED_OPTIONS | 1 |

الأعداد هنا خانات إعداد وفحوص تجهيز، لا عدد إشارات أو تقدير دقة. السجل RESOLVED-PARAMETERS.json يحتفظ بالمصدر والسطر والتعريف والحدود لكل خانة، مع عدم اعتمادها تلقائيًا كتجربة دخول.

## إعادة إنتاج الأدلة

تُثبت نسخة pinets@0.11.1 وملف package-lock.json. تعمل أدوات الحساب دون اعتماد تداول، ويمنع الفحص الاتصال الخارجي أثناء تشغيل Pine. بيانات الفحص اصطناعية بالكامل.

أوامر إعادة الفحص من مجلد الحزمة بعد فك حزمة الأدلة:

```bash
python3 fetch_sources.py
npm ci --prefix pine_runtime --ignore-scripts --no-audit --no-fund
python3 resolve_domains.py
python3 collect_historical_grids.py
python3 validate_primitives.py
python3 probe_all_frames.py
python3 check_completeness.py
```

الأمر الأخير يعيد خروج2 لأن شمولية التنفيذ غير مكتملة؛ ذلك متعمد لمنع تسليم غير جاهز، وليس نتيجة تداول سلبية. لا يعيد اختبار كل مؤشر في السوق ولا يثبت وجود أفضل إعداد.

تجاوز التحضير600ثانية موثق. الزمن الكلي الدقيق غير مقاس؛ الحد الأدنى منذ أول توقيت محفوظ هو 1133.8ثانية. زمن فحص الفريمات الاصطناعي منفصل: 132.731ثانية. لا تُنسب هذه المدة وحدها إلى العمل كله.

التالي: استكمال تحويل المصادر واعتماد مجالات الدخول وتوقيت النسخ والمراجعة الدلالية، ثم تجربة جاهزية كاملة قبل تسليم الورقة الموحدة للمنفذ.
