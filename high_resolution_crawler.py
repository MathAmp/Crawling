import time
import re
import asyncio
import requests
import aiohttp

master_regex = r'<.*>\s*(?P<정원>\d+)\s*\((?P<재학생>\d+)\)\s*<.*>\s*' \
               r'<.*>\s*(?P<수강신청인원>\d+)\s*<.*>'
url = 'http://sugang.snu.ac.kr/sugang/cc/cc100.action'

course = {'srchSbjtCd': '033.019', 'workType': 'S'}


async def _search_course(course_info_dict: dict):
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=course_info_dict) as search_request:
            return await search_request.text()


async def _get_regex_info_in_html_text(html_text, regex_expression):
    pattern = re.compile(regex_expression)
    return pattern.findall(html_text)


async def _request_course_info(course_info_dict, regex_expression=master_regex):
    html_text = await _search_course(course_info_dict)
    find = await _get_regex_info_in_html_text(html_text, regex_expression)
    print(find)
    print(time.time())


async def _main(course_info_dict):
    await asyncio.gather(*[_request_course_info(course_info_dict) for _ in range(100)])


def make_info_dict(subject_id, subject_name=None, professor_name=None):
    return {'srchSbjtCd': subject_id, 'workType': 'S'}


def request(course_info_dict=None, n=1):
    if course_info_dict is None:
        course_info_dict = course
    for i in range(n):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(_main(course_info_dict))