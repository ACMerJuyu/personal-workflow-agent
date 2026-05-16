const statusEl = document.querySelector("#api-status");
const messageInput = document.querySelector("#message");
const plannerInput = document.querySelector("#planner");
const commitInput = document.querySelector("#commit");
const resetInput = document.querySelector("#reset-db");
const runButton = document.querySelector("#run-button");
const runIdEl = document.querySelector("#run-id");
const resultTitleEl = document.querySelector("#result-title");
const resultBulletsEl = document.querySelector("#result-bullets");
const traceCountEl = document.querySelector("#trace-count");
const traceListEl = document.querySelector("#trace-list");
const emailsListEl = document.querySelector("#emails-list");
const calendarListEl = document.querySelector("#calendar-list");
const todosListEl = document.querySelector("#todos-list");
const pendingCountEl = document.querySelector("#pending-count");
const pendingActionsListEl = document.querySelector("#pending-actions-list");
const historyListEl = document.querySelector("#history-list");
const refreshHistoryButton = document.querySelector("#refresh-history");

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }

  return response.json();
}

async function checkHealth() {
  try {
    await api("/health");
    statusEl.textContent = "API Online";
    statusEl.className = "status-pill ok";
  } catch (error) {
    statusEl.textContent = "API Offline";
    statusEl.className = "status-pill error";
  }
}

async function runAgent() {
  runButton.disabled = true;
  runButton.textContent = "Running...";

  try {
    const payload = await api("/agent/chat", {
      method: "POST",
      body: JSON.stringify({
        message: messageInput.value,
        planner: plannerInput.value,
        commit: commitInput.checked,
        reset_db: resetInput.checked,
      }),
    });

    renderResult(payload);
    await refreshData();
  } catch (error) {
    resultTitleEl.textContent = "Request failed";
    resultBulletsEl.innerHTML = `<li>${escapeHtml(error.message)}</li>`;
  } finally {
    runButton.disabled = false;
    runButton.textContent = "Run Agent";
  }
}

function renderResult(payload) {
  runIdEl.textContent = `Run #${payload.run_id} | ${payload.mode} | ${payload.intent} | ${payload.planner_mode}`;
  resultTitleEl.textContent = payload.title;
  resultBulletsEl.innerHTML = payload.bullets
    .map((bullet) => `<li>${escapeHtml(bullet)}</li>`)
    .join("");

  const steps = payload.react_steps && payload.react_steps.length
    ? payload.react_steps
    : payload.trace.map((call) => ({
        kind: "action",
        content: `Call ${call.name}.`,
        tool_name: call.name,
        arguments: call.arguments,
        observation: call.result,
      }));

  traceCountEl.textContent = `${steps.length} steps`;
  traceListEl.innerHTML = steps
    .map(
      (step, index) => `
        <article class="trace-card react-step ${escapeHtml(step.kind)}">
          <div class="react-step-header">
            <span>${index + 1}</span>
            <h4>${escapeHtml(formatStepTitle(step))}</h4>
          </div>
          <p>${escapeHtml(step.content)}</p>
          ${renderStepDetails(step)}
        </article>
      `,
    )
    .join("");
}

function formatStepTitle(step) {
  if (step.kind === "action" && step.tool_name) {
    return `Action: ${step.tool_name}`;
  }
  return step.kind.charAt(0).toUpperCase() + step.kind.slice(1);
}

function renderStepDetails(step) {
  if (step.kind !== "action" && step.kind !== "observation") {
    return "";
  }

  const details = {};
  if (step.arguments && Object.keys(step.arguments).length) {
    details.arguments = step.arguments;
  }
  if (step.observation !== null && step.observation !== undefined) {
    details.observation = step.observation;
  }

  if (!Object.keys(details).length) {
    return "";
  }

  return `<pre>${escapeHtml(JSON.stringify(details, null, 2))}</pre>`;
}

async function refreshData() {
  const [emails, calendar, todos, pendingActions, history] = await Promise.all([
    api("/emails"),
    api("/calendar"),
    api("/todos"),
    api("/agent/pending-actions"),
    api("/agent/runs"),
  ]);

  renderEmails(emails);
  renderCalendar(calendar);
  renderTodos(todos);
  renderPendingActions(pendingActions);
  renderHistory(history);
}

function renderEmails(emails) {
  emailsListEl.innerHTML = emails
    .map(
      (email) => `
        <article class="data-card">
          <h4>${escapeHtml(email.subject)}</h4>
          <p>${escapeHtml(email.sender)} | ${escapeHtml(email.priority)} | due ${escapeHtml(email.deadline)}</p>
        </article>
      `,
    )
    .join("");
}

function renderCalendar(events) {
  calendarListEl.innerHTML = events
    .map(
      (event) => `
        <article class="data-card">
          <h4>${escapeHtml(event.title)}</h4>
          <p>${escapeHtml(event.date)} | ${escapeHtml(event.start)}-${escapeHtml(event.end)}</p>
        </article>
      `,
    )
    .join("");
}

function renderTodos(todos) {
  todosListEl.innerHTML = todos
    .map(
      (todo) => `
        <article class="data-card">
          <h4>${escapeHtml(todo.title)}</h4>
          <p>due ${escapeHtml(todo.due)} | ${escapeHtml(todo.priority)}</p>
        </article>
      `,
    )
    .join("");
}

function renderHistory(runs) {
  historyListEl.innerHTML = runs
    .map(
      (run) => `
        <article class="history-card">
          <h4>#${run.id} ${escapeHtml(run.final_title)}</h4>
          <p>${escapeHtml(run.intent)} | ${escapeHtml(run.mode)} | ${escapeHtml(run.created_at)}</p>
        </article>
      `,
    )
    .join("");
}

function renderPendingActions(actions) {
  pendingCountEl.textContent = `${actions.length} pending`;

  if (!actions.length) {
    pendingActionsListEl.innerHTML = `
      <article class="approval-card empty-state">
        <p>No pending action.</p>
      </article>
    `;
    return;
  }

  pendingActionsListEl.innerHTML = actions
    .map(
      (action) => `
        <article class="approval-card">
          <div>
            <h4>${escapeHtml(action.description)}</h4>
            <p>${escapeHtml(action.action_type)} | run #${escapeHtml(action.run_id)} | ${escapeHtml(action.created_at)}</p>
          </div>
          <div class="approval-actions">
            <button data-action="approve" data-id="${action.id}">Approve</button>
            <button class="reject-button" data-action="reject" data-id="${action.id}">Reject</button>
          </div>
        </article>
      `,
    )
    .join("");
}

async function approveAction(actionId) {
  await api(`/agent/actions/${actionId}/approve`, { method: "POST" });
  await refreshData();
}

async function rejectAction(actionId) {
  await api(`/agent/actions/${actionId}/reject`, { method: "POST" });
  await refreshData();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

runButton.addEventListener("click", runAgent);
messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    runAgent();
  }
});
refreshHistoryButton.addEventListener("click", refreshData);
pendingActionsListEl.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-action]");
  if (!button) {
    return;
  }

  button.disabled = true;
  if (button.dataset.action === "approve") {
    await approveAction(button.dataset.id);
  } else {
    await rejectAction(button.dataset.id);
  }
});

checkHealth();
refreshData();
