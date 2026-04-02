export function getApiKey(){ const k=process.env.QVERIS_API_KEY; if(!k) throw new Error('QVERIS_API_KEY is required'); return k; }
