# Resistance News | أخبار المقاومة

موقع أخبار عربي ثابت (Static Site) يجمع ويورد الأخبار والتحليلات من مصادر مختارة،
ويعرضها في صفحة واحدة تتحدّث تلقائياً كل بضعة دقائق دون تدخّل يدوي.

> الموقع مبني بملفات بسيطة (HTML/CSS/JS + Python) ويعمل عبر **GitHub Pages** و**GitHub Actions** — لا يحتاج خادماً.

---

## ✨ المميزات

- **تحديث تلقائي** كل 10 دقائق عبر GitHub Actions.
- عرض البطاقات بالعربية (اتجاه RTL) مع تمييز كل مصدر بلون خاص.
- جلب الأخبار من **قنوات تيليغرام** و**خلاصات RSS** و**فيديوهات يوتيوب**.
- ترجمة تلقائية للأخبار الإنجليزية إلى العربية.
- بطاقات فيديو يوتيوب تحتوي **العنوان + رابط الفيديو** مباشرة.
- صفحة خفيفة تتحدّث ذاتياً كل 5 دقائق في المتصفح.

---

## 🔄 كيف يعمل

1. سكربت `fetch_news.py` يجمع الأخبار من المصادر ويخزّنها في `news.json`.
2. سكربت `fetch_youtube.py` يجلب آخر فيديوهات قناة يوتيوب المحددة،
   ويخزّن بياناتها في `youtube_cache.json` (لتفادي إعادة معالجة القديم).
3. ملف `index.html` يعرض محتوى `news.json` في بطاقات منظّمة حسب التاريخ.
4. GitHub Action (`.github/workflows/update-news.yml`) يشغّل السكربت كل 10 دقائق
   ويرفع التغييرات تلقائياً إلى المستودع، فتنعكس فوراً على الموقع.

```
تيليغرام + RSS + يوتيوب
        │
        ▼
 fetch_news.py / fetch_youtube.py
        │
        ▼
     news.json  ──►  index.html  ──►  الموقع
        │
        ▼
 GitHub Actions (كل 10 دقائق)
```

---

## 📡 المصادر الحالية

| المصدر | النوع | الوصف |
|--------|------|-------|
| `PressTV` | تيليغرام | Press TV |
| `suppressednews` | تيليغرام | Suppressed News |
| `MiddleEastMonitor` | RSS | Middle East Monitor |
| `YouTube-AlAouni` | يوتيوب | قناة **عبد الحميد العوني** (عنوان الفيديو + رابط) |

---

## 🚀 التشغيل محلياً

```bash
# تثبيت المتطلبات
pip install -r requirements.txt

# جلب الأخبار وتحديث news.json
python fetch_news.py

# افتح index.html في المتصفح لمعاينة الموقع
```

---

## 🛠 التخصيص

### إضافة قناة تيليغرام
عدّل قائمة `TELEGRAM_CHANNELS` في `fetch_news.py`:

```python
TELEGRAM_CHANNELS = [
    "PressTV",
    "suppressednews",
    "قناتك_هنا",
]
```

### إضافة خلاصة RSS
عدّل قائمة `RSS_FEEDS` في `fetch_news.py`:

```python
RSS_FEEDS = [
    {"name": "MiddleEastMonitor", "url": "https://www.middleeastmonitor.com/feed/"},
]
```

### تغيير قناة يوتيوب
عدّل `CHANNEL_URL` في `fetch_youtube.py` (يدعم رابط `@handle` أو `channel/UC...`).

### إضافة وسم/لون جديد في الموقع
أضف اسم المصدر في `CHANNEL_LABELS` داخل `index.html` مع صنف CSS مخصص.

---

## 🤖 تلخيص فيديوهات يوتيوب بالذكاء الاصطناعي (اختياري)

حالياً تظهر بطاقة الفيديو **عنوان الفيديو + رابطه** (بلا مفتاح API).

لإضافة ملخص عربي قصير (2-4 جمل) من محتوى الفيديو، فعّل التلخيص عبر أي نقطة
نهاية متوافقة مع واجهة OpenAI (مثل **GitHub Models** أو **Gemini** المجانية):

1. في **إعدادات المستودع → Secrets and variables → Actions** أضف:
   - `LLM_BASE_URL` — مثلاً `https://models.inference.ai.azure.com` (GitHub Models)
     أو `https://generativelanguage.googleapis.com/v1beta/openai` (Gemini).
   - `LLM_API_KEY` — رمز الوصول/المفتاح.
   - `LLM_MODEL` — اختياري، افتراضياً `gpt-4o-mini` (GitHub Models) أو `gemini-2.5-flash` (Gemini).

2. السكربت `fetch_youtube.py` سيُلخّص فقط الفيديوهات **الجديدة** عند اكتشافها
   (ويخزّن الملخص في `youtube_cache.json`)، ثم يستخدمه كنص البطاقة؛
   وإذا لم تُضبط الأسرار يكتفي بعنوان الفيديو تلقائياً.

> للتشغيل محلياً: اضبط هذه المتغيرات في بيئتك قبل تشغيل `python fetch_news.py`.

---

## 📋 المتطلبات

- Python 3.11+
- الحزم في `requirements.txt`:
  - `requests`, `beautifulsoup4`, `deep-translator`
  - `youtube-transcript-api`

---

## ⚠️ إخلاء مسؤولية

المحتوى منسوخ آلياً من مصادره الخارجية ولا يعبّر بالضرورة عن رأي صاحب الموقع.
الأخبار تُجمع لأغراض المتابعة والرصد فقط.

---

## 👤 صاحب المشروع

**Ahmed Alqassabi** — ahmed4050@gmai.com
