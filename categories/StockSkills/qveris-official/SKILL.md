---
name: qveris-official
description: "Official QVeris capability discovery skill for finance workflows. Discovers available QVeris APIs and tools using your configured API key, including stock, sector, market, and capital-flow endpoints; coverage depends on the account, credits, and currently exposed upstream tools."
version: 0.1.0
metadata:
  openclaw:
    emoji: "📈"
    requires:
      bins: [node]
      env: [QVERIS_API_KEY]
      config: []
---

# QVeris Official

## Overview

QVeris Official is a discovery-first skill for the QVeris platform. It helps the agent query QVeris for the tools and endpoints currently available to the authenticated account, especially around finance and stock-market workflows such as market data, sector views, capital-flow analysis, and related API discovery.

This skill does **not** guarantee that a specific endpoint exists. Actual coverage depends on the upstream QVeris catalog, the API key's permissions, account credits, rate limits, and whatever tools QVeris exposes at query time.

## When to Use This Skill

Use this skill when:
- You want to discover what QVeris finance or stock APIs are currently available
- You need to inspect capital-flow, stock, sector, or market-analysis related tool options
- You want an official QVeris-backed capability discovery step before building a finance workflow
- You need to verify whether a desired QVeris endpoint is exposed to the current account

## Notes

- Requires `QVERIS_API_KEY`
- Discovery responses may include account-specific tools and remaining credits
- QVeris uses credits and rate limits; avoid unnecessary repeated discovery calls
- Some discovered tools may be symbol-specific rather than market-wide ranking endpoints
