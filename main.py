"""
크리AI티브 웨비나 자동화 프로그램
상단 테이블 바 + 발송 관리(탭①) + 설정(탭②)
"""

import json
import os
import sys
import threading
import webbrowser
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from datetime import datetime


def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


BASE_DIR = _base_dir()
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
DASHBOARD_PATH = os.path.join(BASE_DIR, "dashboard.html")
DASHBOARD_CONFIG_JS_PATH = os.path.join(BASE_DIR, "dashboard_config.js")

DEFAULT_CONFIG = {
    "airtable": {
        "api_key": "",
        "base_id": "",
        "table_name": "",
        "current_month": "",
        "current_webinar_record_id": "",
        "fields": {
            "name": "성함", "nickname": "활동명", "email": "이메일",
            "phone": "휴대폰번호", "level": "수준", "privacy_agree": "개인정보동의",
            "paid": "입금완료", "send_status": "발송상태", "month": "기준월",
            "webinar_link": "웨비나_월별집계",
        },
    },
    "solapi": {"api_key": "", "api_secret": "", "sender_phone": ""},
    "gmail": {"sender_email": "", "app_password": ""},
    "webinar": {
        "title": "크리AI티브 웨비나", "date": "", "time": "20:00",
        "meet_link": "", "feedback_link": "",
        "speaker1": "", "speaker2": "", "topic1": "", "topic2": "",
    },
}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    cfg.setdefault("airtable", {})
    cfg["airtable"].setdefault("fields", {})
    cfg["airtable"]["fields"].setdefault("name", "성함")
    cfg["airtable"]["fields"].setdefault("nickname", "활동명")
    cfg["airtable"]["fields"].setdefault("email", "이메일")
    cfg["airtable"]["fields"].setdefault("phone", "휴대폰번호")
    cfg["airtable"]["fields"].setdefault("level", "수준")
    cfg["airtable"]["fields"].setdefault("privacy_agree", "개인정보동의")
    cfg["airtable"]["fields"].setdefault("paid", "입금완료")
    cfg["airtable"]["fields"].setdefault("send_status", "발송상태")
    cfg["airtable"]["fields"].setdefault("month", "기준월")
    cfg["airtable"]["fields"].setdefault("webinar_link", "웨비나_월별집계")
    cfg["airtable"]["fields"].pop("webinar_date", None)
    cfg["airtable"]["fields"].pop("recording_sent", None)
    cfg["airtable"].setdefault("current_month", "")
    cfg["airtable"].setdefault("current_webinar_record_id", "")
    cfg["airtable"]["table_name"] = "웨비나접수_통합"

    cfg.setdefault("solapi", {})
    cfg["solapi"].setdefault("api_key", "")
    cfg["solapi"].setdefault("api_secret", "")
    cfg["solapi"].setdefault("sender_phone", "")

    cfg.setdefault("gmail", {})
    cfg["gmail"].setdefault("sender_email", "")
    cfg["gmail"].setdefault("app_password", "")

    cfg.setdefault("webinar", {})
    cfg["webinar"].setdefault("title", "크리AI티브 웨비나")
    cfg["webinar"].setdefault("date", "")
    cfg["webinar"].setdefault("time", "20:00")
    cfg["webinar"].setdefault("meet_link", "")
    cfg["webinar"].setdefault("feedback_link", "")
    cfg["webinar"].setdefault("speaker1", "")
    cfg["webinar"].setdefault("speaker2", "")
    cfg["webinar"].setdefault("topic1", "")
    cfg["webinar"].setdefault("topic2", "")
    cfg["webinar"].pop("recording_link", None)
    if not cfg["airtable"]["current_month"]:
        webinar_date = cfg["webinar"].get("date", "").strip()
        try:
            cfg["airtable"]["current_month"] = f"{datetime.strptime(webinar_date, '%Y-%m-%d').month}월"
        except ValueError:
            cfg["airtable"]["current_month"] = f"{datetime.now().month}월"
    export_dashboard_config(cfg)
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    export_dashboard_config(cfg)


def _dashboard_config_payload(cfg):
    airtable_cfg = cfg.get("airtable", {})
    fields_cfg = airtable_cfg.get("fields", {})
    return {
        "pat": (airtable_cfg.get("api_key") or "").strip(),
        "baseId": (airtable_cfg.get("base_id") or "").strip(),
        "tableName": ((airtable_cfg.get("table_name") or "\uc6e8\ube44\ub098\uc811\uc218_\ud1b5\ud569")).strip(),
        "monthLabel": (airtable_cfg.get("current_month") or "").strip(),
        "monthField": ((fields_cfg.get("month") or "\uae30\uc900\uc6d4")).strip(),
    }


def export_dashboard_config(cfg=None):
    payload = _dashboard_config_payload(cfg or load_config())
    script_body = "window.__DASHBOARD_CFG__ = " + json.dumps(payload, ensure_ascii=False, indent=2) + ";\n"
    with open(DASHBOARD_CONFIG_JS_PATH, "w", encoding="utf-8") as f:
        f.write(script_body)


# ════════════════════════════════════════════════════════════
#  카톡 공지 생성기
# ════════════════════════════════════════════════════════════
_WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def build_kakao_notice(raw_content, webinar):
    """사용자가 붙여넣은 원본 내용 + 웨비나 설정으로 카톡 공지문을 생성한다."""
    title = (webinar.get("title") or "크리AI티브 웨비나").strip()
    date = (webinar.get("date") or "").strip()
    time = (webinar.get("time") or "20:00").strip()
    meet_link = (webinar.get("meet_link") or "").strip()
    speaker1 = (webinar.get("speaker1") or "").strip()
    speaker2 = (webinar.get("speaker2") or "").strip()
    topic1 = (webinar.get("topic1") or "").strip()
    topic2 = (webinar.get("topic2") or "").strip()

    date_label = date
    if date:
        try:
            d = datetime.strptime(date, "%Y-%m-%d")
            date_label = f"{d.month}월 {d.day}일 ({_WEEKDAY_KO[d.weekday()]})"
        except ValueError:
            pass

    body = "\n".join(line.strip() for line in raw_content.splitlines() if line.strip())

    parts = [f"🎓 [{title}] 안내", ""]
    if date_label:
        parts.append(f"📅 일시: {date_label} {time}")

    speaker_lines = []
    for name, topic in ((speaker1, topic1), (speaker2, topic2)):
        if not name:
            continue
        speaker_lines.append(f"  · {name} – {topic}" if topic else f"  · {name}")
    if speaker_lines:
        parts.append("🎤 강사 & 주제")
        parts.extend(speaker_lines)

    divider = "─" * 14
    parts.extend(["", divider, body, divider, ""])
    parts.append("💜 함께해요!")
    if meet_link:
        parts.append(f"🔗 참여 링크: {meet_link}")
    parts.append("")
    parts.append("#크리AI티브 #AI웨비나")

    return "\n".join(parts)


# ════════════════════════════════════════════════════════════
#  메인 애플리케이션
# ════════════════════════════════════════════════════════════

class WebinarApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("크리AI티브 웨비나 자동화")
        self.geometry("780x660")
        self.minsize(740, 600)

        self.config_data = load_config()
        export_dashboard_config(self.config_data)
        self._setup_style()

        # ── 상단 테이블 바 ──
        self._build_table_bar()

        # ── 하단 상태바 (notebook보다 먼저 pack) ──
        self._build_status_bar()

        # ── 탭 ──
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.tab_send = ttk.Frame(self.notebook)
        self.tab_kakao = ttk.Frame(self.notebook)
        self.tab_template = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_send, text="  발송 관리  ")
        self.notebook.add(self.tab_kakao, text="  카톡 공지  ")
        self.notebook.add(self.tab_template, text="  템플릿 편집  ")
        self.notebook.add(self.tab_settings, text="  설정  ")

        self._build_send_tab()
        self._build_kakao_tab()
        self._build_template_tab()
        self._build_settings_tab()

        # 스케줄러 시작
        self._start_scheduler()

        # 시작 시 현재 웨비나 기준 내부 회차 동기화
        self.after(400, self._auto_detect_table)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── 스타일 ────────────────────────────────────────────
    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        BG    = "#f4f5f7"
        WHITE = "#ffffff"
        BRAND = "#534AB7"
        LIGHT = "#eeedf9"

        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=[16, 9], font=("", 10))
        style.map("TNotebook.Tab",
                  background=[("selected", WHITE), ("!selected", BG)],
                  foreground=[("selected", BRAND), ("!selected", "#666")])

        style.configure("TFrame", background=BG)
        style.configure("Section.TLabelframe", background=WHITE, relief="flat",
                        borderwidth=1, bordercolor="#dde0f0")
        style.configure("Section.TLabelframe.Label", background=WHITE,
                        font=("", 10, "bold"), foreground=BRAND)

        # Primary 버튼 (발송)
        style.configure("Primary.TButton",
                        background=BRAND, foreground=WHITE,
                        font=("", 9, "bold"), padding=[10, 5])
        style.map("Primary.TButton",
                  background=[("active", "#3f37a0"), ("disabled", "#b0acd8")],
                  foreground=[("disabled", "#e0dff5")])

        # Secondary 버튼 (새로고침·기타)
        style.configure("Secondary.TButton",
                        background=LIGHT, foreground=BRAND,
                        font=("", 9), padding=[8, 4])
        style.map("Secondary.TButton",
                  background=[("active", "#d8d5f5")])

        # Test 버튼 (테스트 발송)
        style.configure("Test.TButton",
                        background="#e8f4fd", foreground="#0066cc",
                        font=("", 9, "bold"), padding=[10, 5])
        style.map("Test.TButton",
                  background=[("active", "#cce8fa"), ("disabled", "#d0e8f5")])

    # ════════════════════════════════════════════════════════
    #  하단 상태바
    # ════════════════════════════════════════════════════════
    def _build_status_bar(self):
        bar = tk.Frame(self, bg="#2d2b4e", height=26)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        bar.pack_propagate(False)

        self.lbl_last_send = tk.Label(
            bar, text="마지막 발송: -", bg="#2d2b4e", fg="#9896c0",
            font=("", 8), padx=12)
        self.lbl_last_send.pack(side=tk.LEFT)

        tk.Label(bar, text="|", bg="#2d2b4e", fg="#4a4870").pack(side=tk.LEFT)

        webinar_date = self.config_data.get("webinar", {}).get("date", "미설정")
        self.lbl_status_date = tk.Label(
            bar, text=f"웨비나: {webinar_date}", bg="#2d2b4e", fg="#9896c0",
            font=("", 8), padx=12)
        self.lbl_status_date.pack(side=tk.LEFT)

        tk.Label(bar, text="v2.0", bg="#2d2b4e", fg="#4a4870",
                 font=("", 8), padx=12).pack(side=tk.RIGHT)

    # ════════════════════════════════════════════════════════
    #  상단 테이블 바
    # ════════════════════════════════════════════════════════
    def _build_table_bar(self):
        bar = tk.Frame(self, bg="#534AB7", pady=8, padx=14)
        bar.pack(fill=tk.X)

        tk.Label(bar, text="운영 기준:", bg="#534AB7", fg="#d0cbff",
                 font=("", 9)).pack(side=tk.LEFT)

        self.lbl_table_info = tk.Label(
            bar,
            text="통합 접수 테이블",
            bg="#534AB7",
            fg="#ffffff",
            font=("", 9, "bold"),
        )
        self.lbl_table_info.pack(side=tk.LEFT, padx=(6, 12))

        ttk.Button(bar, text="↻", width=2,
                   command=self._refresh_table_list).pack(side=tk.LEFT, padx=(0, 10))

        self.lbl_webinar_scope = tk.Label(
            bar,
            text="",
            bg="#534AB7",
            fg="#d0cbff",
            font=("", 9),
        )
        self.lbl_webinar_scope.pack(side=tk.LEFT)

    # ── 테이블 목록 새로고침 ──────────────────────────────
    def _refresh_table_list(self, callback=None):
        def _fetch():
            try:
                from modules import airtable_client
                airtable_client.ensure_unified_table()
                current_month = self.config_data["airtable"].get("current_month", "")
                webinar_date = self.config_data.get("webinar", {}).get("date", "").strip()
                self.after(0, lambda: self._update_table_bar(current_month, webinar_date, callback))
            except Exception as e:
                self.after(0, lambda: self._log(f"[오류] 통합 테이블 상태 조회 실패: {e}"))
        threading.Thread(target=_fetch, daemon=True).start()

    def _update_table_bar(self, current_month, webinar_date, callback=None):
        self.lbl_table_info.config(text="웨비나접수_통합")
        if webinar_date:
            scope_text = f"현재 웨비나: {webinar_date}"
        elif current_month:
            scope_text = f"내부 분류값: {current_month}"
        else:
            scope_text = "현재 웨비나 날짜 미설정"
        self.lbl_webinar_scope.config(text=scope_text)
        if callback:
            callback()

    # ── 시작 시 자동 감지 ────────────────────────────────
    def _auto_detect_table(self):
        webinar_date = self.config_data.get("webinar", {}).get("date", "").strip()
        target_month = datetime.now().month
        if webinar_date:
            try:
                target_month = datetime.strptime(webinar_date, "%Y-%m-%d").month
            except ValueError:
                pass

        target_month_label = f"{target_month}월"

        def _create():
            from modules import airtable_client
            ok, table_name, msg = airtable_client.create_monthly_table(target_month)
            if ok:
                self.config_data["airtable"]["current_month"] = target_month_label
                self.config_data["airtable"]["table_name"] = table_name
                save_config(self.config_data)
                self.after(0, lambda: self._log(f"[운영 기준 동기화] {msg}"))
                self.after(0, self._refresh_table_list)
                self.after(0, self._refresh_counts)
                self.after(0, self._sync_monthly_summary_async)
            else:
                self.after(0, lambda: self._log(f"[오류] {msg}"))
        threading.Thread(target=_create, daemon=True).start()

    # ════════════════════════════════════════════════════════
    #  탭① 발송 관리
    # ════════════════════════════════════════════════════════
    def _build_send_tab(self):
        frame = self.tab_send
        frame.configure(padding=16)

        # ── 입금 확인 발송 ──
        sec1 = ttk.LabelFrame(frame, text="① 입금 확인 발송", style="Section.TLabelframe", padding=14)
        sec1.pack(fill=tk.X, pady=(0, 8))
        self.lbl_unsent = tk.Label(sec1, text="미발송 N명 확인 중...", bg="#fff", fg="#666", font=("", 9))
        self.lbl_unsent.pack(side=tk.LEFT)
        ttk.Button(sec1, text="새로고침", style="Secondary.TButton",
                   command=self._refresh_counts).pack(side=tk.RIGHT, padx=(0, 6))
        self.btn_confirm = ttk.Button(sec1, text="이메일+문자 발송", style="Primary.TButton",
                                      command=self._send_confirm)
        self.btn_confirm.pack(side=tk.RIGHT)

        # ── 웨비나 링크 발송 ──
        sec2 = ttk.LabelFrame(frame, text="② 웨비나 링크 발송 (D-1 자동 / 수동)", style="Section.TLabelframe", padding=14)
        sec2.pack(fill=tk.X, pady=(0, 8))
        self.lbl_link = tk.Label(sec2, text="입금완료 전체 N명", bg="#fff", fg="#666", font=("", 9))
        self.lbl_link.pack(side=tk.LEFT)
        self.btn_link = ttk.Button(sec2, text="이메일+문자 발송", style="Primary.TButton",
                                   command=self._send_link)
        self.btn_link.pack(side=tk.RIGHT)

        # ── 피드백 링크 발송 ──
        sec3 = ttk.LabelFrame(frame, text="③ 피드백 링크 발송 (당일 22:10 자동 / 수동)", style="Section.TLabelframe", padding=14)
        sec3.pack(fill=tk.X, pady=(0, 8))
        self.lbl_feedback = tk.Label(sec3, text="입금완료 전체 N명", bg="#fff", fg="#666", font=("", 9))
        self.lbl_feedback.pack(side=tk.LEFT)
        self.btn_feedback = ttk.Button(sec3, text="이메일+문자 발송", style="Primary.TButton",
                                       command=self._send_feedback)
        self.btn_feedback.pack(side=tk.RIGHT)

        # ── 테스트 발송 ──
        sec4 = ttk.LabelFrame(frame, text="④ 테스트 발송 (나에게 보내기)", style="Section.TLabelframe", padding=14)
        sec4.pack(fill=tk.X, pady=(0, 8))

        row1 = tk.Frame(sec4, bg="#fff")
        row1.pack(fill=tk.X, pady=(0, 5))
        tk.Label(row1, text="이메일", bg="#fff", font=("", 9), width=8, anchor="w").pack(side=tk.LEFT)
        self.test_email_var = tk.StringVar(value=self.config_data.get("gmail", {}).get("sender_email", ""))
        ttk.Entry(row1, textvariable=self.test_email_var, width=30).pack(side=tk.LEFT, padx=(0, 16))
        tk.Label(row1, text="전화번호", bg="#fff", font=("", 9), width=7, anchor="w").pack(side=tk.LEFT)
        self.test_phone_var = tk.StringVar(value=self.config_data.get("solapi", {}).get("sender_phone", ""))
        ttk.Entry(row1, textvariable=self.test_phone_var, width=16).pack(side=tk.LEFT)

        row2 = tk.Frame(sec4, bg="#fff")
        row2.pack(fill=tk.X)
        tk.Label(row2, text="발송 유형", bg="#fff", font=("", 9), width=8, anchor="w").pack(side=tk.LEFT)
        self.test_type_var = tk.StringVar(value="입금 확인")
        ttk.Combobox(row2, textvariable=self.test_type_var,
                     values=["입금 확인", "웨비나 링크", "피드백"],
                     state="readonly", width=14).pack(side=tk.LEFT, padx=(0, 10))
        self.btn_test_send = ttk.Button(row2, text="테스트 발송", style="Test.TButton",
                                        command=self._send_test)
        self.btn_test_send.pack(side=tk.LEFT)

        # ── 로그 창 ──
        log_frame = ttk.LabelFrame(frame, text="발송 로그", style="Section.TLabelframe", padding=8)
        log_frame.pack(fill=tk.BOTH, expand=True)
        self.log_box = scrolledtext.ScrolledText(log_frame, height=8, font=("Consolas", 9),
                                                  state=tk.DISABLED, bg="#1e1e2e", fg="#cdd6f4",
                                                  relief=tk.FLAT)
        self.log_box.pack(fill=tk.BOTH, expand=True)

    # ── 카운트 새로고침 ────────────────────────────────────
    def _refresh_counts(self):
        def _fetch():
            try:
                from modules import airtable_client
                unsent = airtable_client.get_unsent_paid()
                paid   = airtable_client.get_paid_registrants()
                self.after(0, lambda: self._update_count_labels(len(unsent), len(paid)))
            except Exception as e:
                self.after(0, lambda: self._log(f"[오류] 카운트 조회 실패: {e}"))
        threading.Thread(target=_fetch, daemon=True).start()

    def _update_count_labels(self, unsent, paid):
        color = "#d32f2f" if unsent > 0 else "#388e3c"
        weight = "bold" if unsent > 0 else ""
        self.lbl_unsent.config(text=f"미발송  {unsent}명  대기 중", fg=color,
                               font=("", 9, weight) if weight else ("", 9))
        self.lbl_link.config(text=f"입금완료 {paid}명 전체")
        self.lbl_feedback.config(text=f"입금완료 {paid}명 전체")

    # ── 발송 공통 래퍼 ────────────────────────────────────
    def _run_send(self, btn, action_fn, confirm_msg):
        if not messagebox.askyesno("발송 확인", confirm_msg):
            return
        btn.config(state=tk.DISABLED)
        self._log(f"[{datetime.now().strftime('%H:%M:%S')}] 발송 시작...")

        def _task():
            try:
                ok, fail = action_fn()
                self.after(0, lambda: self._log(
                    f"[{datetime.now().strftime('%H:%M:%S')}] 완료 — 성공 {ok}건 / 실패 {fail}건"
                ))
            except Exception as e:
                self.after(0, lambda: self._log(f"[오류] {e}"))
            finally:
                self.after(0, lambda: btn.config(state=tk.NORMAL))
                self.after(0, self._refresh_counts)

        threading.Thread(target=_task, daemon=True).start()

    # ── 발송 버튼 핸들러 ──────────────────────────────────
    def _send_confirm(self):
        from modules import airtable_client, email_sender, sms_sender
        targets = airtable_client.get_unsent_paid()
        if not targets:
            messagebox.showinfo("알림", "발송 대상이 없습니다."); return

        def action():
            e_ok, e_fail = email_sender.send_bulk_email(targets, "email_confirm")
            s_ok, s_fail = sms_sender.send_bulk_sms(targets, "sms_confirm")
            for p in targets:
                airtable_client.update_send_status(p["record_id"], "확인발송완료")
                self._log(f"  ✓ {p['name']} — 이메일·문자 발송")
            return e_ok + s_ok, e_fail + s_fail

        self._run_send(self.btn_confirm, action,
                       f"{len(targets)}명에게 입금 확인 이메일·문자를 발송합니다. 진행하시겠습니까?")

    def _send_link(self):
        from modules import airtable_client, email_sender, sms_sender
        if not self.config_data.get("webinar", {}).get("meet_link", "").strip():
            messagebox.showwarning("링크 미설정", "설정 탭에서 Google Meet 링크를 먼저 입력해 주세요.")
            return
        targets = airtable_client.get_paid_registrants()
        if not targets:
            messagebox.showinfo("알림", "발송 대상이 없습니다."); return

        def action():
            e_ok, e_fail = email_sender.send_bulk_email(targets, "email_link")
            s_ok, s_fail = sms_sender.send_bulk_sms(targets, "sms_link")
            for p in targets:
                airtable_client.update_send_status(p["record_id"], "링크발송완료")
                self._log(f"  ✓ {p['name']} — 링크 이메일·문자 발송")
            return e_ok + s_ok, e_fail + s_fail

        self._run_send(self.btn_link, action,
                       f"{len(targets)}명에게 웨비나 링크를 발송합니다. 진행하시겠습니까?")

    def _send_feedback(self):
        from modules import airtable_client, email_sender, sms_sender
        if not self.config_data.get("webinar", {}).get("feedback_link", "").strip():
            messagebox.showwarning("링크 미설정", "설정 탭에서 피드백 링크를 먼저 입력해 주세요.")
            return
        targets = airtable_client.get_paid_registrants()
        if not targets:
            messagebox.showinfo("알림", "발송 대상이 없습니다."); return

        def action():
            e_ok, e_fail = email_sender.send_bulk_email(targets, "email_feedback")
            s_ok, s_fail = sms_sender.send_bulk_sms(targets, "sms_feedback")
            for p in targets:
                airtable_client.update_send_status(p["record_id"], "피드백발송완료")
                self._log(f"  ✓ {p['name']} — 피드백 이메일·문자 발송")
            return e_ok + s_ok, e_fail + s_fail

        self._run_send(self.btn_feedback, action,
                       f"{len(targets)}명에게 피드백 링크를 발송합니다. 진행하시겠습니까?")

    # ── 로그 ──────────────────────────────────────────────
    def _log(self, msg):
        self.log_box.config(state=tk.NORMAL)
        self.log_box.insert(tk.END, msg + "\n")
        self.log_box.see(tk.END)
        self.log_box.config(state=tk.DISABLED)
        if "완료" in msg or "발송" in msg:
            self.lbl_last_send.config(
                text=f"마지막 발송: {datetime.now().strftime('%H:%M:%S')}")

    def _send_test(self):
        email = self.test_email_var.get().strip()
        phone = self.test_phone_var.get().strip()
        send_type = self.test_type_var.get()

        if not email and not phone:
            messagebox.showwarning("입력 필요", "이메일 또는 전화번호를 입력해 주세요.")
            return

        TYPE_MAP = {
            "입금 확인":   ("email_confirm", "sms_confirm"),
            "웨비나 링크": ("email_link",    "sms_link"),
            "피드백":      ("email_feedback", "sms_feedback"),
        }
        email_tpl, sms_tpl = TYPE_MAP[send_type]
        test_recipient = [{"name": "테스트", "email": email, "phone": phone, "record_id": None}]

        self.btn_test_send.config(state=tk.DISABLED)
        self._log(f"[테스트 발송] {send_type} → {email or '-'} / {phone or '-'}")

        def _task():
            from modules import email_sender, sms_sender
            e_ok = e_fail = s_ok = s_fail = 0
            if email:
                e_ok, e_fail = email_sender.send_bulk_email(test_recipient, email_tpl)
            if phone:
                s_ok, s_fail = sms_sender.send_bulk_sms(test_recipient, sms_tpl)
            result_msg = f"이메일 {'성공' if e_ok else ('실패' if email else '-')} / 문자 {'성공' if s_ok else ('실패' if phone else '-')}"
            self.after(0, lambda: self._log(f"[테스트 결과] {result_msg}"))
            self.after(0, lambda: messagebox.showinfo("테스트 발송 완료", result_msg))
            self.after(0, lambda: self.btn_test_send.config(state=tk.NORMAL))

        threading.Thread(target=_task, daemon=True).start()

    def _sync_monthly_summary_async(self):
        def _task():
            try:
                from modules import airtable_client
                airtable_client.sync_monthly_summary()
            except Exception as e:
                self.after(0, lambda: self._log(f"[월별집계 동기화 오류] {e}"))

        threading.Thread(target=_task, daemon=True).start()

    # ════════════════════════════════════════════════════════
    #  탭② 카톡 공지 생성
    # ════════════════════════════════════════════════════════
    def _build_kakao_tab(self):
        frame = self.tab_kakao
        frame.configure(padding=14)

        tk.Label(frame, text="원본 내용 붙여넣기", bg="#f4f5f7",
                 font=("", 9, "bold"), fg="#534AB7").pack(anchor="w", pady=(0, 4))
        self.kakao_input = scrolledtext.ScrolledText(
            frame, height=7, font=("", 9), relief=tk.FLAT, bd=1,
            bg="#ffffff", wrap=tk.WORD,
        )
        self.kakao_input.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        btn_row = tk.Frame(frame, bg="#f4f5f7")
        btn_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btn_row, text="공지문 생성", command=self._generate_kakao).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="복사", command=self._copy_kakao).pack(side=tk.LEFT, padx=6)
        ttk.Button(btn_row, text="지우기", command=self._clear_kakao).pack(side=tk.LEFT)

        tk.Label(frame, text="생성된 카톡 공지", bg="#f4f5f7",
                 font=("", 9, "bold"), fg="#534AB7").pack(anchor="w", pady=(4, 4))
        self.kakao_output = scrolledtext.ScrolledText(
            frame, height=10, font=("", 9), relief=tk.FLAT, bd=1,
            bg="#fff8e7", wrap=tk.WORD,
        )
        self.kakao_output.pack(fill=tk.BOTH, expand=True)

    def _generate_kakao(self):
        raw = self.kakao_input.get("1.0", tk.END).strip()
        if not raw:
            messagebox.showinfo("알림", "원본 내용을 입력해 주세요.")
            return
        notice = build_kakao_notice(raw, self.config_data.get("webinar", {}))
        self.kakao_output.delete("1.0", tk.END)
        self.kakao_output.insert("1.0", notice)

    def _copy_kakao(self):
        text = self.kakao_output.get("1.0", tk.END).strip()
        if not text:
            messagebox.showinfo("알림", "복사할 내용이 없습니다. 먼저 공지문을 생성해 주세요.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self._log("[카톡 공지] 클립보드에 복사되었습니다.")

    def _clear_kakao(self):
        self.kakao_input.delete("1.0", tk.END)
        self.kakao_output.delete("1.0", tk.END)

    # ════════════════════════════════════════════════════════
    #  탭③ 템플릿 편집
    # ════════════════════════════════════════════════════════
    def _build_template_tab(self):
        frame = self.tab_template
        frame.configure(padding=12)

        hint = tk.Label(frame,
                        text="사용 가능 변수:  {name}    {meet_link}    {feedback_link}",
                        bg="#f4f5f7", fg="#888", font=("", 8))
        hint.pack(anchor="w", pady=(0, 6))

        sub_nb = ttk.Notebook(frame)
        sub_nb.pack(fill=tk.BOTH, expand=True)
        self._template_sub_nb = sub_nb

        TEMPLATES = [
            ("① 입금 확인", "sms_confirm"),
            ("② 웨비나 링크", "sms_link"),
            ("③ 피드백", "sms_feedback"),
        ]
        self.tpl_texts = {}

        for tab_label, tpl_name in TEMPLATES:
            sub_frame = ttk.Frame(sub_nb, padding=8)
            sub_nb.add(sub_frame, text=f"  {tab_label}  ")

            st = scrolledtext.ScrolledText(
                sub_frame, font=("Consolas", 10), wrap=tk.WORD,
                relief=tk.FLAT, bg="#ffffff", bd=1)
            st.pack(fill=tk.BOTH, expand=True)

            tpl_path = os.path.join(BASE_DIR, "templates", f"{tpl_name}.txt")
            try:
                with open(tpl_path, "r", encoding="utf-8") as f:
                    st.insert("1.0", f.read())
            except FileNotFoundError:
                st.insert("1.0", "")

            self.tpl_texts[tpl_name] = st

        btn_row = tk.Frame(frame, bg="#f4f5f7")
        btn_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btn_row, text="현재 탭 저장", style="Secondary.TButton",
                   command=self._save_current_template).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_row, text="전체 저장", style="Primary.TButton",
                   command=self._save_all_templates).pack(side=tk.LEFT)

    def _save_current_template(self):
        TEMPLATE_NAMES = ["sms_confirm", "sms_link", "sms_feedback"]
        idx = self._template_sub_nb.index(self._template_sub_nb.select())
        self._write_template_file(TEMPLATE_NAMES[idx])
        messagebox.showinfo("저장 완료", f"{TEMPLATE_NAMES[idx]}.txt 저장되었습니다.")

    def _save_all_templates(self):
        for tpl_name in ["sms_confirm", "sms_link", "sms_feedback"]:
            self._write_template_file(tpl_name)
        messagebox.showinfo("저장 완료", "3개 템플릿이 모두 저장되었습니다.")

    def _write_template_file(self, tpl_name):
        content = self.tpl_texts[tpl_name].get("1.0", tk.END).rstrip("\n")
        tpl_path = os.path.join(BASE_DIR, "templates", f"{tpl_name}.txt")
        with open(tpl_path, "w", encoding="utf-8") as f:
            f.write(content)
        self._log(f"[템플릿 저장] {tpl_name}.txt")

    # ════════════════════════════════════════════════════════
    #  탭④ 설정
    # ════════════════════════════════════════════════════════
    def _build_settings_tab(self):
        frame = self.tab_settings
        frame.configure(padding=16)

        canvas = tk.Canvas(frame, bg="#f4f5f7", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        self.settings_inner = tk.Frame(canvas, bg="#f4f5f7")
        self.settings_inner.bind("<Configure>",
                                  lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.settings_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._build_settings_fields()

    def _build_settings_fields(self):
        inner = self.settings_inner
        cfg = self.config_data

        def section(title):
            f = ttk.LabelFrame(inner, text=title, style="Section.TLabelframe", padding=12)
            f.pack(fill=tk.X, padx=4, pady=(0, 10))
            return f

        def row(parent, label, var, show=""):
            r = tk.Frame(parent, bg="#fff")
            r.pack(fill=tk.X, pady=3)
            tk.Label(r, text=label, bg="#fff", width=22, anchor="w", font=("", 9)).pack(side=tk.LEFT)
            e = ttk.Entry(r, textvariable=var, show=show, width=36)
            e.pack(side=tk.LEFT, padx=4)
            return e

        self.sv = {}

        def sv(key, val=""):
            v = tk.StringVar(value=val)
            self.sv[key] = v
            return v

        s1 = section("Airtable")
        row(s1, "API 키 (읽기/쓰기용)", sv("at_key",   cfg["airtable"]["api_key"]), show="*")
        row(s1, "Base ID",              sv("at_base",  cfg["airtable"]["base_id"]))

        s2 = section("SOLAPI SMS")
        row(s2, "API 키",     sv("sms_key",    cfg["solapi"]["api_key"]), show="*")
        row(s2, "API Secret", sv("sms_secret", cfg["solapi"]["api_secret"]), show="*")
        row(s2, "발신 번호",  sv("sms_phone",  cfg["solapi"]["sender_phone"]))

        s3 = section("Gmail SMTP")
        row(s3, "Gmail 주소",   sv("gm_email", cfg["gmail"]["sender_email"]))
        row(s3, "앱 비밀번호", sv("gm_pass",  cfg["gmail"]["app_password"]), show="*")

        s4 = section("웨비나 정보")
        row(s4, "웨비나 제목",       sv("wb_title",    cfg["webinar"]["title"]))
        row(s4, "날짜 (YYYY-MM-DD)", sv("wb_date",     cfg["webinar"]["date"]))
        row(s4, "시작 시간",         sv("wb_time",     cfg["webinar"]["time"]))
        row(s4, "Meet 링크",         sv("wb_meet",     cfg["webinar"]["meet_link"]))
        row(s4, "피드백 링크",       sv("wb_feedback", cfg["webinar"]["feedback_link"]))

        s5 = section("월별 집계 정보")
        row(s5, "강사 1",            sv("wb_speaker1", cfg["webinar"]["speaker1"]))
        row(s5, "강사 1 주제",       sv("wb_topic1",   cfg["webinar"]["topic1"]))
        row(s5, "강사 2",            sv("wb_speaker2", cfg["webinar"]["speaker2"]))
        row(s5, "강사 2 주제",       sv("wb_topic2",   cfg["webinar"]["topic2"]))

        btn_frame = tk.Frame(inner, bg="#f4f5f7")
        btn_frame.pack(fill=tk.X, padx=4, pady=8)
        ttk.Button(btn_frame, text="저장", style="Primary.TButton",
                   command=self._save_settings).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="연결 테스트", style="Secondary.TButton",
                   command=self._test_connections).pack(side=tk.LEFT)

        sep = ttk.Separator(inner, orient=tk.HORIZONTAL)
        sep.pack(fill=tk.X, padx=4, pady=10)

        dash_frame = tk.Frame(inner, bg="#f4f5f7")
        dash_frame.pack(fill=tk.X, padx=4)
        tk.Label(dash_frame, text="대시보드 열기:", bg="#f4f5f7", font=("", 9)).pack(side=tk.LEFT)
        ttk.Button(dash_frame, text="🌐 dashboard.html 브라우저로 열기",
                   command=self._open_dashboard).pack(side=tk.LEFT, padx=8)

    def _save_settings(self):
        sv = self.sv
        self.config_data["airtable"]["api_key"]        = sv["at_key"].get().strip()
        self.config_data["airtable"]["base_id"]        = sv["at_base"].get().strip()
        self.config_data.setdefault("solapi", {})
        self.config_data["solapi"]["api_key"]          = sv["sms_key"].get().strip()
        self.config_data["solapi"]["api_secret"]       = sv["sms_secret"].get().strip()
        self.config_data["solapi"]["sender_phone"]     = sv["sms_phone"].get().strip()
        self.config_data["gmail"]["sender_email"]      = sv["gm_email"].get().strip()
        self.config_data["gmail"]["app_password"]      = sv["gm_pass"].get().strip()
        self.config_data["webinar"]["title"]           = sv["wb_title"].get().strip()
        self.config_data["webinar"]["date"]            = sv["wb_date"].get().strip()
        self.config_data["webinar"]["time"]            = sv["wb_time"].get().strip()
        self.config_data["webinar"]["meet_link"]       = sv["wb_meet"].get().strip()
        self.config_data["webinar"]["feedback_link"]   = sv["wb_feedback"].get().strip()
        self.config_data["webinar"]["speaker1"]        = sv["wb_speaker1"].get().strip()
        self.config_data["webinar"]["speaker2"]        = sv["wb_speaker2"].get().strip()
        self.config_data["webinar"]["topic1"]          = sv["wb_topic1"].get().strip()
        self.config_data["webinar"]["topic2"]          = sv["wb_topic2"].get().strip()
        save_config(self.config_data)
        self._sync_monthly_summary_async()
        self.lbl_status_date.config(
            text=f"웨비나: {self.config_data['webinar']['date'] or '미설정'}")
        messagebox.showinfo("저장 완료", "설정이 저장되었습니다.")

    def _test_connections(self):
        self._save_settings()
        def _test():
            from modules import airtable_client, email_sender, sms_sender
            at_ok, at_msg = airtable_client.test_connection()
            sms_ok, sms_msg = sms_sender.test_connection()
            gm_ok, gm_msg = email_sender.test_connection()
            result = (
                f"Airtable: {'OK' if at_ok else 'FAIL'} {at_msg}\n"
                f"SOLAPI:   {'OK' if sms_ok else 'FAIL'} {sms_msg}\n"
                f"Gmail:    {'OK' if gm_ok else 'FAIL'} {gm_msg}"
            )
            self.after(0, lambda: messagebox.showinfo("연결 테스트 결과", result))
        threading.Thread(target=_test, daemon=True).start()

    def _open_dashboard(self):
        if os.path.exists(DASHBOARD_PATH):
            export_dashboard_config(self.config_data)
            webbrowser.open(f"file:///{DASHBOARD_PATH.replace(chr(92), '/')}")
        else:
            messagebox.showerror("오류", f"dashboard.html을 찾을 수 없습니다.\n{DASHBOARD_PATH}")

    # ════════════════════════════════════════════════════════
    #  스케줄러
    # ════════════════════════════════════════════════════════
    def _start_scheduler(self):
        try:
            from modules import scheduler
            scheduler.set_log_callback(lambda msg: self.after(0, lambda: self._log(msg)))
            scheduler.start()
        except Exception as e:
            self._log(f"[스케줄러 시작 오류] {e}")

    def _on_close(self):
        try:
            from modules import scheduler
            scheduler.stop()
        except Exception:
            pass
        self.destroy()


# ════════════════════════════════════════════════════════════
#  진입점
# ════════════════════════════════════════════════════════════
if __name__ == "__main__":
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)
    app = WebinarApp()
    app.mainloop()
