"""
Gmail SMTP 이메일 발송 모듈
HTML 이메일 단건/다건 발송, 발송 로그 기록을 지원한다.
"""

import json
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime


def _base_dir():
    """EXE 실행 시에는 exe 위치, 일반 실행 시에는 프로젝트 루트를 반환한다."""
    import sys
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_config():
    """config.json을 읽어 설정값을 반환한다."""
    config_path = os.path.join(_base_dir(), "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_log_path():
    """오늘 날짜 기준 이메일 로그 파일 경로를 반환한다."""
    base_dir = _base_dir()
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(logs_dir, f"email_{today}.log")


def _setup_logger():
    """이메일 전용 파일 로거를 설정하고 반환한다."""
    logger = logging.getLogger("email_sender")
    if not logger.handlers:
        handler = logging.FileHandler(_get_log_path(), encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _load_template(template_name, context):
    """
    templates/ 폴더의 HTML 이메일 템플릿을 읽고 context 값으로 치환하여 반환한다.

    Args:
        template_name: 템플릿 파일명 (확장자 제외, 예: 'email_confirm')
        context: 치환할 딕셔너리

    Returns:
        치환 완료된 HTML 문자열
    """
    tpl_path = os.path.join(_base_dir(), "templates", f"{template_name}.html")
    with open(tpl_path, "r", encoding="utf-8") as f:
        content = f.read()
    for key, value in context.items():
        content = content.replace("{" + key + "}", str(value))
    return content


def _get_subject(template_name, context):
    """
    템플릿 이름에 따른 이메일 제목을 반환하고 context 값으로 치환한다.

    Args:
        template_name: 템플릿 파일명 (확장자 제외)
        context: 치환할 딕셔너리

    Returns:
        이메일 제목 문자열
    """
    subjects = {
        "email_confirm":   "[크리AI티브] {name}님, 입금이 확인되었습니다",
        "email_link":      "[크리AI티브] 내일 웨비나 Google Meet 링크 안내",
        "email_feedback":  "[크리AI티브] 오늘 웨비나 어떠셨나요? 피드백 부탁드립니다",
    }
    subject = subjects.get(template_name, "[크리AI티브] 안내")
    for key, value in context.items():
        subject = subject.replace("{" + key + "}", str(value))
    return subject


def send_email(to_email, subject, html_body, simulation=False):
    """
    Gmail SMTP로 HTML 이메일 1건을 발송한다.
    설정 미완료 시 simulation=True로 동작한다.

    Args:
        to_email: 수신 이메일 주소
        subject: 이메일 제목
        html_body: HTML 형식의 본문
        simulation: True이면 실제 발송 없이 로그만 기록

    Returns:
        True (성공) / False (실패)
    """
    logger = _setup_logger()
    config = _load_config()
    sender_email = config["gmail"]["sender_email"]
    app_password = config["gmail"]["app_password"]

    if not sender_email or not app_password or simulation:
        logger.info(f"[시뮬레이션] TO:{to_email} | 제목: {subject}")
        return True

    msg = MIMEMultipart("alternative")
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(sender_email, app_password)
            smtp.sendmail(sender_email, to_email, msg.as_string())
        logger.info(f"[발송성공] TO:{to_email} | 제목: {subject}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(f"[인증실패] Gmail 앱 비밀번호를 확인하세요. TO:{to_email}")
        return False
    except Exception as e:
        logger.error(f"[발송실패] TO:{to_email} | {e}")
        return False


def send_bulk_email(recipients, template_name, extra_context=None):
    """
    접수자 전원에게 HTML 이메일을 일괄 발송한다.

    Args:
        recipients: Airtable에서 가져온 접수자 딕셔너리 리스트
        template_name: templates/ 폴더의 템플릿 파일명 (확장자 제외)
        extra_context: 템플릿 치환에 추가로 넣을 딕셔너리

    Returns:
        (성공 건수, 실패 건수) 튜플
    """
    config = _load_config()
    webinar = config["webinar"]

    success = 0
    fail = 0

    for person in recipients:
        context = {
            "name": person.get("name", ""),
            "meet_link": webinar.get("meet_link", ""),
            "feedback_link": webinar.get("feedback_link", ""),
            "webinar_date": webinar.get("date", ""),
            "webinar_time": webinar.get("time", ""),
            "webinar_title": webinar.get("title", "크리AI티브 웨비나"),
        }
        if extra_context:
            context.update(extra_context)

        to_email = person.get("email", "")
        if not to_email:
            fail += 1
            continue

        try:
            html_body = _load_template(template_name, context)
        except FileNotFoundError:
            html_body = f"<p>{person.get('name', '')}님께 안내드립니다.</p>"

        subject = _get_subject(template_name, context)
        ok = send_email(to_email, subject, html_body)
        if ok:
            success += 1
        else:
            fail += 1

    return success, fail


def test_connection():
    """
    Gmail SMTP 연결을 테스트한다. 실제 메일은 발송하지 않는다.

    Returns:
        (성공 여부: bool, 메시지: str)
    """
    config = _load_config()
    sender_email = config["gmail"]["sender_email"]
    app_password = config["gmail"]["app_password"]

    if not sender_email or not app_password:
        return False, "Gmail 주소 또는 앱 비밀번호가 설정되지 않았습니다."

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(sender_email, app_password)
        return True, "Gmail SMTP 연결 성공"
    except smtplib.SMTPAuthenticationError:
        return False, "인증 실패: Gmail 앱 비밀번호를 확인하세요. (2FA 활성화 및 앱 비밀번호 생성 필요)"
    except Exception as e:
        return False, f"연결 실패: {str(e)}"
