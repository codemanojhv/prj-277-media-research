from __future__ import annotations

import hashlib
import math
import re
from collections import Counter

from app.core.config import EMBEDDING_MODEL
from app.services.analysis import TOPIC_TERMS

CONCEPT_TERMS: dict[str, list[str]] = {
    "solar-energy": ["solar", "rooftop", "सौर", "सोलर", "ಸೌರ", "சூரிய", "సౌర"],
    "rural-water": ["water", "जल", "पानी", "ನೀರು", "ನೀರಿನ", "தண்ணீர்", "நீர்", "నీరు", "నీటి"],
    "digital-learning": ["school", "classroom", "कक्षा", "विद्यालय", "शिक्षा", "ಶಾಲೆ", "ತರಗತಿ", "வகுப்பறை", "பள்ளி", "கல்வி", "తరగతి", "పాఠశాల", "విద్య"],
    "public-health": ["clinic", "health", "स्वास्थ्य", "ಆರೋಗ್ಯ", "சுகாதாரம்", "சுகாதார", "ఆరోగ్యం", "ఆరోగ్య"],
    "farm-services": ["farm", "agriculture", "कृषि", "விவசாயம்", "விவசாய", "ಕೃಷಿ", "వ్యవసాయం", "వ్యవసాయ"],
    "road-safety": ["highway", "road", "सड़क", "ರಸ್ತೆ", "சாலை", "రోడ్డు", "రహదారి"],
    "clean-cooking": ["cooking", "stove", "रसोई", "ಅಡುಗೆ", "சமையல்", "వంట"],
    "public-digital-services": ["public digital", "online service", "सार्वजनिक डिजिटल सेवा", "ಸಾರ್ವಜನಿಕ ಡಿಜಿಟಲ್ ಸೇವೆ", "பொது டிஜிட்டல் சேவை", "ప్రజా డిజిటల్ సేవ"],
    "skills-employment": ["employment", "skills", "रोजगार", "कौशल", "ಉದ್ಯೋಗ", "திறன்", "ఉపాధి"],
    "public-budget": ["budget", "बजट", "வரவுசெலவு", "ಬಜೆಟ್", "బడ్జెట్"],
}
CONCEPT_LABELS = {
    "solar-energy": "solar rooftop electricity access",
    "rural-water": "rural drinking water supply service",
    "digital-learning": "school classroom digital learning connectivity",
    "public-health": "public clinic healthcare service access",
    "farm-services": "agriculture farm support service",
    "road-safety": "highway road traffic safety review",
    "clean-cooking": "clean cooking household energy access",
    "public-digital-services": "public digital government services",
    "skills-employment": "employment skills training service",
    "public-budget": "union government budget consultation economy",
}


def matched_concepts(text: str) -> list[str]:
    folded = text.casefold()
    return [concept for concept, terms in CONCEPT_TERMS.items() if any(term.casefold() in folded for term in terms)]


def enrich_for_embedding(text: str) -> str:
    concepts = matched_concepts(text)
    return f"{text} Semantic concepts: {' '.join(concepts)}" if concepts else text


def lexical_embedding(text: str, dimensions: int = 384) -> list[float]:
    """Small deterministic cross-script feature vector used when model assets are unavailable."""
    folded = text.casefold()
    features: Counter[str] = Counter()
    words = re.findall(r"[\w]+", folded, flags=re.UNICODE)
    features.update(f"word:{word}" for word in words if len(word) > 1)
    for token in words:
        for size in (2, 3, 4):
            features.update(f"char:{token[index:index + size]}" for index in range(max(0, len(token) - size + 1)))
    for concept, terms in CONCEPT_TERMS.items():
        if any(term.casefold() in folded for term in terms):
            features[f"concept:{concept}"] += 5
    for topic, terms in TOPIC_TERMS.items():
        if any(term.casefold() in folded for term in terms):
            features[f"topic:{topic}"] += 1
    vector = [0.0] * dimensions
    for feature, count in features.items():
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "little") % dimensions
        sign = 1.0 if digest[4] & 1 else -1.0
        vector[bucket] += sign * (1.0 + math.log(count))
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


class EmbeddingProvider:
    def __init__(self, model_name: str = EMBEDDING_MODEL):
        self.model_name = model_name
        self._model = None
        self._fallback = False

    def embed(self, texts: list[str]) -> tuple[list[list[float]], str]:
        if not texts:
            return [], self.model_name
        if not self._fallback:
            try:
                if self._model is None:
                    from fastembed import TextEmbedding

                    self._model = TextEmbedding(model_name=self.model_name)
                vectors = [[float(value) for value in vector] for vector in self._model.embed(texts)]
                concepts = [matched_concepts(text) for text in texts]
                concept_texts = [
                    "Research topic: " + "; ".join(CONCEPT_LABELS[key] for key in found) if found else "General news article"
                    for found in concepts
                ]
                concept_vectors = [[float(value) for value in vector] for vector in self._model.embed(concept_texts)]
                fused = []
                for vector, concept_vector, found in zip(vectors, concept_vectors, concepts, strict=True):
                    if not found:
                        fused.append(vector)
                        continue
                    mixed = [0.42 * article_value + 0.58 * concept_value for article_value, concept_value in zip(vector, concept_vector, strict=True)]
                    norm = math.sqrt(sum(value * value for value in mixed))
                    fused.append([value / norm for value in mixed] if norm else mixed)
                return fused, f"{self.model_name}+concept-fusion-v1"
            except Exception as exc:  # model download/runtime failures should not block article storage
                self._fallback = True
                self._model = None
                print(f"[EMBEDDING] multilingual model unavailable; using lexical fallback: {type(exc).__name__}: {exc}")
        return [lexical_embedding(text) for text in texts], "local-lexical-multilingual-fallback-v1"


def cosine(left: list[float], right: list[float]) -> float:
    if not left or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0
