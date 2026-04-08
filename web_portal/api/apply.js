function parseBody(req) {
  if (!req.body) return {};
  if (typeof req.body === "string") return JSON.parse(req.body);
  return req.body;
}

function normalizeMonthLabel(rawMonth) {
  const value = String(rawMonth || "").trim();

  const labelMatch = /^([1-9]|1[0-2])월$/.exec(value);
  if (labelMatch) {
    return `${Number(labelMatch[1])}월`;
  }

  const isoMatch = /^(\d{4})-(0[1-9]|1[0-2])$/.exec(value);
  if (isoMatch) {
    return `${Number(isoMatch[2])}월`;
  }

  return null;
}

async function findOrCreateWebinarSummary({ apiKey, baseId, summaryTableName, monthLabel }) {
  const query = new URLSearchParams({
    filterByFormula: `{기준월}='${monthLabel}'`,
    maxRecords: "1",
  });

  const listRes = await fetch(
    `https://api.airtable.com/v0/${encodeURIComponent(baseId)}/${encodeURIComponent(summaryTableName)}?${query.toString()}`,
    {
      headers: {
        Authorization: `Bearer ${apiKey}`,
      },
    }
  );

  if (!listRes.ok) {
    throw new Error(await listRes.text());
  }

  const listData = await listRes.json();
  if (listData.records?.length) {
    return listData.records[0].id;
  }

  const createRes = await fetch(
    `https://api.airtable.com/v0/${encodeURIComponent(baseId)}/${encodeURIComponent(summaryTableName)}`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        fields: {
          "기준월": monthLabel,
        },
      }),
    }
  );

  if (!createRes.ok) {
    throw new Error(await createRes.text());
  }

  const created = await createRes.json();
  return created.id;
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.status(405).json({ ok: false, message: "Method not allowed" });
    return;
  }

  try {
    const body = parseBody(req);
    const apiKey = process.env.AIRTABLE_API_KEY;
    const baseId = process.env.AIRTABLE_BASE_ID;
    const tableName = process.env.AIRTABLE_REGISTRATION_TABLE || "웨비나접수_통합";
    const summaryTableName = process.env.AIRTABLE_SUMMARY_TABLE || "웨비나_월별집계";
    const monthLabel = normalizeMonthLabel(body.month);

    if (!apiKey || !baseId) {
      res.status(500).json({ ok: false, message: "Airtable 환경 변수가 설정되지 않았습니다." });
      return;
    }

    if (!monthLabel) {
      res.status(400).json({ ok: false, message: "기준월은 1월부터 12월 사이에서 선택해 주세요." });
      return;
    }

    if (!body.name || !body.email || !body.phone || !body.level || !body.privacyAgree || !body.paymentConfirm) {
      res.status(400).json({ ok: false, message: "필수 항목이 누락되었습니다." });
      return;
    }

    const webinarRecordId = await findOrCreateWebinarSummary({
      apiKey,
      baseId,
      summaryTableName,
      monthLabel,
    });

    const airtableRes = await fetch(
      `https://api.airtable.com/v0/${encodeURIComponent(baseId)}/${encodeURIComponent(tableName)}`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          fields: {
            "기준월": monthLabel,
            "성함": body.name,
            "활동명": body.nickname || "",
            "이메일": body.email,
            "휴대폰번호": body.phone,
            "수준": body.level,
            "개인정보동의": body.privacyAgree,
            "입금확인": body.paymentConfirm === "네",
            "입금완료": false,
            "발송상태": "미발송",
            "웨비나_월별집계": [webinarRecordId],
          },
        }),
      }
    );

    if (!airtableRes.ok) {
      const errorText = await airtableRes.text();
      res.status(airtableRes.status).json({ ok: false, message: errorText });
      return;
    }

    res.status(200).json({ ok: true, message: "신청이 접수되었습니다." });
  } catch (error) {
    res.status(500).json({ ok: false, message: error.message || "신청 처리 중 오류가 발생했습니다." });
  }
}
