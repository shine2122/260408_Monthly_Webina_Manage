from modules import airtable_client


def main():
    tasks = [
        ("통합 신청 테이블", airtable_client.ensure_unified_table),
        ("월별 집계 테이블", airtable_client.ensure_summary_table),
        ("피드백 테이블", airtable_client.ensure_feedback_table),
    ]

    for label, fn in tasks:
        try:
            ok, table_name, msg = fn()
            status = "OK" if ok else "FAIL"
            print(f"[{status}] {label} | {table_name} | {msg}")
        except Exception as e:
            print(f"[FAIL] {label} | {e}")


if __name__ == "__main__":
    main()
