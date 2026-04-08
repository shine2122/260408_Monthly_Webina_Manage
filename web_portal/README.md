# 웹 신청/피드백 포털

추천 구조는 `Vercel + Airtable` 입니다.

- `Airtable만` 쓰면 폼은 빨리 만들 수 있지만, 디자인 제어가 약합니다.
- `Vercel + Airtable` 조합이면 공개 링크는 고정하고, 저장은 Airtable에 유지할 수 있습니다.
- 이 프로젝트는 신청 저장을 통합 테이블 하나로 운영하고, 필요한 내부 분류만 Airtable 필드로 관리합니다.

## 권장 링크 구조

- 신청 폼: `https://<your-domain>/apply`
- 피드백 폼: `https://<your-domain>/feedback`

신청 페이지 문구와 일정은 `apply-content.js`에서 관리하고, 저장 시 필요한 내부 분류값은 API에서 처리합니다.

## Airtable 준비

신청은 통합 테이블 `웨비나접수_통합`에 저장됩니다.
각 신청 레코드는 `웨비나_월별집계`의 해당 웨비나 레코드와 링크되어 관계형으로 연결됩니다.

필수 필드:

- `성함`
- `활동명`
- `이메일`
- `휴대폰번호`
- `수준`
- `개인정보동의`
- `입금완료`
- `발송상태`

피드백은 단일 테이블 `웨비나_피드백`에 저장하는 구성을 권장합니다.

필수 필드:

- `웨비나명`
- `성함`
- `이메일`
- `만족도`
- `가장 좋았던 점`
- `다음에 듣고 싶은 주제`
- `자유 의견`

로컬 파이썬 앱 설정이 이미 맞아 있다면 아래 스크립트로 필요한 Airtable 테이블을 한 번에 만들 수 있습니다.

```powershell
python .\bootstrap_web_airtable.py
```

## Vercel 환경 변수

`web_portal` 폴더를 별도 프로젝트로 Vercel에 배포하고 아래 환경 변수를 넣으세요.

- `AIRTABLE_API_KEY`
- `AIRTABLE_BASE_ID`
- `AIRTABLE_REGISTRATION_TABLE`
- `AIRTABLE_SUMMARY_TABLE`
- `AIRTABLE_FEEDBACK_TABLE`

예시:

- `AIRTABLE_REGISTRATION_TABLE=웨비나접수_통합`
- `AIRTABLE_SUMMARY_TABLE=웨비나_월별집계`
- `AIRTABLE_FEEDBACK_TABLE=웨비나_피드백`

## 배포

`web_portal` 폴더에서 배포하면 됩니다.

```powershell
cd .\web_portal
vercel
```

배포 후 바로 사용할 시작 링크:

- 신청 링크: `https://<your-domain>/apply`
- 피드백 링크: `https://<your-domain>/feedback`

## 신청 페이지 문구 수정

신청 페이지의 홍보 문구와 강사 정보는 아래 파일에서 직접 수정할 수 있습니다.

- [apply-content.js](C:\Users\5800x\Documents\Claude\CriAItiveLab\Education\Monthly_Webina_Manage\web_portal\content\apply-content.js)

수정 항목:

- `title`
- `heroCopy`
- `scheduleDate`
- `scheduleFormat`
- `scheduleCapacity`
- `speakers`
- `recommendedFor`
- `chatNotice`
- `paymentCopy`

파일을 수정한 뒤 다시 배포하면 신청 페이지에 반영됩니다.
