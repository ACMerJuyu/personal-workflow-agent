const statusEl = document.querySelector("#api-status");
const messageInput = document.querySelector("#message");
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
  runIdEl.textContent = `Run #${payload.run_id} | ${payload.mode} | ${payload.intent}`;
  resultTitleEl.textContent = payload.title;
  resultBulletsEl.innerHTML = payload.bullets
    .map((bullet) => `<li>${escapeHtml(bullet)}</li>`)
    .join("");

  traceCountEl.textContent = `${payload.trace.length} calls`;
  traceListEl.innerHTML = payload.trace
    .map(
      (call, index) => `
        <article class="trace-card">
          <h4>${index + 1}. ${escapeHtml(call.name)}</h4>
          <pre>${escapeHtml(JSON.stringify({ arguments: call.arguments, result: call.result }, null, 2))}</pre>
        </article>
      `,
    )
    .join("");
}

async function refreshData() {
  const [emails, calendar, todos, history] = await Promise.all([
    api("/emails"),
    api("/calendar"),
    api("/todos"),
    api("/agent/runs"),
  ]);

  renderEmails(emails);
  renderCalendar(calendar);
  renderTodos(todos);
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

checkHealth();
refreshData();
