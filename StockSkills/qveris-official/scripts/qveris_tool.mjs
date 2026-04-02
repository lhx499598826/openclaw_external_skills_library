#!/usr/bin/env node
import { readQverisApiKey } from "./qveris_env.mjs";
import { callTool, discoverTools, getBaseUrl, inspectToolsByIds } from "./qveris_client.mjs";

function normalizeLegacyArgs(rawArgs) {
  const args = [...rawArgs];
  const warnings = new Set();
  const commandAliases = { search: "discover", execute: "call", invoke: "call", "get-by-ids": "inspect" };
  if (args.length > 0 && commandAliases[args[0]]) {
    warnings.add(`'${args[0]}' is deprecated; use '${commandAliases[args[0]]}' instead.`);
    args[0] = commandAliases[args[0]];
  }
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--search-id") {
      warnings.add("'--search-id' is deprecated; use '--discovery-id' instead.");
      args[i] = "--discovery-id";
    }
  }
  return { args, warnings: [...warnings] };
}

function displayDiscoveryResults(result) {
  const discoveryId = result.search_id ?? "N/A";
  const tools = result.results ?? [];
  const total = result.total ?? tools.length;
  console.log(`\nDiscovery ID: ${discoveryId}`);
  console.log(`Found ${total} tools\n`);
  if (tools.length === 0) return console.log("No tools found.");
  for (let i = 0; i < tools.length; i++) {
    const tool = tools[i];
    const toolId = tool.tool_id ?? "N/A";
    const name = tool.name ?? "N/A";
    const desc = tool.description ?? "N/A";
    const stats = tool.stats ?? {};
    let successRate = stats.success_rate ?? "N/A";
    let avgTime = stats.avg_execution_time_ms ?? "N/A";
    if (typeof successRate === "number") successRate = `${Math.round(successRate * 100)}%`;
    if (typeof avgTime === "number") avgTime = `${avgTime.toFixed(1)}ms`;
    console.log(`[${i + 1}] ${name}`);
    console.log(`    ID: ${toolId}`);
    console.log(`    ${desc.length > 100 ? desc.slice(0, 100) + "..." : desc}`);
    console.log(`    Success: ${successRate} | Avg Time: ${avgTime}`);
    const params = tool.params ?? [];
    if (params.length > 0) {
      const required = params.filter((p) => p.required).map((p) => p.name);
      const optional = params.filter((p) => !p.required).map((p) => p.name);
      if (required.length > 0) console.log(`    Required: ${required.join(", ")}`);
      if (optional.length > 0) console.log(`    Optional: ${optional.slice(0, 5).join(", ")}${optional.length > 5 ? "..." : ""}`);
    }
    const examples = tool.examples ?? {};
    if (examples.sample_parameters) console.log(`    Example: ${JSON.stringify(examples.sample_parameters)}`);
    console.log();
  }
}

function displayCallResult(result) {
  const success = result.success ?? false;
  const execTime = result.elapsed_time_ms ?? "N/A";
  const cost = result.cost ?? 0;
  console.log(`\n${success ? "Success" : "Failed"}`);
  console.log(`Time: ${execTime}ms | Cost: ${cost}`);
  if (!success) console.log(`Error: ${result.error_message ?? "Unknown error"}`);
  const data = result.result ?? {};
  if (Object.keys(data).length > 0) {
    console.log("\nResult:");
    console.log(JSON.stringify(data, null, 2));
  }
}

function printUsage() {
  const baseUrl = getBaseUrl();
  console.log(`QVeris Capability Discovery & Tool Calling CLI\n\nUsage:\n  node scripts/qveris_tool.mjs discover <query> [options]\n  node scripts/qveris_tool.mjs call <tool_id> --discovery-id <id> [options]\n  node scripts/qveris_tool.mjs inspect <tool_id> [tool_id2 ...] [options]\n\nCommands:\n  discover <query>\n  call <tool_id>\n  inspect <id> [id2 ...]\n\nNotes:\n  all requests are routed to ${baseUrl}`);
}

function parseArgs(argv) {
  const normalized = normalizeLegacyArgs(argv.slice(2));
  const args = normalized.args;
  if (args.length === 0 || args.includes("--help") || args.includes("-h")) {
    printUsage();
    process.exit(0);
  }
  for (const warning of normalized.warnings) console.error(`Deprecated: ${warning}`);
  const command = args[0];
  const parsed = { command, json: false };
  if (command === "discover") {
    if (args.length < 2) process.exit(1);
    parsed.query = args[1]; parsed.limit = 10; parsed.timeout = 30;
    for (let i = 2; i < args.length; i++) {
      if (args[i] === "--limit" && i + 1 < args.length) parsed.limit = parseInt(args[++i], 10);
      else if (args[i] === "--timeout" && i + 1 < args.length) parsed.timeout = parseInt(args[++i], 10);
      else if (args[i] === "--json") parsed.json = true;
    }
  } else if (command === "call") {
    if (args.length < 2) process.exit(1);
    parsed.toolId = args[1]; parsed.discoveryId = null; parsed.params = "{}"; parsed.maxSize = 20480; parsed.timeout = 60;
    for (let i = 2; i < args.length; i++) {
      if (args[i] === "--discovery-id" && i + 1 < args.length) parsed.discoveryId = args[++i];
      else if (args[i] === "--params" && i + 1 < args.length) parsed.params = args[++i];
      else if (args[i] === "--max-size" && i + 1 < args.length) parsed.maxSize = parseInt(args[++i], 10);
      else if (args[i] === "--timeout" && i + 1 < args.length) parsed.timeout = parseInt(args[++i], 10);
      else if (args[i] === "--json") parsed.json = true;
    }
    if (!parsed.discoveryId) process.exit(1);
  } else if (command === "inspect") {
    if (args.length < 2) process.exit(1);
    parsed.toolIds = []; parsed.discoveryId = null; parsed.timeout = 30;
    for (let i = 1; i < args.length; i++) {
      if (args[i] === "--discovery-id" && i + 1 < args.length) parsed.discoveryId = args[++i];
      else if (args[i] === "--timeout" && i + 1 < args.length) parsed.timeout = parseInt(args[++i], 10);
      else if (args[i] === "--json") parsed.json = true;
      else if (!args[i].startsWith("--")) parsed.toolIds.push(args[i]);
    }
    if (parsed.toolIds.length === 0) process.exit(1);
  } else {
    process.exit(1);
  }
  return parsed;
}

async function main() {
  const args = parseArgs(process.argv);
  const apiKey = readQverisApiKey();
  try {
    if (args.command === "discover") {
      const result = await discoverTools({ apiKey, query: args.query, limit: args.limit, timeoutMs: args.timeout * 1000 });
      if (args.json) console.log(JSON.stringify(result, null, 2)); else displayDiscoveryResults(result);
    } else if (args.command === "call") {
      let params; try { params = JSON.parse(args.params); } catch { process.exit(1); }
      const result = await callTool({ apiKey, toolId: args.toolId, discoveryId: args.discoveryId, parameters: params, maxResponseSize: args.maxSize, timeoutMs: args.timeout * 1000 });
      if (args.json) console.log(JSON.stringify(result, null, 2)); else displayCallResult(result);
    } else if (args.command === "inspect") {
      const result = await inspectToolsByIds({ apiKey, toolIds: args.toolIds, discoveryId: args.discoveryId, timeoutMs: args.timeout * 1000 });
      if (args.json) console.log(JSON.stringify(result, null, 2)); else displayDiscoveryResults(result);
    }
  } catch (e) {
    console.error(`Error: ${e.name === "AbortError" ? "Request timed out" : e.message}`);
    process.exit(1);
  }
}

main();
