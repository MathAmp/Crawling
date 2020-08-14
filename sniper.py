from time import sleep
from crawler import course_no_to_records
from crawler import get_multipage_info_in_dict
from crawler import union_course_page_no
from crawler import convert_course_no_to_page_no
import emailer
from configurations import target_courses
from time import time
from crawler import timer


def course_identifier(subject_id, course_no):
    return subject_id, course_no


initial_registrant_counts = {}


def target_courses_to_course_id_list(target_course_dict: dict):
    return sum([[course_identifier(subject_id, course_no) for course_no in course_no_list]
                for subject_id, course_no_list in target_course_dict.items()], list())


def target_courses_to_course_loc_list(target_course_dict: dict):
    return sum([union_course_page_no(subject_id, course_no_list)
                for subject_id, course_no_list in target_course_dict.items()], list())


def run():
    time_list = list()
    course_loc_list = target_courses_to_course_loc_list(target_courses)
    for i in range(10000):
        print(f"{i + 1} / {10000}")
        time_list.append(single_run(course_loc_list))
    return time_list


@timer
def single_run(course_loc_list):
    # download course
    course_loc_text_dict = get_multipage_info_in_dict(course_loc_list)

    # analysis
    for subject_id in target_courses:
        print(f"{subject_id} 확인중")
        # 모든 강좌번호에 대해 검색해서 결과 저장하기
        course_nos = target_courses[subject_id]
        # print(course_nos)
        records = course_no_to_records(subject_id, course_nos, course_loc_text_dict)
        # print(records)

        for record in records:
            course_id = course_identifier(subject_id, record['강좌번호'])
            registrant_count = int(record['수강신청인원'])
            # 첫 검색인 경우, 수강신청인원을 기록한다.
            if course_id not in initial_registrant_counts:
                initial_registrant_counts[course_id] = registrant_count
            else:
                if registrant_count < initial_registrant_counts[course_id]:
                    emailer.send(f"{subject_id} 빈자리 알림",
                                 f"{subject_id}의 {record['강좌번호']} 분반에 자리가 확인되었습니다.\n\n"
                                 f">> sugang.snu.ac.kr")
                    print('Message Sent!')
                    initial_registrant_counts[course_id] = registrant_count
    print(initial_registrant_counts)
