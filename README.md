# 📰 أخبار المقاومة

[![Python](https://img.shields.io/badge/Python-3.x-blue)](https://www.python.org/)
[![GitHub Actions](https://img.shields.io/badge/GitHub-Actions-black)](https://github.com/features/actions)
[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-brightgreen)](https://pages.github.com/)

## 📋 نظرة عامة

موقع أخبار عربي تلقائي يجمع وينشر أخبار المقاومة والمستجدات في الشرق الأوسط من مصادر متعددة.

## 📰 المصادر

### 📺 قنوات Telegram
- **PressTV** -(ir)
- **SuppressedNews** - أخبار مقموعة

### 📡 RSS Feeds
- **Middle East Monitor** - مراقب الشرق الأوسط

### 🎥 YouTube
- مقاطع فيديو ذات صلة
- ملخصات بالذكاء الاصطناعي (اختياري)

## ⭐ المميزات

### 🔄 الأتمتة
- تحديث كل **10 دقائق** عبر GitHub Actions
- نشر تلقائي عبر GitHub Pages
- إزالة التكرار تلقائياً

### 🌐 العرض
- بطاقات RTL عربية
- ألوان مميزة لكل مصدر
- نافذة أخبار 72 ساعة

### 🎥 الفيديو
- عرض فيديوهات YouTube في الأعلى
- إخفاء بعد 24 ساعة
- ملخصات بالذكاء الاصطناعي (OpenAI/Gemini)

### 🌍 الترجمة
- ترجمة تلقائية للأخبار الإنجليزية
- Google Translate API

## 🏗️ البنية

```
┌─────────────────┐
│  GitHub Actions  │
│  (كل 10 دقائق)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Python Scripts │
│  (جمع الأخبار)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   news.json     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  GitHub Pages   │
│  (HTML/CSS/JS)  │
└─────────────────┘
```

## 🚀 التشغيل

```bash
# استنساخ المستودع
git clone https://github.com/ahmed4050/resistance-news.git

# تثبيت المتطلبات
pip install -r requirements.txt

# تشغيل يدوياً
python scraper.py
```

## ⚙️ الإعدادات

```python
# config.py
SOURCES = {
    'telegram': [...],
    'rss': [...],
    'youtube': [...]
}

# إعدادات OpenAI (اختياري)
OPENAI_API_KEY = "your_key_here"  # في GitHub Secrets
```

## 📁 هيكل الملفات

```
resistance-news/
├── scraper.py          # السكربت الرئيسي
├── config.py           # الإعدادات
├── requirements.txt    # المتطلبات
├── index.html          # الصفحة الرئيسية
├── style.css           # الأنماط
├── script.js           # المنطق البرمجي
├── news.json           # بيانات الأخبار
└── .github/
    └── workflows/
        └── update.yml  # GitHub Actions
```

## 📊 الإحصائيات

- 📰 مصادر: 5+
- 🔄 تحديثات: كل 10 دقائق
- 🌍 اللغة: العربية
- 📱 متوافق مع: جميع الأجهزة

## 👨‍💻 المؤلف

**Ahmed Al-Qassabi** - [GitHub](https://github.com/ahmed4050)

## 📄 الرخصة

هذا المشروع مرخص بموجب رخصة MIT.
