from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.config import PROJECT_ROOT
from app.db.models import Article, Base, Source, Story
from app.db.session import SessionLocal, engine
from app.services.ingestion import ingest_records
from app.services.pipeline import process_corpus

LANGUAGES = {
    "en": ("English", "India"),
    "hi": ("Hindi", "North India"),
    "kn": ("Kannada", "Karnataka"),
    "ta": ("Tamil", "Tamil Nadu"),
    "te": ("Telugu", "Telangana"),
}

STORIES = [
    {
        "key": "solar-access", "topic": "environment",
        "title": {"en": "solar rooftop access", "hi": "सौर छत पहुंच", "kn": "ಸೌರ ಮೇಲ್ಛಾವಣಿ ಪ್ರವೇಶ", "ta": "சூரிய கூரை அணுகல்", "te": "సౌర పైకప్పు ప్రాప్యత"},
        "phrase": {"en": "solar rooftop service", "hi": "सौर सेवा", "kn": "ಸೌರ ಸೇವೆ", "ta": "சூரிய சேவை", "te": "సౌర సేవ"},
    },
    {
        "key": "rural-water", "topic": "infrastructure",
        "title": {"en": "rural water service", "hi": "ग्रामीण जल सेवा", "kn": "ಗ್ರಾಮೀಣ ನೀರಿನ ಸೇವೆ", "ta": "கிராமப்புற நீர் சேவை", "te": "గ్రామీణ నీటి సేవ"},
        "phrase": {"en": "rural water service", "hi": "जल सेवा", "kn": "ನೀರಿನ ಸೇವೆ", "ta": "நீர் சேவை", "te": "నీటి సేవ"},
    },
    {
        "key": "school-connectivity", "topic": "education",
        "title": {"en": "classroom connectivity", "hi": "कक्षा डिजिटल संपर्क", "kn": "ತರಗತಿ ಸಂಪರ್ಕ", "ta": "வகுப்பறை இணைப்பு", "te": "తరగతి అనుసంధానం"},
        "phrase": {"en": "school digital service", "hi": "डिजिटल शिक्षा", "kn": "ಡಿಜಿಟಲ್ ಶಿಕ್ಷಣ", "ta": "டிஜிட்டல் கல்வி", "te": "డిజిటల్ విద్య"},
    },
    {
        "key": "public-clinics", "topic": "healthcare",
        "title": {"en": "public clinic access", "hi": "सार्वजनिक स्वास्थ्य सेवा", "kn": "ಸಾರ್ವಜನಿಕ ಆರೋಗ್ಯ ಸೇವೆ", "ta": "பொது சுகாதார சேவை", "te": "ప్రజా ఆరోగ్య సేవ"},
        "phrase": {"en": "public health clinic", "hi": "स्वास्थ्य सेवा", "kn": "ಆರೋಗ್ಯ ಸೇವೆ", "ta": "சுகாதார சேவை", "te": "ఆరోగ్య సేవ"},
    },
    {
        "key": "farm-services", "topic": "agriculture",
        "title": {"en": "farm support service", "hi": "कृषि सहायता सेवा", "kn": "ಕೃಷಿ ಬೆಂಬಲ ಸೇವೆ", "ta": "விவசாய ஆதரவு சேவை", "te": "వ్యవసాయ మద్దతు సేవ"},
        "phrase": {"en": "farm service", "hi": "कृषि सेवा", "kn": "ಕೃಷಿ ಸೇವೆ", "ta": "விவசாய சேவை", "te": "వ్యవసాయ సేవ"},
    },
    {
        "key": "road-safety", "topic": "infrastructure",
        "title": {"en": "highway safety review", "hi": "राष्ट्रीय सड़क सुरक्षा समीक्षा", "kn": "ರಾಷ್ಟ್ರೀಯ ರಸ್ತೆ ಸುರಕ್ಷತಾ ಪರಿಶೀಲನೆ", "ta": "தேசிய சாலை பாதுகாப்பு ஆய்வு", "te": "జాతీయ రహదారి భద్రత సమీక్ష"},
        "phrase": {"en": "national highway safety", "hi": "राष्ट्रीय सड़क", "kn": "ರಾಷ್ಟ್ರೀಯ ರಸ್ತೆ", "ta": "தேசிய சாலை", "te": "జాతీయ రహదారి"},
    },
    {
        "key": "clean-cooking", "topic": "welfare",
        "title": {"en": "clean cooking access", "hi": "स्वच्छ रसोई पहुंच", "kn": "ಸ್ವಚ್ಛ ಅಡುಗೆ ಪ್ರವೇಶ", "ta": "சுத்தமான சமையல் அணுகல்", "te": "శుభ్రమైన వంట ప్రాప్యత"},
        "phrase": {"en": "clean cooking service", "hi": "स्वच्छ रसोई सेवा", "kn": "ಸ್ವಚ್ಛ ಅಡುಗೆ ಸೇವೆ", "ta": "சுத்தமான சமையல் சேவை", "te": "శుభ్రమైన వంట సేవ"},
    },
    {
        "key": "digital-services", "topic": "technology",
        "title": {"en": "public digital services", "hi": "सार्वजनिक डिजिटल सेवा", "kn": "ಸಾರ್ವಜನಿಕ ಡಿಜಿಟಲ್ ಸೇವೆ", "ta": "பொது டிஜிட்டல் சேவை", "te": "ప్రజా డిజిటల్ సేవ"},
        "phrase": {"en": "digital service access", "hi": "डिजिटल सेवा", "kn": "ಡಿಜಿಟಲ್ ಸೇವೆ", "ta": "டிஜிட்டல் சேவை", "te": "డిజిటల్ సేవ"},
    },
    {
        "key": "skills-employment", "topic": "employment",
        "title": {"en": "skills and employment pilot", "hi": "कौशल और रोजगार पहल", "kn": "ಕೌಶಲ್ಯ ಮತ್ತು ಉದ್ಯೋಗ ಉಪಕ್ರಮ", "ta": "திறன் மற்றும் வேலைவாய்ப்பு முயற்சி", "te": "నైపుణ్యాలు మరియు ఉపాధి కార్యక్రమం"},
        "phrase": {"en": "employment skills service", "hi": "रोजगार कौशल सेवा", "kn": "ಉದ್ಯೋಗ ಕೌಶಲ್ಯ ಸೇವೆ", "ta": "வேலைவாய்ப்பு திறன் சேவை", "te": "ఉపాధి నైపుణ్య సేవ"},
    },
    {
        "key": "budget-consultation", "topic": "economy",
        "title": {"en": "public budget consultation", "hi": "सार्वजनिक बजट परामर्श", "kn": "ಸಾರ್ವಜನಿಕ ಬಜೆಟ್ ಸಮಾಲೋಚನೆ", "ta": "பொது வரவுசெலவு ஆலோசனை", "te": "ప్రజా బడ్జెట్ సంప్రదింపులు"},
        "phrase": {"en": "union budget consultation", "hi": "केंद्रीय बजट", "kn": "ಕೇಂದ್ರ ಬಜೆಟ್", "ta": "மத்திய வரவுசெலவு", "te": "కేంద్ర బడ్జెట్"},
    },
]

SENTENCES = {
    "en": {
        "disclaimer": "This is synthetic academic coverage and is not a real news report.",
        "context": "In this fictional Government of India media exercise, a Union ministry shared a demonstration about {phrase}.",
        "focus": "The scenario considers regional service access and how local needs may be represented.",
        "positive": "Supporters welcomed the proposed improvement and described a possible benefit for households.",
        "negative": "Local readers raised concerns about delay and limited access for remote households.",
        "close": "All names and events in this sample are invented for an academic interface demonstration.",
    },
    "hi": {
        "disclaimer": "यह काल्पनिक नमूना है और वास्तविक समाचार रिपोर्ट नहीं है।",
        "context": "भारत सरकार के इस काल्पनिक मीडिया अभ्यास में एक केंद्रीय मंत्रालय ने {phrase} का प्रदर्शन साझा किया।",
        "focus": "यह परिदृश्य क्षेत्रीय सेवा पहुंच और स्थानीय जरूरतों पर विचार करता है।",
        "positive": "समर्थकों ने प्रस्तावित सुधार का स्वागत किया और परिवारों के लिए लाभ की बात कही।",
        "negative": "स्थानीय पाठकों ने देरी और दूरस्थ परिवारों तक सीमित पहुंच पर चिंता जताई।",
        "close": "इस नमूने के सभी नाम और घटनाएं अकादमिक प्रदर्शन के लिए बनाई गई हैं।",
    },
    "kn": {
        "disclaimer": "ಇದು ಕಲ್ಪಿತ ಮಾದರಿ; ನೈಜ ಸುದ್ದಿವರದಿ ಅಲ್ಲ.",
        "context": "ಭಾರತ ಸರ್ಕಾರದ ಈ ಕಲ್ಪಿತ ಮಾಧ್ಯಮ ಅಭ್ಯಾಸದಲ್ಲಿ ಕೇಂದ್ರ ಸಚಿವಾಲಯವು {phrase} ಕುರಿತು ಮಾದರಿಯನ್ನು ಹಂಚಿಕೊಂಡಿತು.",
        "focus": "ಈ ಸನ್ನಿವೇಶವು ಪ್ರಾದೇಶಿಕ ಸೇವಾ ಪ್ರವೇಶ ಮತ್ತು ಸ್ಥಳೀಯ ಅಗತ್ಯಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತದೆ.",
        "positive": "ಬೆಂಬಲಿಗರು ಪ್ರಸ್ತಾವಿತ ಸುಧಾರಣೆಯನ್ನು ಸ್ವಾಗತಿಸಿ ಕುಟುಂಬಗಳಿಗೆ ಲಾಭವಾಗಬಹುದು ಎಂದರು.",
        "negative": "ಸ್ಥಳೀಯ ಓದುಗರು ವಿಳಂಬ ಮತ್ತು ದೂರದ ಕುಟುಂಬಗಳಿಗೆ ಸೀಮಿತ ಪ್ರವೇಶದ ಬಗ್ಗೆ ಕಳವಳ ವ್ಯಕ್ತಪಡಿಸಿದರು.",
        "close": "ಈ ಮಾದರಿಯ ಹೆಸರುಗಳು ಮತ್ತು ಘಟನೆಗಳು ಶೈಕ್ಷಣಿಕ ಪ್ರದರ್ಶನಕ್ಕಾಗಿ ಕಲ್ಪಿತವಾಗಿವೆ.",
    },
    "ta": {
        "disclaimer": "இது கற்பனை மாதிரி; உண்மையான செய்தி அறிக்கை அல்ல.",
        "context": "இந்திய அரசின் இந்த கற்பனை ஊடகப் பயிற்சியில் மத்திய அமைச்சகம் {phrase} குறித்த மாதிரியைப் பகிர்ந்தது.",
        "focus": "இந்த சூழல் பிராந்திய சேவை அணுகலையும் உள்ளூர் தேவைகளையும் ஆராய்கிறது.",
        "positive": "ஆதரவாளர்கள் முன்மொழியப்பட்ட மேம்பாட்டை வரவேற்று குடும்பங்களுக்கு நன்மை இருக்கலாம் என்றனர்.",
        "negative": "உள்ளூர் வாசகர்கள் தாமதம் மற்றும் தொலைதூர குடும்பங்களுக்கான குறைந்த அணுகல் குறித்து கவலை தெரிவித்தனர்.",
        "close": "இந்த மாதிரியின் பெயர்களும் நிகழ்வுகளும் செயலி விளக்கத்திற்காக உருவாக்கப்பட்டவை.",
    },
    "te": {
        "disclaimer": "ఇది కల్పిత నమూనా; నిజమైన వార్తా నివేదిక కాదు.",
        "context": "భారత ప్రభుత్వానికి సంబంధించిన ఈ కల్పిత మీడియా అభ్యాసంలో కేంద్ర మంత్రిత్వ శాఖ {phrase} నమూనాను పంచుకుంది.",
        "focus": "ఈ సందర్భం ప్రాంతీయ సేవల ప్రాప్యత మరియు స్థానిక అవసరాలను పరిశీలిస్తుంది.",
        "positive": "మద్దతుదారులు ప్రతిపాదిత మెరుగుదలను స్వాగతించి కుటుంబాలకు ప్రయోజనం ఉండవచ్చన్నారు.",
        "negative": "స్థానిక పాఠకులు ఆలస్యం మరియు దూర ప్రాంత కుటుంబాలకు పరిమిత ప్రాప్యతపై ఆందోళన వ్యక్తం చేశారు.",
        "close": "ఈ నమూనాలోని పేర్లు, సంఘటనలు అనువర్తన ప్రదర్శన కోసం కల్పించబడ్డాయి.",
    },
}


def generate_demo_articles() -> list[dict]:
    base_date = datetime(2026, 9, 1, 9, 0, tzinfo=UTC)
    articles: list[dict] = []
    for story_index, story in enumerate(STORIES):
        for language_index, (language, (language_name, region)) in enumerate(LANGUAGES.items()):
            for edition in range(2):
                wording = SENTENCES[language]
                tone = "positive" if edition == 0 else "negative"
                title = f"[SYNTHETIC] {story['title'][language]} / edition {edition + 1}"
                content = " ".join([
                    wording["disclaimer"],
                    wording["context"].format(phrase=story["phrase"][language]),
                    wording["focus"],
                    wording[tone],
                    wording["close"],
                ])
                published = base_date + timedelta(days=story_index, hours=language_index * 2 + edition)
                source_name = f"Demo {language_name} {'National Desk' if edition == 0 else 'Regional Review'}"
                articles.append({
                    "title": title,
                    "content": content,
                    "url": f"synthetic://prj277/{story['key']}/{language}/{edition + 1}",
                    "author": "Synthetic sample generator",
                    "published_at": published.isoformat(),
                    "language": language,
                    "region": region,
                    "source_name": source_name,
                    "source_type": "synthetic-demo",
                    "is_synthetic": True,
                })
    return articles


def seed() -> dict:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Refresh only generated demo records so edits to the fixture are reflected on each run.
        for article in list(db.scalars(select(Article).where(Article.is_synthetic.is_(True)))):
            db.delete(article)
        db.flush()
        for story in list(db.scalars(select(Story).where(~Story.article_links.any()))):
            db.delete(story)
        for source in list(db.scalars(select(Source))):
            if not db.scalar(select(Article.id).where(Article.source_id == source.id).limit(1)):
                db.delete(source)
        db.commit()
        records = generate_demo_articles()
        sample_file = PROJECT_ROOT / "data" / "sample" / "prj277_synthetic_articles.json"
        sample_file.parent.mkdir(parents=True, exist_ok=True)
        sample_file.write_text(json.dumps({"dataset": "synthetic academic demonstration", "articles": records}, ensure_ascii=False, indent=2), encoding="utf-8")
        import_result = ingest_records(db, records)
        synthetic_ids = list(db.scalars(select(Article.id).where(Article.is_synthetic.is_(True))))
        pipeline_result = process_corpus(db, article_ids=synthetic_ids)
        return {"dataset": "synthetic academic demonstration", "expected_articles": len(records), "ingestion": import_result, "pipeline": pipeline_result}
    finally:
        db.close()


if __name__ == "__main__":
    print(json.dumps(seed(), ensure_ascii=False, indent=2))
