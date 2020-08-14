import requests
import requests_async
from pprint import pprint
import re
import asyncio
import aiohttp
from time import time
from time import sleep

records_per_page = 10
max_concurrent_search_unit = 25
html_info_request_timeout_limit = 2
bait_regex = r'\d+ \(\d+\)'  # 정원 (재학생)
record_start = '<tr'
record_end = '</tr>'
search_result_count_regex = r'검색건수\s*<span.*>(\d+)</span>\s*건'

fields = ['교과구분', '개설대학', '개설학과', '이수과정', '학년', '교과목번호', '강좌번호', '교과목명',
          '학점-강의-실습', '수업교시', '수업형태', '강의실', '주담당교수', '강의계획서', '정원(재학생)',
          '수강신청인원', '비고']

url = 'http://sugang.snu.ac.kr/sugang/cc/cc100.action'


def timer(func):

    def wrapper(*args, **kwargs):
        start = time()
        func(*args, **kwargs)
        end = time()
        print(f"{func.__name__} is executed in {end - start}s")
        return end - start

    return wrapper


def search(subject_id, page_no):
    search_info = {'srchSbjtCd': subject_id, 'workType': 'S', 'pageNo': page_no}
    with requests.Session() as session:
        req = session.post(url, search_info)
    return req.text


def wait_until_url_connect():
    while True:
        if search('', '1'):
            return
        else:
            sleep(1)


async def _concurrent_search(subject_id, page_no):
    search_info = {'srchSbjtCd': subject_id, 'workType': 'S', 'pageNo': page_no}
    connector = aiohttp.TCPConnector(limit_per_host=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        try:
            async with session.post(url, data=search_info, timeout=html_info_request_timeout_limit) as async_req:
                text = await async_req.text()
                await session.close()
                async_req.close()
                return text, subject_id, page_no
        except asyncio.exceptions.TimeoutError:
            return None, subject_id, page_no
        except aiohttp.client_exceptions.ClientPayloadError:
            print("ERORR")
            return None, subject_id, page_no
        except aiohttp.client_exceptions.ClientConnectorError:
            print("Internet Disconnected")
            wait_until_url_connect()
            return None, subject_id, page_no


async def _gather_concurrent_search(partial_course_loc_list):
    async_req_list = [asyncio.ensure_future(_concurrent_search(subject_id, page_no))
                      for subject_id, page_no in partial_course_loc_list]
    await asyncio.gather(*async_req_list)
    return async_req_list


def request_concurrent_search(partial_course_loc_list):
    loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)
    ret = [req.result() for req in loop.run_until_complete(_gather_concurrent_search(partial_course_loc_list))]
    loop.close()
    del loop
    return ret


def get_multipage_info_in_list(course_loc_list):
    return sum([request_concurrent_search(course_loc_list[partial_index: partial_index + max_concurrent_search_unit])
                for partial_index in range(0, len(course_loc_list), max_concurrent_search_unit)], list())


def get_multipage_info_in_dict(course_loc_list):
    return {(course_id, page_no): text for text, course_id, page_no in get_multipage_info_in_list(course_loc_list)}


def multipage_search(subject_id):
    page_no_to_check = 1    # first page
    pages = [search(subject_id, page_no_to_check)]
    target_page_no = find_max_page(pages[0])
    pages += [text for text, subject_id, page_no
              in get_multipage_info_in_list([(subject_id, str(page_no)) for page_no in range(2, target_page_no + 1)])]
    return pages


def union_course_page_no(subject_id, course_no_list):
    return list(set([(subject_id, convert_course_no_to_page_no(course_no)) for course_no in course_no_list]))


def course_no_search(subject_id, course_nos):
    page_no_set = set()
    for course_no in course_nos:
        page_no_set.add(convert_course_no_to_page_no(course_no))

    pages = []
    for page_no in page_no_set:
        pages.append(search(subject_id, page_no))
    return '\n'.join(pages)


def find_max_page(html_text):
    pattern = re.compile(search_result_count_regex)
    pattern_matches = pattern.findall(html_text)
    assert len(pattern_matches) == 1
    record_count = int(pattern_matches[0])  # == last course number
    return convert_course_no_to_page_no(record_count)


def convert_course_no_to_page_no(course_no):
    return (int(course_no) + records_per_page - 1) // records_per_page


def bidirectional_search(text, start_pos):
    front = start_pos
    back = start_pos
    while text[front:front + len(record_start)] != record_start:
        front -= 1
    while text[back:back + len(record_end)] != record_end:
        back += 1
    back += len(record_end)
    return front, back


def extract_records(html_text):
    pattern = re.compile(bait_regex)
    bait_indexes = [m.start() for m in re.finditer(pattern, html_text)]

    record_ranges = []
    for bait_index in bait_indexes:
        record_ranges.append(bidirectional_search(html_text, bait_index))

    record_texts = []
    for record_range in record_ranges:
        record_texts.append(html_text[record_range[0]:record_range[1]])

    return record_texts


def tag_strip(text):
    buffer = []
    opened_tag_count = 0
    for char in text:
        if char == '<':
            opened_tag_count += 1
        elif char == '>':
            opened_tag_count -= 1
        else:
            if opened_tag_count == 0:
                buffer.append(char)
    return ''.join(buffer)


def parse_record(record_text):
    lines = [line.strip() for line in record_text.split('\n')]
    lines = lines[2:-1]  # <tr>와 </tr>, checkbox 제거
    lines = [tag_strip(line) for line in lines]
    assert len(lines) == len(fields)
    record_data = {}
    for field_name, data in zip(fields, lines):
        record_data[field_name] = data
    return record_data


def course_id_list_to_records(course_id_list, html_text_dict):
    return {course_id: parse_record(html_text_dict[convert_course_no_to_page_no(course_id)]) for course_id in course_id_list}


def course_no_to_records(subject_id, course_nos, course_loc_text_dict):
    all_records_dict = dict()   # dict: course_id -> record
    for course_no in course_nos:
        html_text = course_loc_text_dict[subject_id, convert_course_no_to_page_no(course_no)]
        if html_text:   # None if aiohttp request fail(timeout 3sec
            all_record_texts = extract_records(html_text)
            for record_text in all_record_texts:
                record = parse_record(record_text)
                all_records_dict[record['교과목번호'], int(record['강좌번호'])] = record
    return [all_records_dict[subject_id, int(course_no)] for course_no in course_nos
            if (subject_id, int(course_no)) in all_records_dict]


@timer
def main():
    target_subject_id = ''
    #target_course_nos = [3, 13, 23]
    #records = course_no_to_records(target_subject_id, target_course_nos)
    multipage_search(target_subject_id)

    #print(f"{len(records)} records found.")


if __name__ == '__main__':
    main()

