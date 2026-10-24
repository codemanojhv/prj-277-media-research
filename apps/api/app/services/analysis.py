from __future__ import annotations

import re

from app.services.language import clean_text

TOPIC_TERMS: dict[str, list[str]] = {
    "economy": ["economy", "economic", "budget", "बजट", "आर्थिक", "अर्थव्यवस्था", "ಆರ್ಥಿಕ", "ಬಜೆಟ್", "வரவுசெலவு", "బడ్జెట్", "ఆర్థిక"],
    "employment": ["employment", "jobs", "काम", "रोजगार", "ಉದ್ಯೋಗ", "வேலைவாய்ப்பு", "ఉపాధి"],
    "education": ["education", "school", "शिक्षा", "ಶಿಕ್ಷಣ", "கல்வி", "విద్య"],
    "healthcare": ["health", "clinic", "स्वास्थ्य", "ಆರೋಗ್ಯ", "சுகாதாரம்", "ఆరోగ్యం"],
    "infrastructure": ["infrastructure", "highway", "road", "water", "सड़क", "जल", "पानी", "अवसंरचना", "ಮೂಲಸೌಕರ್ಯ", "ನೀರು", "சாலை", "தண்ணீர்", "உள்கட்டமைப்பு", "నీరు", "రోడ్డు", "మౌలిక సదుపాయాలు"],
    "agriculture": ["agriculture", "farm", "कृषि", "விவசாயம்", "ಕೃಷಿ", "వ్యవసాయం"],
    "technology": ["technology", "digital", "तकनीक", "डिजिटल", "ತಂತ್ರಜ್ಞಾನ", "தொழில்நுட்பம்", "సాంకేతిక"],
    "welfare": ["welfare", "scheme", "cooking", "stove", "योजना", "कल्याण", "रसोई", "ಅಡುಗೆ", "ಯೋಜನೆ", "சமையல்", "நலத்திட்டம்", "వంట", "పథకం"],
    "environment": ["environment", "solar", "सौर", "ಸೌರ", "சூரிய", "సౌర", "जलवायु", "ಪರಿಸರ", "சுற்றுச்சூழல்", "పర్యావరణం"],
    "governance": ["governance", "parliament", "मंत्रालय", "ಸಚಿವಾಲಯ", "அமைச்சகம்", "మంత్రిత్వ శాఖ"],
}

POSITIVE_TERMS = [
    "improved", "improvement", "benefit", "welcomed", "positive", "expanded access", "लाभ", "सुधार", "सकारात्मक",
    "மேம்பாடு", "நன்மை", "ಸುಧಾರಣೆ", "ಲಾಭ", "మెరుగుదల", "ప్రయోజనం",
]
NEGATIVE_TERMS = [
    "concern", "delay", "shortfall", "criticism", "risk", "limited access", "चिंता", "देरी", "कमी",
    "கவலை", "தாமதம்", "குறை", "ಕಳವಳ", "ವಿಳಂಬ", "ಕೊರತೆ", "ఆందోళన", "ఆలస్యం", "కొరత",
]
CONCERN_TERMS = ["concern", "delay", "shortfall", "access gap", "चिंता", "देरी", "कमी", "கவலை", "தாமதம்", "களವಳ", "ಆಲಸ్యం", "ఆందోళన", "ఆలస్యం"]
POSITIVE_MARKERS = ["benefit", "welcomed", "improvement", "improved", "लाभ", "सुधार", "நன்மை", "மேம்பாடு", "ಲಾಭ", "ಸುಧಾರಣೆ", "ప్రయోజనం", "మెరుగుదల"]
CLAIM_MARKERS = ["reported", "announced", "said", "states", "shared", "के अनुसार", "घोषणा", "ಹೇಳಿದೆ", "ಹಂಚಿಕೊಂಡಿತು", "அறிவித்தது", "பகிர்ந்தது", "తెలిపింది", "పంచుకుంది"]
ENTITY_TERMS = [
    ("Government of India", "government"), ("भारत सरकार", "government"), ("ಭಾರತ ಸರ್ಕಾರ", "government"),
    ("இந்திய அரசு", "government"), ("భారత ప్రభుత్వం", "government"), ("Parliament", "institution"),
    ("संसद", "institution"), ("ಸಂಸತ್ತು", "institution"), ("நாடாளுமன்றம்", "institution"), ("పార్లమెంట్", "institution"),
]


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?।])\s+", clean_text(text))
    return [part.strip() for part in parts if len(part.strip()) > 12]


def _matches(sentence: str, terms: list[str]) -> list[str]:
    folded = sentence.casefold()
    return [term for term in terms if term.casefold() in folded]


def _snippets(text: str, terms: list[str], limit: int = 3) -> list[str]:
    return [sentence for sentence in sentences(text) if _matches(sentence, terms)][:limit]


def analyze_article(text: str, language: str) -> dict:
    text = clean_text(text)
    sentence_list = sentences(text)
    positive_evidence = _snippets(text, POSITIVE_TERMS)
    negative_evidence = _snippets(text, NEGATIVE_TERMS)
    if positive_evidence and negative_evidence:
        sentiment, sentiment_score, sentiment_confidence = "mixed", 0.0, 0.67
    elif positive_evidence:
        sentiment, sentiment_score, sentiment_confidence = "positive", 0.62, 0.64
    elif negative_evidence:
        sentiment, sentiment_score, sentiment_confidence = "negative", -0.62, 0.64
    else:
        sentiment, sentiment_score, sentiment_confidence = "uncertain", 0.0, 0.25

    topics = []
    folded = text.casefold()
    for topic, terms in TOPIC_TERMS.items():
        found = [term for term in terms if term.casefold() in folded]
        if found:
            topics.append({"topic": topic, "confidence": 0.62, "evidence": found[0]})
    topics.sort(key=lambda item: item["topic"])

    entities = []
    for term, entity_type in ENTITY_TERMS:
        if term.casefold() in folded:
            entities.append({"text": term, "type": entity_type, "confidence": 0.8, "evidence": term})
    for match in re.findall(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", text):
        if match.casefold() not in {entity["text"].casefold() for entity in entities} and match not in {"This", "In", "The", "A", "Officials"}:
            entities.append({"text": match, "type": "named-phrase", "confidence": 0.55, "evidence": match})
    entities = entities[:12]

    concerns = [{"text": s, "type": "extracted", "confidence": 0.62} for s in _snippets(text, CONCERN_TERMS)]
    positive_aspects = [{"text": s, "type": "extracted", "confidence": 0.62} for s in _snippets(text, POSITIVE_MARKERS)]
    claims = []
    for sentence in sentence_list:
        if _matches(sentence, CLAIM_MARKERS) or re.search(r"\b\d+(?:\.\d+)?%?\b", sentence):
            claims.append({"text": sentence, "type": "article-claim", "confidence": 0.48})
    key_points = [{"text": sentence, "type": "extracted", "confidence": 0.76} for sentence in sentence_list[:3]]
    summary = " ".join(sentence_list[:2])[:620]
    return {
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "sentiment_confidence": sentiment_confidence,
        "summary": summary or "The article does not contain enough text to summarize.",
        "key_points": key_points,
        "topics": topics[:5],
        "entities": entities,
        "claims": claims[:5],
        "concerns": concerns,
        "positive_aspects": positive_aspects,
        "evidence": {
            "sentiment": positive_evidence[:1] + negative_evidence[:1],
            "topics": [topic["evidence"] for topic in topics[:5]],
            "summary": sentence_list[:2],
        },
        "model": f"local-evidence-rules-v1/{language}",
    }
