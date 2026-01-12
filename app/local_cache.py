from flask_caching import Cache

cache = Cache()


def questions_cache_key(provider, exam_code):
    return f"questions:{provider}:{exam_code}"