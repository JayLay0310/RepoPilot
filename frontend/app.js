const apiBaseInput = document.querySelector("#apiBase");
const healthBtn = document.querySelector("#healthBtn");
const healthText = document.querySelector("#healthText");
const repoName = document.querySelector("#repoName");
const repoPath = document.querySelector("#repoPath");
const registerBtn = document.querySelector("#registerBtn");
const refreshReposBtn = document.querySelector("#refreshReposBtn");
const repoSelect = document.querySelector("#repoSelect");
const queryInput = document.querySelector("#queryInput");
const createTaskBtn = document.querySelector("#createTaskBtn");
const taskStatus = document.querySelector("#taskStatus");
const taskStage = document.querySelector("#taskStage");
const taskProgress = document.querySelector("#taskProgress");
const progressBar = document.querySelector("#progressBar");
const reportView = document.querySelector("#reportView");
const sectionList = document.querySelector("#sectionList");

let activeTimer = null;

healthBtn.addEventListener("click", checkHealth);
registerBtn.addEventListener("click", registerRepo);
refreshReposBtn.addEventListener("click", loadRepos);
createTaskBtn.addEventListener("click", createTask);

loadRepos().catch(showError);

function apiBase() {
  return apiBaseInput.value.replace(/\/$/, "");
}

async function request(path, options = {}) {
  const response = await fetch(`${apiBase()}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `HTTP ${response.status}`);
  }
  return response.json();
}

async function checkHealth() {
  const data = await request("/health");
  healthText.textContent = `${data.service}: ${data.status}`;
}

async function registerRepo() {
  const name = repoName.value.trim();
  const path = repoPath.value.trim();
  if (!name || !path) {
    showError(new Error("请填写仓库名称和路径。"));
    return;
  }
  await request("/api/repos/register", {
    method: "POST",
    body: JSON.stringify({ name, path }),
  });
  await loadRepos();
}

async function loadRepos() {
  const repos = await request("/api/repos/list");
  repoSelect.innerHTML = "";
  if (!repos.length) {
    repoSelect.innerHTML = '<option value="">暂无仓库</option>';
    return;
  }
  for (const repo of repos) {
    const option = document.createElement("option");
    option.value = repo.id;
    option.textContent = `${repo.name} - ${repo.path}`;
    repoSelect.appendChild(option);
  }
}

async function createTask() {
  const repoId = repoSelect.value;
  const query = queryInput.value.trim();
  if (!repoId || !query) {
    showError(new Error("请选择仓库并填写分析需求。"));
    return;
  }
  const task = await request("/api/tasks/", {
    method: "POST",
    body: JSON.stringify({ repo_id: repoId, query }),
  });
  updateStatus(task);
  pollTask(task.id);
}

function pollTask(taskId) {
  if (activeTimer) {
    clearInterval(activeTimer);
  }
  activeTimer = setInterval(async () => {
    try {
      const task = await request(`/api/tasks/${taskId}`);
      updateStatus(task);
      if (task.status === "completed" || task.status === "failed") {
        clearInterval(activeTimer);
        activeTimer = null;
        if (task.report) {
          renderReport(task.report);
        }
      }
    } catch (error) {
      clearInterval(activeTimer);
      activeTimer = null;
      showError(error);
    }
  }, 1000);
}

function updateStatus(task) {
  taskStatus.textContent = task.status || "unknown";
  taskStage.textContent = task.stage || "running";
  const progress = Number(task.progress || 0);
  taskProgress.textContent = `${progress}%`;
  progressBar.style.width = `${Math.max(0, Math.min(100, progress))}%`;
}

function renderReport(markdown) {
  const html = window.marked ? window.marked.parse(markdown) : `<pre>${escapeHtml(markdown)}</pre>`;
  reportView.innerHTML = html;
  renderSections();
  renderMermaid();
}

function renderSections() {
  const headings = reportView.querySelectorAll("h1, h2");
  sectionList.innerHTML = "";
  headings.forEach((heading, index) => {
    const id = `section-${index}`;
    heading.id = id;
    const button = document.createElement("button");
    button.className = "section-link";
    button.textContent = heading.textContent;
    button.addEventListener("click", () => heading.scrollIntoView({ behavior: "smooth", block: "start" }));
    sectionList.appendChild(button);
  });
}

async function renderMermaid() {
  const mermaidBlocks = [...reportView.querySelectorAll("code.language-mermaid")];
  if (!mermaidBlocks.length) {
    return;
  }
  try {
    const mermaid = await import("https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs");
    mermaid.default.initialize({ startOnLoad: false, theme: "default" });
    for (const [index, code] of mermaidBlocks.entries()) {
      const source = code.textContent;
      const container = document.createElement("div");
      container.className = "mermaid";
      const result = await mermaid.default.render(`graph-${index}`, source);
      container.innerHTML = result.svg;
      code.closest("pre").replaceWith(container);
    }
  } catch {
    // Mermaid is optional; keep raw code blocks when CDN import is unavailable.
  }
}

function showError(error) {
  reportView.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
