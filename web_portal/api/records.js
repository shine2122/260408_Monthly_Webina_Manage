export default async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');

  const apiKey = process.env.AIRTABLE_API_KEY;
  const baseId = process.env.AIRTABLE_BASE_ID;
  const tableName = req.query.table || process.env.AIRTABLE_REGISTRATION_TABLE || '웨비나접수_통합';
  const monthLabel = req.query.month || '';
  const monthField = req.query.monthField || '기준월';

  if (!apiKey || !baseId) {
    res.status(500).json({ ok: false, message: 'Airtable 환경 변수가 설정되지 않았습니다.' });
    return;
  }

  let allRecords = [];
  let offset = null;

  try {
    do {
      const url = new URL(`https://api.airtable.com/v0/${encodeURIComponent(baseId)}/${encodeURIComponent(tableName)}`);
      if (monthLabel && monthField) {
        url.searchParams.set('filterByFormula', `{${monthField}}='${monthLabel}'`);
      }
      if (offset) url.searchParams.set('offset', offset);

      const airtableRes = await fetch(url.toString(), {
        headers: { Authorization: `Bearer ${apiKey}` },
      });

      if (!airtableRes.ok) {
        const err = await airtableRes.json().catch(() => ({}));
        res.status(airtableRes.status).json({ ok: false, message: err?.error?.message || airtableRes.statusText });
        return;
      }

      const data = await airtableRes.json();
      allRecords = allRecords.concat(data.records || []);
      offset = data.offset || null;
    } while (offset);

    res.status(200).json({ ok: true, records: allRecords });
  } catch (error) {
    res.status(500).json({ ok: false, message: error.message });
  }
}
