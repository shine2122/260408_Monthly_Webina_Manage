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

  return value || null;
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
    const tableName = process.env.AIRTABLE_FEEDBACK_TABLE || "웨비나_피드백";

    if (!apiKey || !baseId) {
      res.status(500).json({ ok: false, message: "Airtable 환경 변수가 설정되지 않았습니다." });
      return;
    }

    const monthLabel = normalizeMonthLabel(body.month);

    if (!monthLabel || !body.name || !body.rating) {
      res.status(400).json({ ok: false, message: "필수 항목이 누락되었습니다." });
      return;
    }

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
            "웨비나명": body.title || "",
            "성함": body.name,
            "만족도": Number(body.rating),
            "가장 좋았던 점": body.bestPart || "",
            "다음에 듣고 싶은 주제": body.nextTopic || "",
            "자유 의견": body.comment || "",
          },
        }),
      }
    );

    if (!airtableRes.ok) {
      const errorText = await airtableRes.text();
      res.status(airtableRes.status).json({ ok: false, message: errorText });
      return;
    }

    res.status(200).json({ ok: true, message: "피드백이 저장되었습니다." });
  } catch (error) {
    res.status(500).json({ ok: false, message: error.message || "피드백 저장 중 오류가 발생했습니다." });
  }
}
