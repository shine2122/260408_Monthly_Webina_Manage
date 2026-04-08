"""
Airtable API 연동 모듈
통합 접수 테이블(웨비나접수_통합)을 기준으로 조회/집계/이관을 담당한다.
"""

import json
import os
from collections import defaultdict
from datetime import datetime

import requests


REGISTRATION_TABLE = "웨비나접수_통합"
SUMMARY_TABLE = "웨비나_월별집계"
FEEDBACK_TABLE = "웨비나_피드백"
SUMMARY_LINK_FIELD = "웨비나_월별집계"
MONTH_SELECT_CHOICES = [{"name": f"{month}월"} for month in range(1, 13)]


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

    airtable_cfg = config.setdefault("airtable", {})
    fields = airtable_cfg.setdefault("fields", {})
    fields.setdefault("name", "성함")
    fields.setdefault("nickname", "활동명")
    fields.setdefault("email", "이메일")
    fields.setdefault("phone", "휴대폰번호")
    fields.setdefault("level", "수준")
    fields.setdefault("privacy_agree", "개인정보동의")
    fields.setdefault("paid", "입금완료")
    fields.setdefault("send_status", "발송상태")
    fields.setdefault("month", "기준월")
    fields.setdefault("webinar_link", SUMMARY_LINK_FIELD)

    current_month = airtable_cfg.get("current_month", "").strip()
    if not current_month:
        current_month = _derive_month_label(config)
        airtable_cfg["current_month"] = current_month
    airtable_cfg.setdefault("current_webinar_record_id", "")

    table_name = airtable_cfg.get("table_name", "").strip()
    if not table_name or table_name.endswith("월_웨비나접수"):
        airtable_cfg["table_name"] = REGISTRATION_TABLE

    return config


def _save_config(config):
    config_path = os.path.join(_base_dir(), "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _derive_month_label(config):
    webinar_date = config.get("webinar", {}).get("date", "").strip()
    if webinar_date:
        try:
            month = datetime.strptime(webinar_date, "%Y-%m-%d").month
            return f"{month}월"
        except ValueError:
            pass
    return f"{datetime.now().month}월"


def _sort_month_labels(labels):
    def _month_num(label):
        prefix = str(label).strip().replace("월", "")
        return int(prefix) if prefix.isdigit() else 0

    return sorted(labels, key=_month_num)


def _get_headers(config):
    return {
        "Authorization": f"Bearer {config['airtable']['api_key']}",
        "Content-Type": "application/json",
    }


def _get_table_url(config, table_name):
    base_id = config["airtable"]["base_id"]
    return f"https://api.airtable.com/v0/{base_id}/{requests.utils.quote(table_name)}"


def _get_registration_url(config):
    return _get_table_url(config, REGISTRATION_TABLE)


def _fetch_table_metadata(config):
    url = f"https://api.airtable.com/v0/meta/bases/{config['airtable']['base_id']}/tables"
    response = requests.get(url, headers=_get_headers(config), timeout=15)
    response.raise_for_status()
    return response.json().get("tables", [])


def _find_table_metadata(config, table_name):
    for table in _fetch_table_metadata(config):
        if table.get("name") == table_name:
            return table
    return None


def _fetch_all_records_from_table(config, table_name, params=None):
    """
    Airtable에서 특정 테이블의 전체 레코드를 페이지네이션 처리하여 반환한다.
    """
    url = _get_table_url(config, table_name)
    headers = _get_headers(config)
    all_records = []
    offset = None
    params = dict(params or {})

    while True:
        if offset:
            params["offset"] = offset
        elif "offset" in params:
            params.pop("offset")

        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        all_records.extend(data.get("records", []))
        offset = data.get("offset")
        if not offset:
            break

    return all_records


def _fetch_all_records(config, params=None):
    return _fetch_all_records_from_table(config, REGISTRATION_TABLE, params)


def _fetch_summary_records(config, params=None):
    return _fetch_all_records_from_table(config, SUMMARY_TABLE, params)


def _record_to_dict(record, fields_map):
    fields = record.get("fields", {})
    return {
        "record_id": record["id"],
        "month": fields.get(fields_map["month"], ""),
        "name": fields.get(fields_map["name"], ""),
        "nickname": fields.get(fields_map["nickname"], ""),
        "email": fields.get(fields_map["email"], ""),
        "phone": fields.get(fields_map["phone"], ""),
        "level": fields.get(fields_map["level"], ""),
        "privacy_agree": fields.get(fields_map["privacy_agree"], ""),
        "paid": fields.get(fields_map["paid"], False),
        "send_status": fields.get(fields_map["send_status"], "미발송"),
        "created_time": record.get("createdTime", ""),
    }


def _combine_formulas(*formulas):
    valid = [formula for formula in formulas if formula]
    if not valid:
        return ""
    if len(valid) == 1:
        return valid[0]
    return f"AND({','.join(valid)})"


def _month_formula(config, month_label):
    month_field = config["airtable"]["fields"]["month"]
    return f"{{{month_field}}}='{month_label}'"


def _summary_month_formula(month_label):
    return f"{{기준월}}='{month_label}'"


def _normalize_month_label(value):
    raw = str(value or "").strip()
    if raw.endswith("월"):
        prefix = raw[:-1].strip()
        if prefix.isdigit():
            month_num = int(prefix)
            if 1 <= month_num <= 12:
                return f"{month_num}월"
    return ""


def _target_month_label(config, month_label=None):
    if month_label:
        return month_label
    return config["airtable"].get("current_month", "").strip() or _derive_month_label(config)


def _find_summary_record(config, month_label):
    if not month_label:
        return None
    records = _fetch_summary_records(config, {"filterByFormula": _summary_month_formula(month_label)})
    return records[0] if records else None


def _build_summary_fields(config, month_label, stats):
    webinar = config.get("webinar", {})
    webinar_date = webinar.get("date", "").strip()
    webinar_time = webinar.get("time", "").strip() or "20:00"
    summary_datetime = f"{webinar_date}T{webinar_time}:00" if webinar_date else ""

    payload_fields = {
        "기준월": month_label,
        "신청자 수": stats["registered"],
        "입금완료자 수": stats["paid"],
        # Legacy field: keep it blank so the summary table stays readable.
        "접수테이블명": "",
    }
    if month_label == _target_month_label(config):
        payload_fields.update(
            {
                "강사명1": webinar.get("speaker1", ""),
                "강사명2": webinar.get("speaker2", ""),
                "강사1 주제": webinar.get("topic1", ""),
                "강사2 주제": webinar.get("topic2", ""),
                "웨비나일시": summary_datetime,
            }
        )
    return payload_fields


def _extract_invalid_summary_field(response_text):
    try:
        payload = json.loads(response_text)
    except Exception:
        return None

    message = payload.get("error", {}).get("message", "")
    if not message.startswith('Field "'):
        return None

    _, _, rest = message.partition('Field "')
    field_name, separator, _ = rest.partition('"')
    return field_name if separator else None


def _save_summary_record(config, summary_url, record_id, payload_fields):
    method = requests.patch if record_id else requests.post
    url = f"{summary_url}/{record_id}" if record_id else summary_url
    fields_to_save = dict(payload_fields)

    for _ in range(len(payload_fields) + 1):
        response = method(
            url,
            headers=_get_headers(config),
            json={"fields": fields_to_save},
            timeout=15,
        )
        if response.status_code in (200, 201):
            return response.json()

        invalid_field = _extract_invalid_summary_field(response.text)
        if invalid_field and invalid_field in fields_to_save:
            fields_to_save.pop(invalid_field, None)
            continue

        raise RuntimeError(f"월별 집계 동기화 실패: {response.text[:120]}")

    raise RuntimeError("월별 집계 동기화 실패: 저장 가능한 필드가 없습니다.")


def _sync_registration_links(config, summary_record_ids):
    link_field = config["airtable"]["fields"]["webinar_link"]
    registration_url = _get_registration_url(config)
    updates = []

    for record in _fetch_all_records(config):
        fields = record.get("fields", {})
        month_label = fields.get(config["airtable"]["fields"]["month"], "").strip()
        summary_record_id = summary_record_ids.get(month_label)
        if not summary_record_id:
            continue

        current_links = fields.get(link_field) or []
        if current_links == [summary_record_id]:
            continue

        updates.append(
            {
                "id": record["id"],
                "fields": {
                    link_field: [summary_record_id],
                },
            }
        )

    for start in range(0, len(updates), 10):
        batch = updates[start:start + 10]
        response = requests.patch(
            registration_url,
            headers=_get_headers(config),
            json={"records": batch},
            timeout=15,
        )
        response.raise_for_status()


def get_all_registrants(month_label=None):
    config = _load_config()
    fields_map = config["airtable"]["fields"]
    target_month = _target_month_label(config, month_label)
    params = {"filterByFormula": _month_formula(config, target_month)} if target_month else {}
    records = _fetch_all_records(config, params)
    return [_record_to_dict(record, fields_map) for record in records]


def get_paid_registrants(month_label=None):
    config = _load_config()
    fields_map = config["airtable"]["fields"]
    target_month = _target_month_label(config, month_label)
    paid_field = fields_map["paid"]
    formula = _combine_formulas(
        _month_formula(config, target_month),
        f"{{{paid_field}}}=1",
    )
    records = _fetch_all_records(config, {"filterByFormula": formula})
    return [_record_to_dict(record, fields_map) for record in records]


def get_unsent_paid(month_label=None):
    config = _load_config()
    fields_map = config["airtable"]["fields"]
    target_month = _target_month_label(config, month_label)
    paid_field = fields_map["paid"]
    status_field = fields_map["send_status"]
    formula = _combine_formulas(
        _month_formula(config, target_month),
        f"{{{paid_field}}}=1",
        f"{{{status_field}}}='미발송'",
    )
    records = _fetch_all_records(config, {"filterByFormula": formula})
    return [_record_to_dict(record, fields_map) for record in records]


def update_send_status(record_id, status):
    config = _load_config()
    fields_map = config["airtable"]["fields"]
    url = f"{_get_registration_url(config)}/{record_id}"
    payload = {"fields": {fields_map["send_status"]: status}}
    response = requests.patch(url, headers=_get_headers(config), json=payload, timeout=15)
    return response.status_code == 200


def test_connection():
    try:
        config = _load_config()
        if not config["airtable"]["api_key"] or not config["airtable"]["base_id"]:
            return False, "API 키 또는 Base ID가 설정되지 않았습니다."

        url = f"https://api.airtable.com/v0/meta/bases/{config['airtable']['base_id']}/tables"
        response = requests.get(url, headers=_get_headers(config), timeout=10)
        if response.status_code == 200:
            return True, "Airtable 연결 성공"
        if response.status_code == 401:
            return False, "인증 실패: API 키를 확인하세요."
        if response.status_code == 404:
            return False, "Base ID를 찾을 수 없습니다."
        return False, f"연결 실패 (HTTP {response.status_code})"
    except requests.exceptions.ConnectionError:
        return False, "인터넷 연결을 확인하세요."
    except Exception as e:
        return False, f"오류: {str(e)}"


def list_tables():
    config = _load_config()
    return [table["name"] for table in _fetch_table_metadata(config)]


def list_available_months():
    config = _load_config()
    months = {config["airtable"].get("current_month", "")}

    if REGISTRATION_TABLE in list_tables():
        fields_map = config["airtable"]["fields"]
        for record in _fetch_all_records(config):
            month_label = record.get("fields", {}).get(fields_map["month"], "").strip()
            if month_label:
                months.add(month_label)

    if SUMMARY_TABLE in list_tables():
        summary_records = _fetch_all_records_from_table(config, SUMMARY_TABLE)
        for record in summary_records:
            month_label = record.get("fields", {}).get("기준월", "").strip()
            if month_label:
                months.add(month_label)

    return _sort_month_labels(label for label in months if label)


def ensure_unified_table():
    config = _load_config()
    if REGISTRATION_TABLE in list_tables():
        return True, REGISTRATION_TABLE, f"이미 존재하는 테이블입니다: {REGISTRATION_TABLE}"

    url = f"https://api.airtable.com/v0/meta/bases/{config['airtable']['base_id']}/tables"
    payload = {
        "name": REGISTRATION_TABLE,
        "fields": [
            {"name": "기준월", "type": "singleLineText"},
            {"name": "성함", "type": "singleLineText"},
            {"name": "활동명", "type": "singleLineText"},
            {"name": "이메일", "type": "email"},
            {"name": "휴대폰번호", "type": "phoneNumber"},
            {
                "name": "수준",
                "type": "singleSelect",
                "options": {"choices": [{"name": "입문자"}, {"name": "초보자"}, {"name": "중급자"}]},
            },
            {
                "name": "개인정보동의",
                "type": "singleSelect",
                "options": {"choices": [{"name": "예"}, {"name": "아니오"}]},
            },
            {"name": "입금완료", "type": "checkbox", "options": {"icon": "check", "color": "greenBright"}},
            {
                "name": "발송상태",
                "type": "singleSelect",
                "options": {
                    "choices": [
                        {"name": "미발송"},
                        {"name": "확인발송완료"},
                        {"name": "링크발송완료"},
                        {"name": "피드백발송완료"},
                    ]
                },
            },
            {"name": "원본테이블명", "type": "singleLineText"},
            {"name": "원본레코드ID", "type": "singleLineText"},
        ],
    }
    res = requests.post(url, headers=_get_headers(config), json=payload, timeout=15)
    if res.status_code == 200:
        return True, REGISTRATION_TABLE, f"{REGISTRATION_TABLE} 테이블 생성 완료"
    return False, REGISTRATION_TABLE, f"생성 실패: {res.text[:100]}"


def ensure_summary_table():
    config = _load_config()
    if SUMMARY_TABLE in list_tables():
        return True, SUMMARY_TABLE, f"이미 존재하는 테이블입니다: {SUMMARY_TABLE}"

    url = f"https://api.airtable.com/v0/meta/bases/{config['airtable']['base_id']}/tables"
    payload = {
        "name": SUMMARY_TABLE,
        "fields": [
            {"name": "기준월", "type": "singleLineText"},
            {"name": "강사명1", "type": "singleLineText"},
            {"name": "강사명2", "type": "singleLineText"},
            {"name": "강사1 주제", "type": "singleLineText"},
            {"name": "강사2 주제", "type": "singleLineText"},
            {
                "name": "웨비나일시",
                "type": "dateTime",
                "options": {
                    "dateFormat": {"name": "local"},
                    "timeFormat": {"name": "24hour"},
                    "timeZone": "Asia/Seoul",
                },
            },
            {"name": "신청자 수", "type": "number", "options": {"precision": 0}},
            {"name": "입금완료자 수", "type": "number", "options": {"precision": 0}},
            {"name": "접수테이블명", "type": "singleLineText"},
        ],
    }
    res = requests.post(url, headers=_get_headers(config), json=payload, timeout=15)
    if res.status_code == 200:
        return True, SUMMARY_TABLE, f"{SUMMARY_TABLE} 테이블 생성 완료"
    return False, SUMMARY_TABLE, f"생성 실패: {res.text[:100]}"


def ensure_feedback_table():
    config = _load_config()
    if FEEDBACK_TABLE in list_tables():
        return True, FEEDBACK_TABLE, f"이미 존재하는 테이블입니다: {FEEDBACK_TABLE}"

    url = f"https://api.airtable.com/v0/meta/bases/{config['airtable']['base_id']}/tables"
    payload = {
        "name": FEEDBACK_TABLE,
        "fields": [
            {"name": "기준월", "type": "singleLineText"},
            {"name": "웨비나명", "type": "singleLineText"},
            {"name": "성함", "type": "singleLineText"},
            {"name": "만족도", "type": "number", "options": {"precision": 0}},
            {"name": "가장 좋았던 점", "type": "multilineText"},
            {"name": "다음에 듣고 싶은 주제", "type": "multilineText"},
            {"name": "자유 의견", "type": "multilineText"},
        ],
    }
    res = requests.post(url, headers=_get_headers(config), json=payload, timeout=15)
    if res.status_code == 200:
        return True, FEEDBACK_TABLE, f"{FEEDBACK_TABLE} 테이블 생성 완료"
    return False, FEEDBACK_TABLE, f"생성 실패: {res.text[:100]}"


def migrate_month_fields_to_single_select():
    config = _load_config()
    target_tables = [REGISTRATION_TABLE, SUMMARY_TABLE, FEEDBACK_TABLE]
    results = []

    for table_name in target_tables:
        table_meta = _find_table_metadata(config, table_name)
        if not table_meta:
            results.append({"table": table_name, "status": "missing"})
            continue

        fields_by_name = {field["name"]: field for field in table_meta.get("fields", [])}
        month_field = fields_by_name.get("기준월")
        if not month_field:
            results.append({"table": table_name, "status": "missing_month_field"})
            continue

        source_field_name = "기준월"
        if month_field.get("type") != "singleSelect":
            backup_field_name = "기준월_텍스트"
            suffix = 2
            while backup_field_name in fields_by_name:
                backup_field_name = f"기준월_텍스트_{suffix}"
                suffix += 1

            field_url = (
                f"https://api.airtable.com/v0/meta/bases/{config['airtable']['base_id']}"
                f"/tables/{table_meta['id']}/fields/{month_field['id']}"
            )
            rename_response = requests.patch(
                field_url,
                headers=_get_headers(config),
                json={"name": backup_field_name},
                timeout=15,
            )
            rename_response.raise_for_status()

            create_response = requests.post(
                f"https://api.airtable.com/v0/meta/bases/{config['airtable']['base_id']}/tables/{table_meta['id']}/fields",
                headers=_get_headers(config),
                json={
                    "name": "기준월",
                    "type": "singleSelect",
                    "options": {"choices": MONTH_SELECT_CHOICES},
                },
                timeout=15,
            )
            create_response.raise_for_status()
            source_field_name = backup_field_name

        records = _fetch_all_records_from_table(config, table_name)
        update_batches = []
        for record in records:
            fields = record.get("fields", {})
            month_label = _normalize_month_label(fields.get(source_field_name, ""))
            if not month_label:
                continue
            if fields.get("기준월") == month_label:
                continue
            update_batches.append(
                {
                    "id": record["id"],
                    "fields": {"기준월": month_label},
                }
            )

        table_url = _get_table_url(config, table_name)
        for start in range(0, len(update_batches), 10):
            batch = update_batches[start:start + 10]
            response = requests.patch(
                table_url,
                headers=_get_headers(config),
                json={"records": batch, "typecast": True},
                timeout=15,
            )
            response.raise_for_status()

        results.append(
            {
                "table": table_name,
                "status": "ok",
                "source_field": source_field_name,
                "updated_records": len(update_batches),
            }
        )

    return results


def set_current_month(month_label):
    config = _load_config()
    config["airtable"]["current_month"] = month_label
    config["airtable"]["table_name"] = REGISTRATION_TABLE
    summary_record = _find_summary_record(config, month_label)
    config["airtable"]["current_webinar_record_id"] = summary_record["id"] if summary_record else ""
    _save_config(config)


def sync_monthly_summary():
    config = _load_config()
    ok, _, msg = ensure_summary_table()
    if not ok:
        raise RuntimeError(msg)
    ok, _, msg = ensure_unified_table()
    if not ok:
        raise RuntimeError(msg)

    current_month = _target_month_label(config)
    summary_url = _get_table_url(config, SUMMARY_TABLE)
    existing_rows = _fetch_summary_records(config)
    existing_by_month = {}
    for record in existing_rows:
        month_label = record.get("fields", {}).get("기준월", "").strip()
        if month_label:
            existing_by_month[month_label] = record

    unified_records = _fetch_all_records(config)
    stats_by_month = defaultdict(lambda: {"registered": 0, "paid": 0})
    month_field = config["airtable"]["fields"]["month"]
    paid_field = config["airtable"]["fields"]["paid"]

    for record in unified_records:
        fields = record.get("fields", {})
        month_label = fields.get(month_field, "").strip()
        if not month_label:
            continue
        stats_by_month[month_label]["registered"] += 1
        if fields.get(paid_field):
            stats_by_month[month_label]["paid"] += 1

    months_to_sync = {
        month_label
        for month_label in (set(existing_by_month.keys()) | set(stats_by_month.keys()) | {current_month})
        if month_label
    }

    summary_record_ids = {}

    for month_label in _sort_month_labels(months_to_sync):
        stats = stats_by_month.get(month_label, {"registered": 0, "paid": 0})
        payload_fields = _build_summary_fields(config, month_label, stats)

        existing = existing_by_month.get(month_label)
        saved_record = _save_summary_record(
            config,
            summary_url,
            existing["id"] if existing else None,
            payload_fields,
        )
        summary_record_ids[month_label] = saved_record["id"]

    _sync_registration_links(config, summary_record_ids)

    config["airtable"]["current_webinar_record_id"] = summary_record_ids.get(current_month, "")
    _save_config(config)
    return True


def migrate_monthly_tables_to_unified():
    """
    기존 월별 접수 테이블을 웨비나접수_통합으로 이관한다.
    동일한 (기준월, 이름, 휴대폰번호, 이메일) 조합은 중복 삽입하지 않는다.
    """
    config = _load_config()
    ok, _, msg = ensure_unified_table()
    if not ok:
        raise RuntimeError(msg)

    fields_map = config["airtable"]["fields"]
    existing_records = _fetch_all_records(config)
    seen = set()
    for record in existing_records:
        fields = record.get("fields", {})
        signature = (
            fields.get(fields_map["month"], "").strip(),
            str(fields.get(fields_map["name"], "")).strip(),
            str(fields.get(fields_map["phone"], "")).strip(),
            str(fields.get(fields_map["email"], "")).strip(),
        )
        seen.add(signature)

    month_tables = [table for table in list_tables() if table.endswith("월_웨비나접수")]
    month_tables = [table for table in month_tables if table != REGISTRATION_TABLE]

    inserted = 0
    skipped = 0
    registration_url = _get_registration_url(config)

    for table_name in _sort_month_labels(month_tables):
        month_number = str(table_name).split("월_웨비나접수", 1)[0].strip()
        if not month_number.isdigit():
            continue
        month_label = f"{int(month_number)}월"
        legacy_records = _fetch_all_records_from_table(config, table_name)
        batch = []

        for record in legacy_records:
            fields = record.get("fields", {})
            signature = (
                month_label,
                str(fields.get(fields_map["name"], "")).strip(),
                str(fields.get(fields_map["phone"], "")).strip(),
                str(fields.get(fields_map["email"], "")).strip(),
            )
            if signature in seen:
                skipped += 1
                continue

            batch.append(
                {
                    "fields": {
                        "기준월": month_label,
                        "성함": fields.get(fields_map["name"], ""),
                        "활동명": fields.get(fields_map["nickname"], ""),
                        "이메일": fields.get(fields_map["email"], ""),
                        "휴대폰번호": fields.get(fields_map["phone"], ""),
                        "수준": fields.get(fields_map["level"], ""),
                        "개인정보동의": fields.get(fields_map["privacy_agree"], ""),
                        "입금완료": bool(fields.get(fields_map["paid"], False)),
                        "발송상태": fields.get(fields_map["send_status"], "미발송"),
                        "원본테이블명": table_name,
                        "원본레코드ID": record["id"],
                    }
                }
            )
            seen.add(signature)

            if len(batch) == 10:
                response = requests.post(
                    registration_url,
                    headers=_get_headers(config),
                    json={"records": batch},
                    timeout=15,
                )
                response.raise_for_status()
                inserted += len(batch)
                batch = []

        if batch:
            response = requests.post(
                registration_url,
                headers=_get_headers(config),
                json={"records": batch},
                timeout=15,
            )
            response.raise_for_status()
            inserted += len(batch)

    sync_monthly_summary()
    return {"inserted": inserted, "skipped": skipped, "table": REGISTRATION_TABLE}


def create_monthly_table(month=None):
    """
    레거시 호환용. 더 이상 월별 테이블을 생성하지 않고 통합 테이블을 보장한다.
    """
    ok, _, msg = ensure_unified_table()
    if not ok:
        return False, REGISTRATION_TABLE, msg
    config = _load_config()
    month_num = month or datetime.now().month
    month_label = f"{int(month_num)}월"
    config["airtable"]["current_month"] = month_label
    config["airtable"]["table_name"] = REGISTRATION_TABLE
    _save_config(config)
    sync_monthly_summary()
    return True, REGISTRATION_TABLE, f"{month_label} 회차를 {REGISTRATION_TABLE} 기준으로 준비했습니다."


def switch_table(table_name):
    """
    레거시 호환용. table_name이 'N월_웨비나접수' 형식이면 현재 회차만 바꾼다.
    """
    month_prefix = str(table_name).split("월_웨비나접수", 1)[0].strip()
    if month_prefix.isdigit():
        set_current_month(f"{int(month_prefix)}월")
        return

    config = _load_config()
    config["airtable"]["table_name"] = REGISTRATION_TABLE
    _save_config(config)
