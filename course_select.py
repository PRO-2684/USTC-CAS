from email.mime.text import MIMEText
from json import load
from smtplib import SMTP_SSL
from time import localtime, sleep, time

from jw import JW, CasClient

SLEEP_INTERVAL = 30  # Duration between each request of selected student count
REFRESH_INTERVAL = 10  # Iterations between each refresh of max student count of courses


def send(title, content, email_config):
    mail_from = email_config["username"]
    pwd = email_config["password"]
    mail_to = email_config["mail_to"]
    msg = MIMEText(content)
    msg["Subject"] = title
    msg["From"] = mail_from
    msg["To"] = mail_to
    ss = SMTP_SSL("smtp.qq.com")
    ss.login(mail_from, pwd)
    ss.sendmail(mail_from, mail_to, msg.as_string())
    ss.quit()


def format_lesson(lesson):
    return f"{lesson['course']['nameZh']} ({lesson['code']})"


def main_loop(config):
    jw = JW(CasClient(config["cas"]["username"], config["cas"]["password"]))
    jw.login()
    courses = jw.selectable_courses()

    desiredCodes = config["courses"]
    i = 0

    while True:
        try:
            data = jw._get_std_count(int(courses[code]["id"]) for code in desiredCodes)
        except RuntimeError:
            jw.login()
            continue

        t = localtime(time())
        print(f"[{t.tm_hour:02}:{t.tm_min:02}:{t.tm_sec:02}]")
        i = (i + 1) % REFRESH_INTERVAL
        if i == 0:
            print("  Refreshing courses...")
            courses = jw.selectable_courses()

        if len(desiredCodes) == 0:
            break

        for code in desiredCodes:
            lesson = courses[code]
            if data[str(lesson["id"])] < lesson["limitCount"]:
                s = f"{format_lesson(lesson)} now available! {data[str(lesson['id'])]} / {lesson['limitCount']}"
                print("  " + s)
                if jw.select_course(lesson["id"]):
                    send("Course select success!", s, config["email"])
                    desiredCodes.remove(lesson["code"])
                else:
                    send("Course select failed.", s, config["email"])
            else:
                print(f"  {format_lesson(lesson)} full.")

        sleep(SLEEP_INTERVAL)


if __name__ == "__main__":
    print("Course Select")
    with open("./config.json") as f:
        config = load(f)
    main_loop(config)

# Example of config.json
# {
#     "email": {
#         "username": "abc@example.com",
#         "password": "xxx",
#         "mail_to": "def@example.com"
#     },
#     "cas": {
#         "username": "PBxxxxxxxx",
#         "password": "xxx"
#     },
#     "courses": [
#         "MARX1501M.01"
#     ]
# }
