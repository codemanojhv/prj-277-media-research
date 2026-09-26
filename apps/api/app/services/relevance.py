from __future__ import annotations

from app.core.config import RELEVANCE_THRESHOLD

RELEVANCE_TERMS = {
    "English": [
        "government of india", "union government", "central government", "union ministry",
        "ministry of", "union budget", "parliament", "cabinet", "central scheme", "pm-kisan",
        "swachh bharat mission", "swachh bharat", "make in india", "digital india", "startup india",
        "skill india", "jal jeevan mission", "ayushman bharat", "pm kisan", "namami gange",
        "national health mission", "smart cities mission", "pm ujjwala yojana", "pm svanidhi",
    ],
    "Hindi": ["भारत सरकार", "केंद्र सरकार", "केंद्रीय सरकार", "मंत्रालय", "संसद", "केंद्रीय योजना", "यूनियन बजट", "स्वच्छ भारत मिशन", "स्वच्छ भारत", "मेक इन इंडिया", "डिजिटल इंडिया", "जल जीवन मिशन", "आयुष्मान भारत"],
    "Kannada": ["ಭಾರತ ಸರ್ಕಾರ", "ಕೇಂದ್ರ ಸರ್ಕಾರ", "ಕೇಂದ್ರ ಸಚಿವಾಲಯ", "ಸಚಿವಾಲಯ", "ಸಂಸತ್ತು", "ಕೇಂದ್ರ ಯೋಜನೆ", "ಸ್ವಚ್ಛ ಭಾರತ ಮಿಷನ್", "ಸ್ವಚ್ಛ ಭಾರತ", "ಮೇಕ್ ಇನ್ ಇಂಡಿಯಾ", "ಡಿಜಿಟಲ್ ಇಂಡಿಯಾ", "ಜಲ ಜೀವನ್ ಮಿಷನ್", "ಆಯುಷ್ಮಾನ್ ಭಾರತ್"],
    "Tamil": ["இந்திய அரசு", "மத்திய அரசு", "மத்திய அமைச்சகம்", "அமைச்சகம்", "நாடாளுமன்றம்", "மத்திய திட்டம்", "தூய்மை இந்தியா இயக்கம்", "தூய்மை இந்தியா", "மேக் இன் இந்தியா", "டிஜிட்டல் இந்தியா", "ஜல் ஜீவன் மிஷன்", "ஆயுஷ்மான் பாரத்"],
    "Telugu": ["భారత ప్రభుత్వం", "కేంద్ర ప్రభుత్వం", "కేంద్ర మంత్రిత్వ శాఖ", "మంత్రిత్వ శాఖ", "పార్లమెంట్", "కేంద్ర పథకం", "స్వచ్ఛ భారత్ మిషన్", "స్వచ్ఛ భారత్", "మేక్ ఇన్ ఇండియా", "డిజిటల్ ఇండియా", "జల్ జీవన్ మిషన్", "ఆయుష్మాన్ భారత్"],
}


def assess_relevance(text: str, threshold: float = RELEVANCE_THRESHOLD) -> dict:
    folded = text.casefold()
    reasons: list[str] = []
    for language, terms in RELEVANCE_TERMS.items():
        for term in terms:
            if term.casefold() in folded:
                reasons.append(f"{language} Government of India indicator: {term}")
    reasons = list(dict.fromkeys(reasons))
    score = min(0.98, 0.35 + 0.22 * len(reasons)) if reasons else 0.08
    return {"is_relevant": score >= threshold, "score": round(score, 3), "reasons": reasons}
