"""
SOLAPI SMS 발송 모듈
단건/다건 발송, 발송 로그 기록, 시뮬레이션 모드를 지원한다.
"""

import json
import os
import re
import logging
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
        config = json.load(f)
    _get_solapi_config(config)
    return config


def _get_log_path():
    """오늘 날짜 기준 SMS 로그 파일 경로를 반환한다."""
    base_dir = _base_dir()
    logs_dir = os.path.join(base_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    return os.path.join(logs_dir, f"sms_{today}.log")


def _setup_logger():
    """SMS 전용 파일 로거를 설정하고 반환한다."""
    logger = logging.getLogger("sms_sender")
    if not logger.handlers:
        handler = logging.FileHandler(_get_log_path(), encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%H:%M:%S"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _get_solapi_config(config):
    """신규 solapi 설정과 기존 ppurio 설정을 모두 지원한다."""
    legacy = config.get("ppurio", {}) if isinstance(config.get("ppurio"), dict) else {}
    solapi = config.setdefault("solapi", {})

    if not solapi.get("api_key"):
        solapi["api_key"] = legacy.get("api_key", "")
    if not solapi.get("api_secret"):
        solapi["api_secret"] = legacy.get("api_secret", "")
    if not solapi.get("sender_phone"):
        solapi["sender_phone"] = legacy.get("sender_phone", "")

    return solapi


def _load_solapi_sdk():
    """SOLAPI SDK 클래스를 지연 로드한다."""
    from solapi import SolapiMessageService
    from solapi.model import RequestMessage

    return SolapiMessageService, RequestMessage


def _safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_phone(phone):
    """
    전화번호에서 숫자만 추출해 정규화한다.
    '010-1234-5678' → '01012345678'

    Args:
        phone: 원본 전화번호 문자열

    Returns:
        숫자만 남긴 전화번호 문자열
    """
    return re.sub(r"[^0-9]", "", str(phone))


def _load_template(template_name, context):
    """
    templates/ 폴더의 문자 템플릿을 읽고 context 값으로 치환하여 반환한다.

    Args:
        template_name: 템플릿 파일명 (확장자 제외, 예: 'sms_confirm')
        context: 치환할 딕셔너리 {'name': '홍길동', 'meet_link': '...'}

    Returns:
        치환 완료된 문자열
    """
    tpl_path = os.path.join(_base_dir(), "templates", f"{template_name}.txt")
    with open(tpl_path, "r", encoding="utf-8") as f:
        content = f.read()
    for key, value in context.items():
        content = content.replace("{" + key + "}", str(value))
    return content


def test_connection():
    """
    SOLAPI SDK 로드 가능 여부와 필수 설정값을 점검한다.

    Returns:
        (성공 여부, 메시지)
    """
    config = _load_config()
    solapi = _get_solapi_config(config)

    api_key = solapi.get("api_key", "").strip()
    api_secret = solapi.get("api_secret", "").strip()
    sender = normalize_phone(solapi.get("sender_phone", ""))

    if not api_key or not api_secret or not sender:
        return False, "API Key, API Secret, 발신 번호를 모두 입력해 주세요."

    try:
        SolapiMessageService, _ = _load_solapi_sdk()
        SolapiMessageService(api_key=api_key, api_secret=api_secret)
        return True, "SDK 로드 및 자격 증명 형식 확인 완료"
    except ImportError:
        return False, "solapi 패키지가 설치되지 않았습니다. requirements 설치가 필요합니다."
    except Exception as e:
        return False, str(e)


def send_sms(to_phone, content, simulation=False):
    """
    SOLAPI로 문자 1건을 발송한다.
    설정이 비어 있거나 simulation=True이면 실제 발송 없이 로그만 기록한다.

    Args:
        to_phone: 수신 전화번호 (정규화 자동 처리)
        content: 발송할 문자 내용
        simulation: True이면 실제 API 호출 없이 시뮬레이션

    Returns:
        True (성공) / False (실패)
    """
    logger = _setup_logger()
    config = _load_config()
    phone = normalize_phone(to_phone)

    solapi = _get_solapi_config(config)
    api_key = solapi.get("api_key", "").strip()
    api_secret = solapi.get("api_secret", "").strip()
    sender = normalize_phone(solapi.get("sender_phone", ""))

    if not phone:
        logger.warning("[발송실패] 수신번호가 비어 있습니다.")
        return False

    # 설정 미완료 시 자동 시뮬레이션 모드
    if not api_key or not api_secret or not sender or simulation:
        logger.info(f"[시뮬레이션] TO:{phone} | {content[:30]}...")
        return True

    for attempt in range(2):  # 실패 시 1회 재시도
        try:
            SolapiMessageService, RequestMessage = _load_solapi_sdk()
            service = SolapiMessageService(api_key=api_key, api_secret=api_secret)
            message = RequestMessage(from_=sender, to=phone, text=content)
            response = service.send(message)

            group_info = getattr(response, "group_info", None)
            group_id = getattr(group_info, "group_id", "-")
            count = getattr(group_info, "count", None)
            success_count = _safe_int(getattr(count, "registered_success", 1))
            fail_count = _safe_int(getattr(count, "registered_failed", 0))

            if fail_count > 0 and success_count == 0:
                logger.warning(
                    f"[발송실패 {attempt+1}회] TO:{phone} | group_id:{group_id} | "
                    f"success:{success_count} fail:{fail_count}"
                )
                continue

            logger.info(f"[발송성공] TO:{phone} | group_id:{group_id} | {content[:30]}...")
            return True
        except ImportError:
            logger.error("[발송실패] solapi 패키지가 설치되지 않았습니다.")
            return False
        except Exception as e:
            logger.warning(f"[발송오류 {attempt+1}회] TO:{phone} | {e}")

    logger.error(f"[최종실패] TO:{phone} | 2회 시도 후 포기")
    return False


def send_bulk_sms(recipients, template_name, extra_context=None):
    """
    입금 완료된 접수자 전원에게 문자를 일괄 발송한다.

    Args:
        recipients: Airtable에서 가져온 접수자 딕셔너리 리스트
        template_name: templates/ 폴더의 템플릿 파일명 (확장자 제외)
        extra_context: 템플릿 치환에 추가로 넣을 딕셔너리 (예: meet_link)

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
        }
        if extra_context:
            context.update(extra_context)

        try:
            content = _load_template(template_name, context)
        except FileNotFoundError:
            content = f"[크리AI티브] {person.get('name', '')}님께 안내드립니다."

        phone = person.get("phone", "")
        if not phone:
            fail += 1
            continue

        ok = send_sms(phone, content)
        if ok:
            success += 1
        else:
            fail += 1

    return success, fail
