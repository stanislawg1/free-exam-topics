import json, os

def _get_path(type, exam_provider, exam_name):
    path = "cache"

    if type == "discussion_links":
        path = os.path.join(path, exam_provider, "discussion_links.json")
    elif type == "exam_discussion_links":
        path = os.path.join(path, exam_provider, exam_name, "exam_discussion_links.json") 
    elif type == "exam_questions":
        path = os.path.join(path, exam_provider, exam_name, "questions.json")
    elif type == "providers":
        path = os.path.join(path, "providers.json")
    elif type == "providers_exams":
        path = os.path.join(path, exam_provider, "providers_exams.json")

    return path

def get_from_cache(type, exam_provider, exam_name):
    try:
        path = _get_path(type, exam_provider, exam_name)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        return data
    except FileNotFoundError:
        return None

def save_to_cache(type, exam_provider, exam_name, data):
    path = _get_path(type, exam_provider, exam_name)
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def check_caching(exam_provider, exam_name): 
    # checks the caching level (how deep we need to scrap -1 -> lowest (everything has to be scrapped) ; 4 -> highest (nothing has to be scrapped))
    caching_level = -1
    types = {
        "discussion_links": 0,
        "exam_discussion_links": 1, 
        "exam_questions": 2
    }

    for type_, level in types.items():
        path = _get_path(type_, exam_provider, exam_name)
        if os.path.isfile(path):
            caching_level = level

    return caching_level