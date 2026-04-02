import {getApiKey} from './qveris_env.mjs';
export async function discover(query){ return {query, apiKeyConfigured: !!getApiKey(), note: 'Stub client for external library packaging; execute from mounted runtime implementation if present.'}; }
