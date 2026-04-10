"""
가상 테스트 데이터 26명을 Airtable 웨비나접수_통합 테이블에 삽입한다.
실행: python seed_test_data.py
"""

import json
import os
import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
TABLE_NAME = "웨비나접수_통합"

PEOPLE = [
    ("김지원", "클레어",   "claire.kim@gmail.com",    "010-1234-5678", "초보자",   True),
    ("이수민", "민트",     "mint.lee@gmail.com",      "010-2345-6789", "입문자",   True),
    ("박서연", "해랑",     "harang.park@gmail.com",   "010-3456-7890", "중급자",   True),
    ("최민준", "준이",     "juni.choi@gmail.com",     "010-4567-8901", "초보자",   True),
    ("정유진", "유진",     "yujin.jung@gmail.com",    "010-5678-9012", "초보자",   True),
    ("강도현", "도현",     "dohyun.kang@gmail.com",   "010-6789-0123", "입문자",   True),
    ("윤아름", "아름",     "areum.yoon@gmail.com",    "010-7890-1234", "중급자",   True),
    ("임채원", "찬란히",   "chanrani.lim@gmail.com",  "010-8901-2345", "초보자",   True),
    ("한지은", "지은",     "jieun.han@gmail.com",     "010-9012-3456", "입문자",   True),
    ("오승현", "승현",     "seunghyun.oh@gmail.com",  "010-0123-4567", "중급자",   True),
    ("신예린", "예린",     "yerin.shin@gmail.com",    "010-1357-2468", "초보자",   True),
    ("류민서", "민서",     "minseo.ryu@gmail.com",    "010-2468-3579", "입문자",   True),
    ("조현우", "현우",     "hyunwoo.jo@gmail.com",    "010-3579-4680", "중급자",   True),
    ("권나영", "나영",     "nayoung.kwon@gmail.com",  "010-4680-5791", "초보자",   True),
    ("황지훈", "지훈",     "jihoon.hwang@gmail.com",  "010-5791-6802", "입문자",   True),
    ("안소희", "소희",     "sohee.ahn@gmail.com",     "010-6802-7913", "초보자",   True),
    ("배준호", "준호",     "junho.bae@gmail.com",     "010-7913-8024", "중급자",   True),
    ("전미래", "미래",     "mirae.jeon@gmail.com",    "010-8024-9135", "초보자",   True),
    ("남기태", "기태",     "gitae.nam@gmail.com",     "010-9135-0246", "입문자",   True),
    ("문수빈", "수빈",     "subin.moon@gmail.com",    "010-0246-1357", "중급자",   True),
    ("양현진", "현진",     "hyunjin.yang@gmail.com",  "010-1122-3344", "초보자",   False),
    ("송지민", "지민",     "jimin.song@gmail.com",    "010-2233-4455", "입문자",   False),
    ("고은지", "은지",     "eunji.ko@gmail.com",      "010-3344-5566", "초보자",   False),
    ("서태양", "태양",     "taeyang.seo@gmail.com",   "010-4455-6677", "중급자",   False),
    ("이하늘", "하늘",     "haneul.lee@gmail.com",    "010-5566-7788", "입문자",   False),
    ("박다은", "다은",     "daeun.park@gmail.com",    "010-6677-8899", "초보자",   False),
]

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def insert_records(config, records):
    api_key = config["airtable"]["api_key"]
    base_id = config["airtable"]["base_id"]
    month   = config["airtable"].get("current_month", "4월")
    url = f"https://api.airtable.com/v0/{base_id}/{requests.utils.quote(TABLE_NAME)}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    batch = [
        {
            "fields": {
                "기준월":       month,
                "성함":         name,
                "활동명":       nickname,
                "이메일":       email,
                "휴대폰번호":   phone,
                "수준":         level,
                "개인정보동의": "예",
                "입금완료":     paid,
                "발송상태":     "미발송",
            }
        }
        for name, nickname, email, phone, level, paid in records
    ]

    inserted = 0
    for i in range(0, len(batch), 10):
        chunk = batch[i:i+10]
        res = requests.post(url, headers=headers, json={"records": chunk}, timeout=15)
        if res.status_code in (200, 201):
            inserted += len(res.json().get("records", []))
            print(f"  {inserted}명 삽입 완료...")
        else:
            print(f"  [오류] {res.status_code}: {res.text[:120]}")
    return inserted

if __name__ == "__main__":
    config = load_config()
    print(f"Airtable Base: {config['airtable']['base_id']}")
    print(f"기준월: {config['airtable'].get('current_month', '4월')}")
    print(f"총 {len(PEOPLE)}명 삽입 시작...\n")
    total = insert_records(config, PEOPLE)
    print(f"\n완료: 총 {total}명 삽입")
    print("입금완료: 20명 / 미입금: 6명")
