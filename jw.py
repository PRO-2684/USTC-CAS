from CAS import CasClient
from re import search


class JW:
    def __init__(self, cas: CasClient, debug: bool = False) -> None:
        self.cas = cas
        self.stu_id = -1
        self.turn = -1
        self.session = self.cas.session
        self.session.headers.update(
            {
                "sec-ch-ua": '"Not/A)Brand";v="99", "Microsoft Edge";v="115", "Chromium";v="115"',
                "DNT": "1",
                "sec-ch-ua-mobile": "?0",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.183",
                "X-Requested-With": "XMLHttpRequest",
                "sec-ch-ua-platform": '"Windows"',
                "Origin": "https://jw.ustc.edu.cn",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Accept": "*/*",
                "Accept-Encoding": "gzip, deflate, br",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            }
        )
        self.debug = debug
        if self.debug:
            self.session.proxies.update(
                {"http": "http://localhost:8888", "https": "http://localhost:8888"}
            )  # DEBUG

    def login(self):
        """Login to CAS and Education Administration System."""
        assert self.cas.login()
        assert self.cas.service("https://jw.ustc.edu.cn/ucas-sso/login")
        self.stu_id = self._get_stu_id()
        self.turn = self._get_turn()
        self.session.headers.update(
            {
                "Referer": f"https://jw.ustc.edu.cn/for-std/course-select/{self.stu_id}/turn/{self.turn}/select"
            }
        )
        if self.debug:
            print(f"stu_id: {self.stu_id}, turn: {self.turn}")

    def selectable_courses(self):
        """Get all selectable courses of current semester, returns {code: {info}}."""
        r = self.session.post(
            "https://jw.ustc.edu.cn/ws/for-std/course-select/addable-lessons",
            allow_redirects=False,
            verify=(not self.debug),
            data={"turnId": self.turn, "studentId": self.stu_id},
        )
        data = {item["code"]: item for item in r.json()}
        return data

    def _get_stu_id(self):
        """Get student id."""
        r = self.session.get(
            "https://jw.ustc.edu.cn/for-std/course-select",
            allow_redirects=False,
            verify=(not self.debug),
        )
        location = r.headers["Location"]
        stu_id = int(location.removesuffix("/").split("/")[-1])
        return stu_id

    def _get_turn(self):
        """Get turn id."""
        r = self.session.post(
            "https://jw.ustc.edu.cn/ws/for-std/course-select/open-turns",
            data={
                "studentId": self.stu_id,
                "bizTypeId": 2,
            },
            verify=(not self.debug),
        )
        if r.status_code == 302:
            raise RuntimeError("Not logged in.")
        data = r.json()
        if len(data) == 0:
            return -1
        return data[0]["id"]

    def get_course_table(self, semester: int, dataId: int):
        """Get course table of given semester id. dataId can be found in the url of course table page."""
        r = self.session.get(
            f"https://jw.ustc.edu.cn/for-std/course-table/get-data?bizTypeId=2&semesterId={semester}&dataId={dataId}",
            allow_redirects=False,
            verify=(not self.debug),
        )
        if r.status_code == 302:
            raise RuntimeError("Not logged in.")
        data = r.json()
        return {
            "currentWeek": data["currentWeek"],
            "lessons": [
                {
                    "code": lesson["code"],
                    "name": lesson["course"]["nameZh"],
                    "weeks": lesson["suggestScheduleWeeks"],
                    "time_and_classroom": lesson["scheduleText"]["dateTimePlaceText"][
                        "textZh"
                    ],
                    "teachers": [
                        {
                            "name": teacher["person"]["nameZh"],
                            "age": teacher["age"],
                        }
                        for teacher in lesson["teacherAssignmentList"]
                    ],
                    "textbook": lesson["textbook"],
                }
                for lesson in data["lessons"]
            ],
        }

    def current_course_table(self):
        """Get current course table."""
        r = self.session.get(
            "https://jw.ustc.edu.cn/for-std/course-table",
            allow_redirects=True,
            verify=(not self.debug),
        )
        if r.status_code != 200:
            raise RuntimeError("Expected status code 200, but got {r.status_code}.")
        dataId = int(r.url.split("/")[-1])
        semester = search(r'<option selected="selected" value="(\d+)">', r.text).group(
            1
        )
        return self.get_course_table(semester, dataId)

    def _get_std_count(self, lesson_ids: list[int]):
        """Get student count of given course (when in course selection period)"""
        r = self.session.post(
            f"https://jw.ustc.edu.cn/ws/for-std/course-select/std-count",
            data=[("lessonIds[]", lesson_id) for lesson_id in lesson_ids],
            verify=(not self.debug),
        )
        if r.status_code == 302:
            raise RuntimeError("Not logged in.")
        data = r.json()
        return data

    def select_course(self, lesson_id: int):
        """Select a course by its id."""
        r = self.session.post(
            f"https://jw.ustc.edu.cn/ws/for-std/course-select/add-request",
            data={
                "studentAssoc": self.stu_id,
                "lessonAssoc": lesson_id,
                "courseSelectTurnAssoc": self.turn,
                "scheduleGroupAssoc": "",
                "virtualCost": 0,
            },
            verify=(not self.debug),
        )
        if r.status_code != 200:
            print(r.text)
            raise RuntimeError("Failed to select course.")
        req_id = r.text
        print("req_id:", req_id)
        r = self.session.post(
            "https://jw.ustc.edu.cn/ws/for-std/course-select/add-drop-response",
            data={
                "studentId": self.stu_id,
                "requestId": req_id,
            },
            verify=(not self.debug),
        )
        if r.status_code != 200:
            raise RuntimeError("Failed to select course.")
        data = r.json()
        print(data)
        success = data["success"]
        if success:
            s = f"Successfully selected course {lesson_id}."
        else:
            s = f"Failed to select course {lesson_id}: {data['errorMessage']['text']}"
        print(s)
        return success
