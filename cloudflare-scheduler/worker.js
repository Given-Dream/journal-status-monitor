const DEFAULT_OWNER = "Xuecheng377";
const DEFAULT_REPO = "journal-status-monitor";
const DEFAULT_WORKFLOW = "monitor.yml";
const DEFAULT_REF = "main";

const DAILY_REPORT_HOUR = 8;
const NORMAL_HOURS = new Set([11, 12, 14, 17, 20, 22]);
const FALLBACK_MINUTES = new Set([17, 27, 37]);

function beijingTime(date = new Date()) {
  return new Date(date.getTime() + 8 * 60 * 60 * 1000);
}

function formatBeijingTime(date = new Date()) {
  const bj = beijingTime(date);
  return `${bj.getUTCFullYear()}-${String(bj.getUTCMonth() + 1).padStart(2, "0")}-${String(
    bj.getUTCDate(),
  ).padStart(2, "0")} ${String(bj.getUTCHours()).padStart(2, "0")}:${String(
    bj.getUTCMinutes(),
  ).padStart(2, "0")}:${String(bj.getUTCSeconds()).padStart(2, "0")}`;
}

function resolveMode(date = new Date()) {
  const bj = beijingTime(date);
  const hour = bj.getUTCHours();
  const minute = bj.getUTCMinutes();

  if (!FALLBACK_MINUTES.has(minute)) {
    return null;
  }
  if (hour === DAILY_REPORT_HOUR) {
    return "daily_report";
  }
  if (NORMAL_HOURS.has(hour)) {
    return "normal";
  }
  return null;
}

async function dispatchWorkflow(env, mode) {
  const owner = env.GITHUB_OWNER || DEFAULT_OWNER;
  const repo = env.GITHUB_REPO || DEFAULT_REPO;
  const workflow = env.GITHUB_WORKFLOW || DEFAULT_WORKFLOW;
  const ref = env.GITHUB_REF || DEFAULT_REF;
  const token = env.GITHUB_TOKEN;

  if (!token) {
    throw new Error("Missing GITHUB_TOKEN secret.");
  }

  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`,
    {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        "User-Agent": "journal-status-external-scheduler",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({
        ref,
        inputs: { mode },
      }),
    },
  );

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`GitHub dispatch failed: ${response.status} ${body}`);
  }
}

export default {
  async scheduled(event, env, ctx) {
    const mode = resolveMode();
    if (!mode) {
      console.log("Outside configured Beijing trigger windows; skipped.");
      return;
    }

    ctx.waitUntil(dispatchWorkflow(env, mode));
    console.log(`Triggered GitHub workflow_dispatch with mode=${mode}.`);
  },

  async fetch(request, env) {
    const mode = resolveMode();
    return Response.json({
      ok: true,
      beijingTime: formatBeijingTime(),
      modeIfScheduledNow: mode,
      repository: `${env.GITHUB_OWNER || DEFAULT_OWNER}/${env.GITHUB_REPO || DEFAULT_REPO}`,
      workflow: env.GITHUB_WORKFLOW || DEFAULT_WORKFLOW,
    });
  },
};
