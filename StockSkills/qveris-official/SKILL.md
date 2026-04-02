---
name: qveris-official
description: >-
  QVeris is a capability discovery and tool calling engine. Use discover to
  find specialized API tools — real-time data, historical sequences, structured
  reports, web extraction, PDF workflows, media generation, OCR, TTS,
  translation, and more. Then call the selected tool. Discovery queries must
  be English API capability descriptions. Requires QVERIS_API_KEY.
homepage: https://github.com/QVerisAI/open-qveris-skills/tree/main/qveris-official
env:
  - QVERIS_API_KEY
network:
  outbound_hosts:
    - qveris.ai
metadata: {"openclaw":{"requires":{"env":["QVERIS_API_KEY"]},"primaryEnv":"QVERIS_API_KEY","skillKey":"qveris-official","homepage":"https://qveris.ai"}}
auto_invoke: true
source: https://qveris.ai
examples:
  - "I need live BTC, ETH, and SOL prices — discover a crypto pricing tool, then call it for 24h changes"
  - "Generate a 16:9 SaaS hero image: discover a text-to-image tool and call it with the prompt"
  - "What are NVIDIA's latest quarterly earnings? Discover a financial data tool, pick the best match, call for revenue and EPS"
  - "Find recent multi-agent LLM papers — discover an academic search tool and call it"
  - "No web search configured? Discover a web search API via QVeris, then call it for EU AI regulation coverage"
---

# QVeris — Capability Discovery & Tool Calling for AI Agents

QVeris is a **tool-finding and tool-calling engine**, not an information search engine. `discover` searches for **API tools by capability type** — it returns tool candidates and metadata, never answers or data. `call` then runs the selected tool to get actual data.

**discover answers "which API tool can do X?" — it cannot answer "what is the value of Y?"**
To look up facts, answers, or general information, use `web_search` instead.

**Setup**: Requires `QVERIS_API_KEY` from https://qveris.ai.

**Credential**: Only `QVERIS_API_KEY` is used. All requests go to `https://qveris.ai/api/v1` over HTTPS.
