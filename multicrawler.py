import asyncio
import aiohttp
from time import time
from concurrent.futures import ThreadPoolExecutor
from Tool import url

max_concurrent_search_unit = 120
html_info_request_timeout_limit = 2


async def _concurrent_search(subject_id, page_no):
    search_info = {'srchSbjtCd': subject_id, 'workType': 'S', 'pageNo': page_no}
    connector = aiohttp.TCPConnector(limit_per_host=max_concurrent_search_unit, force_close=True, use_dns_cache=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        text = None
        try:
            async with session.post(url, data=search_info, timeout=html_info_request_timeout_limit) as async_req:
                text = await async_req.text()
                async_req.close()
                await session.close()
        except asyncio.exceptions.TimeoutError:
            print(f"{subject_id}, {page_no} Time out")
        except aiohttp.client_exceptions.ClientPayloadError:
            print("ERROR")
        except aiohttp.client_exceptions.ClientConnectorError:
            print("Internet Disconnected")
        finally:
            return text, subject_id, page_no


async def _gather_concurrent_search(partial_course_loc_list):
    async_req_list = [asyncio.ensure_future(_concurrent_search(subject_id, page_no))
                      for subject_id, page_no in partial_course_loc_list]
    await asyncio.gather(*async_req_list, return_exceptions=True)
    return async_req_list


def request_concurrent_search(partial_course_loc_list):
    loop = asyncio.SelectorEventLoop()
    executor = ThreadPoolExecutor()
    loop.set_default_executor(executor)
    asyncio.set_event_loop(loop)
    ret = [req.result() for req in loop.run_until_complete(_gather_concurrent_search(partial_course_loc_list))]
    executor.shutdown(wait=True)
    loop.close()
    return ret


def get_multipage_info_in_list(course_loc_list):
    return sum([request_concurrent_search(course_loc_list[partial_index: partial_index + max_concurrent_search_unit])
                for partial_index in range(0, len(course_loc_list), max_concurrent_search_unit)], list())


def get_multipage_info_in_dict(course_loc_list):
    return {(course_id, page_no): text for text, course_id, page_no
            in get_multipage_info_in_list(course_loc_list)}
