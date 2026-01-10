from concurrent.futures import ThreadPoolExecutor, as_completed
from .caching import save_to_cache, get_from_cache, check_caching
from .crawler import find_max_page
from .extract import fetch_discussion_links, fetch_discussion
from .filter import filter_exam_links

def get_questions(exam_provider, exam_code, caching=True):

    if caching:
        yield {"type": "stage", "stage": "⌛ Looking for cached questions...", "message": ""}
        caching_level = check_caching(exam_provider, exam_code)

    
    yield {"type": "stage", "stage": "⌛ Finding discussion pages...", "message": ""}
    
    max_discussion_page = find_max_page(exam_provider)

    discussion_links = []

    yield {"type": "stage", "stage": "⌛ Crawling discussion links...", "message": "", "total": max_discussion_page+1 }

    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = [executor.submit(fetch_discussion_links, i) for i in range(1, max_discussion_page+1)]
        i = 1
        for future in as_completed(futures):
            discussion_links.extend(future.result())
            yield {"type": "progress", "stage": "⌛ Crawling discussion links..", "current": i, "total": max_discussion_page+1, "message": f"{i}/{max_discussion_page+1}"}
            i+=1

    yield {"type": "stage", "stage": "⌛ Filtering your exam questions links...","message": ""}

    exam_links = filter_exam_links(exam_code, discussion_links)

    exam_question_length = len(exam_links)

    yield {"type": "stage", "stage": "⌛ Scrapping your exam questions...", "message": "", "total": exam_question_length+1 }

    exam_questions = []
    i = 1

    with ThreadPoolExecutor(max_workers=7) as executor:
        futures = {executor.submit(fetch_discussion, link): link for link in exam_links}
        
        for future in as_completed(futures):
            yield {"type": "progress", "stage": "⌛ Scrapping your exam questions...", "current": i, "total": max_discussion_page+1, "message": f"{i}/{exam_question_length+1}"}
            exam_questions.append(future.result())
            i += 1

    yield {
        "type": "done",
        "questions": exam_questions
    }