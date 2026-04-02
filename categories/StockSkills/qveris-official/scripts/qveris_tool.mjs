import {discover} from './qveris_client.mjs';
const q=process.argv.slice(2).join(' ')||'stock tools';
discover(q).then(r=>console.log(JSON.stringify(r,null,2))).catch(err=>{ console.error(err.message); process.exit(1); });
