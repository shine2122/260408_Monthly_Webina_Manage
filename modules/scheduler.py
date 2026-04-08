"""
예약 발송 스케줄러
백그라운드 스레드로 동작하며 웨비나 링크·피드백 링크를 자동 발송한다.
GUI 실행 중일 때만 동작하고, 이미 발송된 경우 중복 발송하지 않는다.
"""

import json
import os
import threading
import logging
from datetime import datetime, date, timedelta

import schedule
import time


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
    """오늘 날짜 기준 스케줄러 로그 파일 경로를 반환한다."""
    base_dir = _base_dir()
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(logs_dir, f"scheduler_{today}.log")


def _setup_logger():
    """스케줄러 전용 파일 로거를 설정하고 반환한다."""
    logger = logging.getLogger("scheduler")
    if not logger.handlers:
        handler = logging.FileHandler(_get_log_path(), encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _get_webinar_date():
    """config.json의 웨비나 날짜를 date 객체로 반환한다."""
    config = _load_config()
    date_str = config["webinar"]["date"]
    return datetime.strptime(date_str, "%Y-%m-%d").date()


# ── 로그 콜백 (GUI에서 등록) ──────────────────────────────
_log_callback = None

def set_log_callback(callback):
    """
    GUI 로그 창에 메시지를 출력하는 콜백 함수를 등록한다.

    Args:
        callback: 문자열 하나를 받는 함수
    """
    global _log_callback
    _log_callback = callback


def _log(msg):
    """로거와 GUI 콜백 양쪽에 메시지를 기록한다."""
    _setup_logger().info(msg)
    if _log_callback:
        _log_callback(msg)


# ── 자동 발송 작업 ────────────────────────────────────────

def _job_send_webinar_link():
    """
    D-1 오전 10시 실행: 내일이 웨비나인지 확인하고 링크를 자동 발송한다.
    이미 링크발송완료인 접수자는 제외한다.
    """
    from modules import airtable_client, email_sender, sms_sender

    try:
        webinar_date = _get_webinar_date()
        tomorrow = date.today() + timedelta(days=1)

        if webinar_date != tomorrow:
            return  # 내일 웨비나가 아님

        _log("[스케줄러] D-1 웨비나 링크 발송 시작")

        # 링크 미발송자: 발송상태가 '확인발송완료' 인 사람만 대상
        recipients = airtable_client.get_paid_registrants()
        targets = [r for r in recipients if r["send_status"] == "확인발송완료"]

        if not targets:
            _log("[스케줄러] 링크 발송 대상 없음 (이미 모두 발송됨)")
            return

        e_ok, e_fail = email_sender.send_bulk_email(targets, "email_link")
        s_ok, s_fail = sms_sender.send_bulk_sms(targets, "sms_link")

        for person in targets:
            airtable_client.update_send_status(person["record_id"], "링크발송완료")

        _log(f"[스케줄러] 링크 발송 완료 — 이메일 {e_ok}건 성공/{e_fail}건 실패, 문자 {s_ok}건 성공/{s_fail}건 실패")

    except Exception as e:
        _log(f"[스케줄러 오류] 링크 발송 중 예외 발생: {e}")


def _job_send_feedback():
    """
    웨비나 당일 22:10 실행: 오늘이 웨비나인지 확인하고 피드백 링크를 자동 발송한다.
    이미 피드백 발송 완료인 접수자는 제외한다.
    """
    from modules import airtable_client, email_sender, sms_sender

    try:
        webinar_date = _get_webinar_date()

        if webinar_date != date.today():
            return  # 오늘 웨비나가 아님

        _log("[스케줄러] 피드백 링크 발송 시작")

        recipients = airtable_client.get_paid_registrants()
        targets = [r for r in recipients if r["send_status"] == "링크발송완료"]

        if not targets:
            _log("[스케줄러] 피드백 발송 대상 없음 (이미 모두 발송됨)")
            return

        e_ok, e_fail = email_sender.send_bulk_email(targets, "email_feedback")
        s_ok, s_fail = sms_sender.send_bulk_sms(targets, "sms_feedback")

        for person in targets:
            airtable_client.update_send_status(person["record_id"], "피드백발송완료")

        _log(f"[스케줄러] 피드백 발송 완료 — 이메일 {e_ok}건 성공/{e_fail}건 실패, 문자 {s_ok}건 성공/{s_fail}건 실패")

    except Exception as e:
        _log(f"[스케줄러 오류] 피드백 발송 중 예외 발생: {e}")


# ── 스케줄러 시작 ─────────────────────────────────────────

_scheduler_thread = None
_stop_event = threading.Event()


def _run_scheduler():
    """스케줄러 루프를 실행한다. 별도 스레드에서 동작한다."""
    schedule.every().day.at("09:55").do(_job_send_webinar_link)
    schedule.every().day.at("22:10").do(_job_send_feedback)

    _log("[스케줄러] 시작됨 — D-1 09:55 링크 발송 / 당일 22:10 피드백 발송 예약")

    while not _stop_event.is_set():
        schedule.run_pending()
        time.sleep(30)


def start():
    """
    스케줄러 백그라운드 스레드를 시작한다.
    GUI 실행 직후 한 번만 호출한다.
    """
    global _scheduler_thread
    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    _stop_event.clear()
    _scheduler_thread = threading.Thread(target=_run_scheduler, daemon=True)
    _scheduler_thread.start()


def stop():
    """스케줄러 스레드를 종료한다. GUI 종료 시 호출한다."""
    _stop_event.set()
