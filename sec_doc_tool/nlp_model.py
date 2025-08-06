import spacy

_nlp_model = None


def get_nlp_model():
    """Lazy load SpaCy model"""
    global _nlp_model
    if _nlp_model is None:
        try:
            _nlp_model = spacy.load("en_core_web_lg")
        except OSError:
            # Fallback to smaller model if large one not available
            _nlp_model = spacy.load("en_core_web_sm")
    if _nlp_model:
        return _nlp_model
    raise ValueError("Failed to load SpaCy model")
