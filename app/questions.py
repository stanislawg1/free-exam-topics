from concurrent.futures import ThreadPoolExecutor, as_completed
from .caching import save_to_cache, get_from_cache, check_caching
from .crawler import find_max_page, crawl_discussion_links
from .extract import get_discussion
from .filter import filter_exam_links

### MAIN GENERATOR ###

def get_questions(exam_provider, exam_code, url, headers, caching=True): # getting from cache todo
    caching_level = -1
    discussion_links = None
    exam_links = None
    exam_questions = None

    if caching:
        cache_info = yield from cached_questions_stage(exam_provider, exam_code)
        caching_level = cache_info['level']

    if caching_level < 0:
        max_discussion_page = yield from discussion_pages_stage(url, headers,exam_provider)

        discussion_links = yield from crawl_discussion_links_stage(url, headers, exam_provider, max_discussion_page)

        if caching:
            save_to_cache("discussion_links", exam_provider, exam_code, discussion_links)

    if caching_level < 1:
        if not discussion_links:
            discussion_links = get_from_cache("discussion_links", exam_provider, exam_code)

        exam_links = yield from filter_exam_links_stage(exam_code, discussion_links)

        if caching:
            save_to_cache("exam_discussion_links", exam_provider, exam_code, exam_links)

    if caching_level < 2:
        if not exam_links:
            exam_links = get_from_cache("exam_discussion_links", exam_provider, exam_code)
        exam_questions = yield from scrap_exam_questions_stage(exam_links, headers)

        if caching:
            save_to_cache("exam_questions", exam_provider, exam_code, exam_questions)

    yield {"type": "done", "questions": exam_questions}

### HELPERS ###

def cached_questions_stage(exam_provider, exam_code):
    """Generator sprawdzający cache i yieldujący status"""
    yield {"type": "stage", "stage": "⌛ Looking for cached questions...", "message": ""}
    
    caching_level = check_caching(exam_provider, exam_code)
    
    if caching_level >= 0:
        yield {"type": "stage", "stage": "⚡ Loaded from cache", "message": ""}
        return {"cached": True, "level": caching_level}

    yield {"type": "stage", "stage": "🚫 Nothing found in cache", "message": "Scrapping will start soon."}
    return {"cached": False, "level": caching_level}

def discussion_pages_stage(url, headers, exam_provider):
    yield {"type": "stage", "stage": "⌛ Finding discussion pages...", "message": "It should take up to 2 minutes"}
    max_discussion_page = find_max_page(url, headers, exam_provider)
    return max_discussion_page

def crawl_discussion_links_stage(url, headers, exam_provider, max_discussion_page):
    yield {"type": "stage", "stage": "⌛ Crawling discussion links...", "message": "It should take up to 2 minutes", "total": max_discussion_page}

    discussion_links = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(crawl_discussion_links, url, headers, exam_provider, i) for i in range(1, max_discussion_page+1)]
        i = 1
        for future in as_completed(futures):
            discussion_links.extend(future.result())
            yield {"type": "progress",
                   "stage": "⌛ Crawling discussion links..",
                   "current": i,
                   "total": max_discussion_page+1,
                   "message": f"{i}/{max_discussion_page+1}"}
            i += 1
    return discussion_links

def filter_exam_links_stage(exam_code, discussion_links):
    yield {"type": "stage", "stage": "⌛ Filtering your exam questions links...", "message": ""}
    exam_links = filter_exam_links(exam_code, discussion_links)
    return exam_links

def scrap_exam_questions_stage(exam_links, headers):
    total = len(exam_links)
    yield {"type": "stage", "stage": "⌛ Scrapping your exam questions...", "message": "", "total": total}

    exam_questions = []
    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(get_discussion, link, headers): link for link in exam_links}
        i = 1
        for future in as_completed(futures):
            exam_questions.append(future.result())
            yield {"type": "progress",
                   "stage": "⌛ Scrapping your exam questions...",
                   "current": i,
                   "total": total,
                   "message": f"{i}/{total}"}
            i += 1
    return exam_questions