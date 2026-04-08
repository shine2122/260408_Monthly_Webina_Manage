# Monthly_Webina_Manage - 개발 로그

AI 코딩 도구와 함께 진행한 개발 작업 기록입니다.

---

## 2026-03-31 (Day 1)

### 1. 기존 웨비나 자동화 앱을 이어받아 EXE와 설정 구조 정리

```text
어제 작업을 이어서 진행해줘

C:\Users\5800x\Documents\Claude\CriAItiveLab\Education\Monthly_Webina_Manage 어제 여기서 작업을 진행했었어. 이어서 작업을 진행해줘

그럼 exe 파일을 만들어저

응. exe 파일의 설정에 airtable api, gmail 주소와 앱 비밀번호등이 입력이 안되어 있어. 오류가 날 것 같아.
```

**Claude Code 작업:**
- 기존 자동화 시스템 문서를 바탕으로 현재 폴더 구조와 실행 흐름을 다시 파악했다.
- EXE 재빌드 경로를 점검하고, 실행 중인 프로세스 때문에 덮어쓰기가 막히는 문제를 확인했다.
- 설정 파일 구조를 손봐 Airtable 필드 의존성을 줄이고, 녹화 링크 발송 관련 설정을 제거했다.
- `config.json` - 웨비나 기본값, Airtable 필드, 강사/주제 입력 구조 정리
- `main.py` - 설정 로딩 보강, 녹화 링크 발송 섹션 제거 방향 반영
- `modules/airtable_client.py` - Airtable 필드 구조 변화에 맞춰 클라이언트 로직 정비
- `modules/email_sender.py` - 녹화 링크 메일 템플릿 의존 제거
- `modules/sms_sender.py` - 발송 구조 정리
- `dashboard.html` - 운영 대시보드와 설정 흐름 동기화
- `templates/email_feedback.html` - 피드백 메일 템플릿 조정
- `templates/email_recording.html` - 제거
- `templates/sms_recording.txt` - 제거

---

### 2. 월별 운영 방식과 Airtable 구조를 4월 기준으로 재설계

```text
웨비나접수를 3월_웨비나접수로 변경해줘. 그리고 매달마다 새로운 접수 테이블이 생기는 구조로 변경해줘. 예를 들어 4월에는 4월_웨비나접수, 5월에는 5월_웨비나접수

닫혔어. 그럼 exe에서 월별 테이블을 선택할 수 있는 거야? 아니면 어떤 구조가 좋아? 추천해줘

좋아. 수정 전환이 더 좋아.

1. 신청접수작성 페이지와 링크가 필요해. (vercel을 이용하는 것이 나은지, Airtable를 이용하는 것이 나은지 추천해줘.)
2. 신청접수작성은 매월 필요해. 4월 웨비나부터 시작하면 돼.
3. 피드백작성 페이지와 링크가 필요해.
4. exe 파일에서 '녹화링크 발송' 섹션은 필요없어. 제거해줘
5. Airtable의 베이스에서 '녹화발송완료' 필드와, '웨비나일시' 필드는 필요없어. 제거해줘.
6. 매달 집계된 결과를 비교할 수 있는 Table이 필요해
```

**Codex CLI 작업:**
- 현재 앱이 시스템 현재월을 기준으로 움직이던 구조를 웨비나 일정 기준으로 바꾸도록 설계했다.
- 운영 기준월을 4월부터 시작하도록 설정하고, 테이블 자동 감지/전환 로직을 4월 웨비나 기준으로 맞췄다.
- 월별 비교를 위한 `웨비나_월별집계` 동기화 흐름을 앱에서 직접 호출할 수 있게 연결했다.
- `config.json` - 기본 저장 테이블을 `4월_웨비나접수`로 조정
- `main.py` - 테이블 자동 감지, 월별 집계 동기화, 설정 저장 흐름 보강
- `modules/airtable_client.py` - 월별 집계 테이블, 피드백 테이블 생성/관리 함수 추가
- `bootstrap_web_airtable.py` - 4월 신청 테이블, 집계 테이블, 피드백 테이블 초기 생성용 스크립트 추가

---

### 3. 신청 접수 페이지와 피드백 페이지를 별도 웹 포털로 만들고 Vercel에 배포

```text
vercel를 연동하려면 어떻게 하지? 신청접수페이지를 보고 싶어

cd web_portal

npm i -g vercel

좋아

좋아

1,2번만진행해줘.
```

**Codex CLI 작업:**
- 공개 신청 페이지와 피드백 페이지는 `Vercel + Airtable` 조합이 가장 운영하기 좋다고 판단하고, Python EXE와 분리된 `web_portal` 배포 단위를 만들었다.
- 로컬 미리보기 서버를 띄워 신청/피드백 화면을 먼저 확인할 수 있게 했다.
- Vercel CLI 설치, 로그인, 프로젝트 연결, 환경 변수 등록, 재배포까지 진행해 실제 접수/피드백 링크를 바로 열 수 있는 상태로 만들었다.
- 테스트 접수 1건을 넣어 Airtable `4월_웨비나접수` 테이블에 실제 저장되는 것까지 검증했다.
- `web_portal/apply/index.html` - 신청 페이지 UI 구현
- `web_portal/feedback/index.html` - 피드백 페이지 UI 구현
- `web_portal/api/apply.js` - 신청 데이터를 Airtable에 저장하는 API 추가
- `web_portal/api/feedback.js` - 피드백 데이터를 Airtable에 저장하는 API 추가
- `web_portal/README.md` - 웹 포털 실행/배포 안내 정리
- `web_portal/.vercel/project.json` - Vercel 프로젝트 연결 정보 생성

---

### 4. 신청 폼 문구를 직접 편집 가능한 구조로 바꾸고, 페이지 세부 UX를 다듬기

```text
신청페이지의 구성은 아래와 같아야 해. 세미나에 대한 홍보성 글을 내가 직접 입력하고 수정할 수 있도록 해줘.

1번 문구는 필요 없을 것 같아. 제거해줘.

좋아. 그리고 /피드백에서 이메일은 불필요해. 제거해줘.

4월 문구는 아직 작성한게 없어.

- 제목
  - 도입 문단
  - 일정/방식/정원/참가비
  - 강사 1 정보와 세션 소개
  - 강사 2 정보와 세션 소개
  - 추천 대상
  - 오픈채팅 안내
  - 입금 안내/환불 규정

문구는 넣지 않고, 항목만 넣을거야. 아직 작업이 안되어 있어서 말이야

7번의 네 선택은 취소할 수 있어야 해. 한번 더 클릭하면 해제되게 해줘
```

**Codex CLI 작업:**
- 신청 페이지의 홍보 문구를 코드 본문에 박아두지 않고, 별도 콘텐츠 파일에서 직접 수정할 수 있도록 분리했다.
- 4월용 문구가 아직 없는 점을 반영해, 실제 문안 대신 항목만 비워 둔 골격형 랜딩 페이지로 바꿨다.
- 신청 폼 번호 체계를 다시 정리하고, 불필요한 확인 문항과 피드백 폼의 이메일 입력란을 제거했다.
- 입금 안내/환불 규정 문구 배치, 빈 줄 정리, 문구 표기 수정, 선택 해제 UX까지 세부적으로 조정했다.
- `web_portal/content/apply-content.js` - 월별 홍보 문구를 따로 관리하는 콘텐츠 파일 추가
- `web_portal/apply/index.html` - 폼 구조, 안내 문구, 항목 번호, 선택 UX 조정
- `web_portal/feedback/index.html` - 이메일 없는 피드백 폼으로 단순화
- `web_portal/api/feedback.js` - 피드백 저장 스키마를 새 폼 구조에 맞게 수정

---

### 5. Google Sheets 기반 과거 신청 데이터를 Airtable에 반영하고, 집계 구조를 통합 테이블 방향으로 재정리

```text
https://docs.google.com/spreadsheets/d/1d2ECYwdga35UuXLsazXDd2CaCJh5hiOpnWIdpLgp9iM/edit?usp=sharing 이 링크에 있는 사람들의 데이터를 airtable에 입력해줘.

1월 링크 : https://docs.google.com/spreadsheets/d/1Pbvjy-lh26Hpxpu5T1g-GBp_twEfdmvrTLWmfO7N6SU/edit?gid=1823692438#gid=1823692438

2월 : https://docs.google.com/spreadsheets/d/1gjVLvXxgd0VIpX59MYDzycTNXqNr7BYN97Kbf94_XPQ/edit?gid=176150069#gid=176150069

테이블 '웨비나_월별집계'에 합계가 반영되지 않았어. 다른 테이블들과 연동시켜줘

코딩이 아니라 실제로 airtable 기능으로 상호 연동하게 하려면?

매월_웨비나접수 테이블에 합계행을 두고 그것을 웨비나_월별집계와 연결하는 것은 어때?

제가 추천하는 가장 합리적이고, 지속가능한 방식을 다시 한번 정리해줘.

좋아. 그럼 너의 추천대로 변경해줘.
```

**Claude Code 작업:**
- Airtable API 토큰과 베이스 구조를 확인해 기존 3월 신청 테이블 운영 흐름을 손봤다.
- 월별 테이블 운영 방식, 월별 집계 방식, 통합 테이블 구조에 대한 여러 대안을 비교한 뒤 방향을 정리했다.

**Codex CLI 작업:**
- 월별 테이블을 계속 늘리는 방식보다 `웨비나접수_통합`을 실제 저장소로 삼고, 앱/대시보드/웹 포털이 같은 저장 대상을 보게 맞추는 방향이 더 지속 가능하다고 판단했다.
- 저녁 작업에서 통합 테이블 기준으로 앱과 Airtable 연동 코드를 바꾸기 시작했고, 집계 테이블이 이 통합 데이터에서 합계를 읽도록 재설계했다.
- `main.py` - 월별 테이블 전제 제거를 위한 구조 개편 시작
- `modules/airtable_client.py` - 통합/집계 테이블 기준으로 데이터 접근 방향 정리
- `web_portal/api/apply.js` - 저장 대상을 통합 기준으로 옮길 수 있도록 조정

---

## 커밋 히스토리

| 날짜 | 커밋 | 설명 |
|------|------|------|
| 03/31 | `-` | 이 작업 폴더는 Git 저장소가 아니어서 커밋 히스토리를 남기지 못함 |

---

## 기술 스택

- **Frontend**: HTML, CSS, Vanilla JavaScript
- **Backend**: Python, tkinter, requests, Airtable API, Vercel Serverless Functions
- **Deployment**: PyInstaller, Vercel

---

## 주요 기능

1. **월별 웨비나 운영 자동화**
   - EXE에서 발송 관리와 설정을 담당하고, Airtable을 운영 데이터 저장소로 사용

2. **공개 신청/피드백 웹 포털**
   - 신청 페이지와 피드백 페이지를 별도 웹 포털로 분리하고 Vercel에 배포

3. **월별 비교 집계 구조**
   - `웨비나_월별집계` 테이블을 두고 월별 신청/입금 결과를 비교할 수 있도록 정리

4. **콘텐츠 분리형 신청 페이지**
   - 웨비나 홍보 문구를 코드와 분리해 매달 운영자가 쉽게 수정할 수 있게 구성
