const state = {
  token: localStorage.getItem("admin_token") || "",
  me: null,
  keywordGroups: [],
  teamRouting: [],
  teamRoutingLoaded: false,
  selectedTeamRoutingId: "",
  generalSettings: {
    scrapeFrequencyMinutes: 1440,
  },
};

let toastWrap = null;
let serverTimeTimer = null;
let serverTimeBaseMs = null;
let serverTimeLoadedAtMs = null;
let serverTimeZone = "";

const el = {
  loginView: document.getElementById("login-view"),
  dashboardView: document.getElementById("dashboard-view"),
  loginForm: document.getElementById("login-form"),
  loginUsername: document.getElementById("login-username"),
  loginPassword: document.getElementById("login-password"),
  loginError: document.getElementById("login-error"),
  userMeta: document.getElementById("user-meta"),
  serverTime: document.getElementById("server-time"),
  refreshBtn: document.getElementById("refresh-btn"),
  logoutBtn: document.getElementById("logout-btn"),

  keywordForm: document.getElementById("keyword-form"),
  kwName: document.getElementById("kw-name"),
  kwCategories: document.getElementById("kw-categories"),
  kwCategoryPick: document.getElementById("kw-category-pick"),
  kwCategoryAddBtn: document.getElementById("kw-category-add-btn"),
  kwLanguage: document.getElementById("kw-language"),
  kwActive: document.getElementById("kw-active"),
  kwSearch: document.getElementById("kw-search"),
  kwGroupFilter: document.getElementById("kw-group-filter"),
  kwLanguageFilter: document.getElementById("kw-language-filter"),
  keywordList: document.getElementById("keyword-list"),
  teamRoutingSelect: document.getElementById("team-routing-team-pick"),
  teamRoutingSummary: document.getElementById("team-routing-summary"),
  teamRoutingList: document.getElementById("team-routing-list"),

  recipientForm: document.getElementById("recipient-form"),
  rcEmail: document.getElementById("rc-email"),
  rcName: document.getElementById("rc-name"),
  rcTeams: document.getElementById("rc-teams"),
  rcTeamPick: document.getElementById("rc-team-pick"),
  rcTeamAddBtn: document.getElementById("rc-team-add-btn"),
  rcActive: document.getElementById("rc-active"),
  rcTest: document.getElementById("rc-test"),
  rcSearch: document.getElementById("rc-search"),
  rcTeamFilter: document.getElementById("rc-team-filter"),
  recipientList: document.getElementById("recipient-list"),

  runStatusFilter: document.getElementById("run-status-filter"),
  runRefreshBtn: document.getElementById("run-refresh-btn"),
  adminReportExportBtn: document.getElementById("admin-report-export-btn"),
  emailHistoryExportBtn: document.getElementById("email-history-export-btn"),
  runList: document.getElementById("run-list"),
  runSourceList: document.getElementById("run-source-list"),
  adminReportSummary: document.getElementById("admin-report-summary"),
  adminReportTeams: document.getElementById("admin-report-teams"),
  adminReportCampaigns: document.getElementById("admin-report-campaigns"),
  sourceHealthSummary: document.getElementById("source-health-summary"),
  sourceHealthList: document.getElementById("source-health-list"),
  resultJobSelect: document.getElementById("result-job-select"),
  resultLoadBtn: document.getElementById("result-load-btn"),
  resultSummary: document.getElementById("result-summary"),
  resultArticles: document.getElementById("result-articles"),
  resultLogs: document.getElementById("result-logs"),

  logLevelFilter: document.getElementById("log-level-filter"),
  logSearch: document.getElementById("log-search"),
  logRefreshBtn: document.getElementById("log-refresh-btn"),
  logList: document.getElementById("log-list"),

  runModeSelect: document.getElementById("run-mode-select"),
  runSourceSelect: document.getElementById("run-source-select"),
  runExecuteBtn: document.getElementById("run-execute-btn"),
  scraperJobId: document.getElementById("scraper-job-id"),
  scraperStopBtn: document.getElementById("scraper-stop-btn"),
  scraperRetryBtn: document.getElementById("scraper-retry-btn"),
  scraperMsg: document.getElementById("scraper-msg"),

  generalSettingsForm: document.getElementById("general-settings-form"),
  settingsResetBtn: document.getElementById("settings-reset-btn"),
  setFrequency: document.getElementById("set-frequency"),
  setMaxArticles: document.getElementById("set-max-articles"),
  scheduleForm: document.getElementById("schedule-form"),
  setCron: document.getElementById("set-cron"),
  setTimezone: document.getElementById("set-timezone"),
  setScheduleEnabled: document.getElementById("set-schedule-enabled"),
  sourceSettingsList: document.getElementById("source-settings-list"),

  emailHistorySearch: document.getElementById("email-history-search"),
  emailHistoryTeam: document.getElementById("email-history-team"),
  emailHistoryStatus: document.getElementById("email-history-status"),
  emailHistoryRefresh: document.getElementById("email-history-refresh"),
  emailHistoryList: document.getElementById("email-history-list"),
  emailDetailMeta: document.getElementById("email-detail-meta"),
  emailDetailDeliveries: document.getElementById("email-detail-deliveries"),
  emailDetailBody: document.getElementById("email-detail-body"),
  tabButtons: Array.from(document.querySelectorAll(".tab-btn")),
  contentSections: Array.from(document.querySelectorAll(".content-section")),
};

function splitCsv(value) {
  return value.split(",").map((v) => v.trim()).filter(Boolean);
}

function mergeCsvValues(...values) {
  const merged = [];
  const seen = new Set();
  for (const raw of values) {
    for (const value of splitCsv(String(raw || ""))) {
      const key = value.toLocaleLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      merged.push(value);
    }
  }
  return merged;
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function guessLanguageCode(keyword) {
  const value = String(keyword || "").trim();
  if (!value) return "ko";
  if (/[가-힣]/.test(value)) return "ko";
  if (/[A-Za-z]/.test(value)) return "en";
  return "ko";
}

function cronToTime(cronExpr) {
  const value = String(cronExpr || "").trim();
  const match = value.match(/^(\d{1,2})\s+(\d{1,2})\s+\*\s+\*\s+(?:\*|1-5|MON-FRI)$/i);
  if (!match) return "08:00";
  const minute = match[1].padStart(2, "0");
  const hour = match[2].padStart(2, "0");
  return `${hour}:${minute}`;
}

function timeToCron(timeValue) {
  const value = String(timeValue || "").trim();
  const match = value.match(/^(\d{2}):(\d{2})$/);
  if (!match) return "0 8 * * 1-5";
  const [, hour, minute] = match;
  return `${Number(minute)} ${Number(hour)} * * 1-5`;
}

function setupScheduleUi() {
  if (!el.scheduleForm) return;
  const labels = Array.from(el.scheduleForm.querySelectorAll("label"));
  if (labels[0]) labels[0].textContent = "평일 실행 시간";
  if (el.setCron) {
    el.setCron.type = "time";
    if (!el.setCron.value) el.setCron.value = "08:00";
  }
  if (el.setTimezone) {
    const timezoneLabel = el.setTimezone.previousElementSibling;
    if (timezoneLabel && timezoneLabel.tagName === "LABEL") {
      timezoneLabel.remove();
    }
    el.setTimezone.remove();
  }
  const checklineLabel = el.scheduleForm.querySelector(".checkline");
  if (checklineLabel) {
    checklineLabel.lastChild.textContent = " 평일 자동 실행";
  }
  const submitBtn = el.scheduleForm.querySelector('button[type="submit"]');
  if (submitBtn) submitBtn.textContent = "스케줄 저장";
}

function setupGeneralSettingsUi() {
  if (!el.generalSettingsForm) return;
  if (el.setFrequency) {
    const frequencyLabel = el.setFrequency.previousElementSibling;
    if (frequencyLabel && frequencyLabel.tagName === "LABEL") {
      frequencyLabel.remove();
    }
    el.setFrequency.remove();
  } else {
    const labels = Array.from(el.generalSettingsForm.querySelectorAll("label"));
    if (labels.length > 1) {
      labels[0].remove();
    }
  }
  const submitBtn = el.generalSettingsForm.querySelector('button[type="submit"]');
  if (submitBtn) submitBtn.textContent = "설정 저장";
  if (!document.getElementById("settings-reset-btn")) {
    const wrap = document.createElement("div");
    wrap.className = "reset-box";
    wrap.innerHTML = `
      <div class="muted">시스템 기본 설정으로 초기화할 수 있습니다.</div>
      <button id="settings-reset-btn" type="button" class="danger">기본 설정으로 초기화</button>
    `;
    el.generalSettingsForm.insertAdjacentElement("afterend", wrap);
    el.settingsResetBtn = document.getElementById("settings-reset-btn");
    bindSettingsResetButton();
  }
}

function bindSettingsResetButton() {
  if (!el.settingsResetBtn || el.settingsResetBtn.dataset.bound === "1") return;
  el.settingsResetBtn.dataset.bound = "1";
  el.settingsResetBtn.addEventListener("click", async () => {
    if (!confirm("시스템 기본 설정으로 초기화할까요? 현재 설정이 기본값으로 돌아갑니다.")) return;
    try {
      await api("/settings/reset-defaults", { method: "POST" });
      await loadSettings();
      showToast("기본 설정으로 초기화되었습니다.", "success");
    } catch (err) {
      alert(`초기화 실패: ${err.message}`);
    }
  });
}

function ensureToastWrap() {
  if (toastWrap) return;
  toastWrap = document.createElement("div");
  toastWrap.className = "toast-wrap";
  document.body.appendChild(toastWrap);
}

function showToast(message, type = "error") {
  ensureToastWrap();
  const node = document.createElement("div");
  node.className = `toast ${type}`;
  node.textContent = String(message || "");
  toastWrap.appendChild(node);
  setTimeout(() => {
    node.style.opacity = "0";
    node.style.transform = "translateY(8px)";
    setTimeout(() => node.remove(), 220);
  }, 2600);
}

window.alert = (msg) => showToast(msg, "error");

function setLoading(container) {
  if (!container) return;
  container.innerHTML = `
    <div class="skeleton"></div>
    <div class="skeleton"></div>
    <div class="skeleton"></div>
  `;
}

function animatePanels() {
  const panels = document.querySelectorAll(".panel");
  let i = 0;
  panels.forEach((p) => {
    p.classList.remove("fade-in-up");
    p.style.animationDelay = `${i * 28}ms`;
    p.classList.add("fade-in-up");
    i += 1;
  });
}

function switchView(viewName) {
  for (const btn of el.tabButtons) {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  }
  for (const section of el.contentSections) {
    const isActive = section.dataset.section === viewName;
    section.classList.toggle("active", isActive);
  }
}

async function api(path, options = {}) {
  const headers = options.headers || {};
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  if (!headers["Content-Type"] && options.body) headers["Content-Type"] = "application/json";

  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    logout();
    throw new Error("세션이 만료되었습니다. 다시 로그인해 주세요.");
  }
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

function showLogin() {
  el.dashboardView.classList.add("hidden");
  el.loginView.classList.remove("hidden");
}

function showDashboard() {
  el.loginView.classList.add("hidden");
  el.dashboardView.classList.remove("hidden");
  animatePanels();
}

function logout() {
  state.token = "";
  state.me = null;
  state.teamRouting = [];
  state.teamRoutingLoaded = false;
  state.selectedTeamRoutingId = "";
  localStorage.removeItem("admin_token");
  if (serverTimeTimer) {
    clearInterval(serverTimeTimer);
    serverTimeTimer = null;
  }
  serverTimeBaseMs = null;
  serverTimeLoadedAtMs = null;
  serverTimeZone = "";
  showLogin();
}

function setTeamRoutingLoadingState() {
  if (el.teamRoutingSelect) {
    el.teamRoutingSelect.innerHTML = `<option value="">팀 불러오는 중...</option>`;
    el.teamRoutingSelect.disabled = true;
  }
  if (el.teamRoutingSummary) {
    el.teamRoutingSummary.textContent = "팀 정보를 불러오는 중입니다.";
  }
}

function syncSelectedTeamRoutingId(items) {
  const teams = items || [];
  if (!teams.length) {
    state.selectedTeamRoutingId = "";
    return null;
  }

  const selected = teams.find((item) => String(item.id) === String(state.selectedTeamRoutingId));
  if (selected) {
    state.selectedTeamRoutingId = String(selected.id);
    return selected;
  }

  state.selectedTeamRoutingId = String(teams[0].id);
  return teams[0];
}

function renderTeamRoutingPicker(items, selectedTeam) {
  if (el.teamRoutingSelect) {
    el.teamRoutingSelect.innerHTML = "";
    if (!items.length) {
      el.teamRoutingSelect.innerHTML = `<option value="">선택할 팀이 없습니다</option>`;
      el.teamRoutingSelect.disabled = true;
    } else {
      for (const item of items) {
        const opt = document.createElement("option");
        opt.value = String(item.id);
        opt.textContent = `${item.name} (${Number(item.recipient_count || 0)}명)`;
        el.teamRoutingSelect.appendChild(opt);
      }
      el.teamRoutingSelect.disabled = false;
      el.teamRoutingSelect.value = String(selectedTeam ? selectedTeam.id : items[0].id);
    }
  }

  if (!el.teamRoutingSummary) return;
  if (!items.length) {
    el.teamRoutingSummary.textContent = "아직 표시할 팀이 없습니다.";
    return;
  }

  const team = selectedTeam || items[0];
  el.teamRoutingSummary.textContent =
    `총 ${items.length}개 팀 중 ${team.name} 표시 중 · 수신자 ${Number(team.recipient_count || 0)}명 · 키워드 ${Number(team.keyword_count || (team.keywords || []).length || 0)}개`;
}

function buildTeamRoutingCard(item) {
  const categoryNames = item.category_names || [];
  const categoryValue = categoryNames.join(", ");
  const keywords = item.keywords || [];
  const options = [
    `<option value="">기존 그룹 선택</option>`,
    ...(state.keywordGroups || []).map(
      (group) => `<option value="${escapeHtml(group)}">${escapeHtml(group)}</option>`
    ),
  ].join("");
  const teamCategoryOptions = categoryNames.length
    ? categoryNames.map((group) => `<option value="${escapeHtml(group)}">${escapeHtml(group)}</option>`).join("")
    : `<option value="">먼저 그룹을 지정하세요</option>`;

  return `
    <div class="item team-routing-card">
      <div class="item-head">
        <strong>${escapeHtml(item.name)}</strong>
        <div class="chips">
          <span class="chip ${item.is_active ? "" : "warn"}">${item.is_active ? "활성 팀" : "비활성 팀"}</span>
          <span class="chip">${Number(item.recipient_count || 0)}명</span>
        </div>
      </div>
      ${
        categoryNames.length
          ? `<div class="chips">${categoryNames.map((name) => `<span class="chip">${escapeHtml(name)}</span>`).join("")}</div>`
          : `<div class="muted">현재 연결된 수신 그룹이 없습니다.</div>`
      }
      <details class="team-keyword-block">
        <summary>팀 키워드 ${Number(item.keyword_count || keywords.length || 0)}개 보기</summary>
        <textarea class="team-keyword-preview" readonly>${escapeHtml(keywords.join(", "))}</textarea>
      </details>
      <div class="muted">팀 키워드는 연결된 그룹의 활성 키워드로 계산됩니다. 같은 그룹을 쓰는 다른 팀에도 함께 반영될 수 있습니다.</div>
      <div class="team-routing-editor">
        <input
          type="text"
          data-team-routing-input="${item.id}"
          value="${escapeHtml(categoryValue)}"
          placeholder="수신 그룹을 쉼표로 구분해 입력"
        >
        <div class="team-routing-row">
          <select data-team-routing-pick="${item.id}">
            ${options}
          </select>
          <button type="button" class="secondary" data-team-routing-add="${item.id}">그룹 추가</button>
          <button type="button" data-team-routing-save="${item.id}">저장</button>
        </div>
        <div class="team-routing-row">
          <input
            type="text"
            data-team-keyword-input="${item.id}"
            placeholder="이 팀 그룹에 추가할 키워드"
          >
          <select data-team-keyword-category="${item.id}">
            ${teamCategoryOptions}
          </select>
          <button type="button" class="secondary" data-team-keyword-add="${item.id}">키워드 추가</button>
        </div>
      </div>
    </div>
  `;
}

function renderKeywords(items) {
  el.keywordList.innerHTML = "";
  for (const item of items) {
    const card = document.createElement("div");
    card.className = "item";
    card.innerHTML = `
      <div class="item-head">
        <strong>${item.keyword}</strong>
        <span class="chip ${item.is_active ? "" : "warn"}">${item.is_active ? "활성" : "비활성"}</span>
      </div>
      <div class="chips">${(item.categories || []).map((c) => `<span class="chip">${c}</span>`).join("")}</div>
      <div class="item-actions">
        <button class="danger" data-del="${item.id}">삭제</button>
      </div>
    `;
    el.keywordList.appendChild(card);
  }
}

function renderRecipients(items) {
  el.recipientList.innerHTML = "";
  for (const item of items) {
    const card = document.createElement("div");
    card.className = "item";
    card.innerHTML = `
      <div class="item-head">
        <strong>${item.email}</strong>
        <span class="chip ${item.is_active ? "" : "warn"}">${item.is_active ? "활성" : "비활성"}</span>
      </div>
      <div>${item.full_name || "-"}</div>
      <div class="chips">${(item.team_names || []).map((t) => `<span class="chip">${t}</span>`).join("")}</div>
      <div class="item-actions">
        <button class="danger" data-del="${item.id}">삭제</button>
      </div>
    `;
    el.recipientList.appendChild(card);
  }
}

function renderTeamRouting(items) {
  state.teamRouting = items || [];
  state.teamRoutingLoaded = true;
  if (!el.teamRoutingList) return;
  el.teamRoutingList.innerHTML = "";
  const selectedTeam = syncSelectedTeamRoutingId(state.teamRouting);
  renderTeamRoutingPicker(state.teamRouting, selectedTeam);

  if (!selectedTeam) {
    el.teamRoutingList.innerHTML = `<div class="item">팀이 아직 없습니다. 수신자를 추가하면서 팀을 만들면 여기에서 그룹을 연결할 수 있습니다.</div>`;
    return;
  }

  el.teamRoutingList.innerHTML = buildTeamRoutingCard(selectedTeam);
}

function renderRuns(items) {
  el.runList.innerHTML = "";
  for (const item of items) {
    const isSourceHealth = item.job_type === "source_health";
    const title = isSourceHealth ? "Source health diagnostics" : item.job_type;
    const statusClass = item.status === "failed" ? "warn" : "";
    const typeClass = isSourceHealth ? "info" : "";
    const card = document.createElement("div");
    card.className = `item ${isSourceHealth ? "item-source-health" : ""}`.trim();
    card.innerHTML = `
      <div class="item-head">
        <strong>${title}</strong>
        <div class="chips">
          ${isSourceHealth ? `<span class="chip ${typeClass}">health</span>` : ""}
          <span class="chip ${statusClass}">${item.status}</span>
        </div>
      </div>
      <div>트리거: ${item.trigger_type}</div>
      <div>생성: ${new Date(item.created_at).toLocaleString()}</div>
      ${item.error_message ? `<div class="error">${item.error_message}</div>` : ""}
      <div class="item-actions">
        <button class="secondary" data-run="${item.id}">상세 보기</button>
        <button data-usejob="${item.id}">Job ID 사용</button>
      </div>
    `;
    el.runList.appendChild(card);
  }
}

function renderRunSources(items) {
  el.runSourceList.innerHTML = "";
  for (const item of items) {
    const card = document.createElement("div");
    card.className = "item";
    card.innerHTML = `
      <div class="item-head">
        <strong>${item.source_name}</strong>
        <span class="chip ${item.status === "failed" ? "warn" : ""}">${item.status}</span>
      </div>
      <div>기사: ${item.article_count} | 에러: ${item.error_count}</div>
      ${item.error_message ? `<div class="error">${item.error_message}</div>` : ""}
    `;
    el.runSourceList.appendChild(card);
  }
}

function renderSourceHealth(payload) {
  const counts = payload.counts || {};
  const staleThreshold = payload.stale_threshold_days || 7;
  el.sourceHealthSummary.textContent =
    `생성: ${payload.generated_at ? new Date(payload.generated_at).toLocaleString() : "-"} | ` +
    `healthy ${counts.healthy || 0} | stale ${counts.stale || 0} | blocked ${counts.blocked || 0} | ` +
    `unknown ${counts.unknown || 0} | error ${counts.error || 0} | stale alert ${staleThreshold}+d`;

  el.sourceHealthList.innerHTML = "";
  for (const item of payload.results || []) {
    const countText = item.recent_count > 0
      ? `최근 ${item.recent_count}건`
      : `최근 0건 / fallback ${item.wide_count || 0}건`;
    const latestText = item.recent_latest || item.wide_latest || "-";
    const status = item.status || "unknown";
    const warnClass = status === "healthy" ? "" : "warn";
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-head">
        <strong>${item.source_key}</strong>
        <span class="chip ${warnClass}">${status}</span>
      </div>
      <div>${item.description || "-"}</div>
      <div class="muted">${countText} | latest: ${latestText}</div>
      <div class="muted">${item.status_reason || item.error || "-"}</div>
    `;
    el.sourceHealthList.appendChild(row);
  }
}

function formatCampaignSubject(subject, teamNames = []) {
  const value = String(subject || "").trim();
  const looksBroken = !value || /\?{2,}|�|諛|댁|뚮|곕|쒖|몄|꾨|룷/.test(value);
  if (!looksBroken) return value;
  if (teamNames && teamNames.length) {
    return `${teamNames.join(", ")} Email Update`;
  }
  return "Email Update";
}

function renderAdminReport(payload) {
  const runs = payload.runs || {};
  const logs = payload.logs || {};
  const emails = payload.emails || {};
  const health = payload.source_health || {};
  const healthCounts = health.counts || {};
  el.adminReportSummary.textContent =
    `최근 ${payload.days}일 | runs ${runs.total || 0} (success ${runs.success || 0}, failed ${runs.failed || 0}) | ` +
    `logs ERROR ${logs.errors || 0}, WARNING ${logs.warnings || 0} | ` +
    `emails ${emails.campaigns_total || 0} campaigns / ${emails.deliveries_total || 0} deliveries | ` +
    `health blocked ${healthCounts.blocked || 0}, stale ${healthCounts.stale || 0}`;

  el.adminReportTeams.innerHTML = "";
  const teams = emails.team_summary || [];
  if (!teams.length) {
    el.adminReportTeams.innerHTML = `<div class="item">팀별 이메일 통계가 아직 없습니다.</div>`;
  } else {
    for (const item of teams) {
      const row = document.createElement("div");
      row.className = `item ${item.deliveries_failed > 0 ? "item-alert" : "item-ok"}`;
      row.innerHTML = `
        <div class="item-head">
          <strong>${item.team_name}</strong>
          <span class="chip ${item.deliveries_failed > 0 ? "warn" : "info"}">
            ${item.deliveries_failed > 0 ? "needs review" : "healthy"}
          </span>
        </div>
        <div>발송 ${item.deliveries_sent || 0} | 실패 ${item.deliveries_failed || 0} | 전체 ${item.deliveries_total || 0}</div>
        <div class="muted">최근 발송: ${item.latest_sent_at ? new Date(item.latest_sent_at).toLocaleString() : "-"}</div>
      `;
      el.adminReportTeams.appendChild(row);
    }
  }

  el.adminReportCampaigns.innerHTML = "";
  const campaigns = emails.recent_campaigns || [];
  if (!campaigns.length) {
    el.adminReportCampaigns.innerHTML = `<div class="item">최근 이메일 발송 이력이 없습니다.</div>`;
    return;
  }

  for (const item of campaigns) {
      const row = document.createElement("div");
      row.className = "item";
      row.innerHTML = `
      <div class="item-head">
        <strong>${formatCampaignSubject(item.subject, item.team_names || [])}</strong>
        <span class="chip ${item.status === "failed" ? "warn" : ""}">${item.status}</span>
      </div>
      <div class="chips">${(item.team_names || []).map((t) => `<span class="chip">${t}</span>`).join("")}</div>
      <div>기사 수: ${item.article_count || 0}</div>
      <div class="muted">생성: ${item.created_at ? new Date(item.created_at).toLocaleString() : "-"}</div>
      <div class="muted">발송: ${item.sent_at ? new Date(item.sent_at).toLocaleString() : "-"}</div>
    `;
    el.adminReportCampaigns.appendChild(row);
  }
}

async function downloadCsv(path, fallbackName) {
  const response = await fetch(path, {
    headers: state.token ? { Authorization: `Bearer ${state.token}` } : {},
  });
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch (_) {}
    throw new Error(detail);
  }

  const blob = await response.blob();
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  const disposition = response.headers.get("Content-Disposition") || "";
  const match = disposition.match(/filename=\"?([^"]+)\"?/i);
  link.href = href;
  link.download = match ? match[1] : fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

function renderResultSummary(result) {
  const started = result.started_at ? new Date(result.started_at).toLocaleString() : "-";
  const finished = result.finished_at ? new Date(result.finished_at).toLocaleString() : "-";
  el.resultSummary.innerHTML = `
    <strong>${result.job_type || "-"}</strong>
    <div class="muted">상태: ${result.status || "-"} | 시작: ${started} | 종료: ${finished}</div>
    <div class="muted">결과 파일: ${result.result_file || "-"}</div>
    <div class="muted">결과 건수: ${result.article_count || 0}</div>
  `;
}

function renderResultArticles(items) {
  el.resultArticles.innerHTML = "";
  if (!items || items.length === 0) {
    el.resultArticles.innerHTML = `<div class="item">표시할 결과 데이터가 없습니다.</div>`;
    return;
  }
  for (const item of items.slice(0, 100)) {
    const title = item.title || item.name || "(제목 없음)";
    const source = item.source || item.site || item.publisher || "-";
    const url = item.url || item.link || "";
    const summary = item.summary || item.note || item.description || item.ai_summary || "";
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-head">
        <strong>${title}</strong>
        <span class="chip">${source}</span>
      </div>
      ${summary ? `<div>${summary}</div>` : ""}
      ${url ? `<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>` : ""}
    `;
    el.resultArticles.appendChild(row);
  }
}

function renderResultLogs(items) {
  el.resultLogs.innerHTML = "";
  if (!items || items.length === 0) {
    el.resultLogs.innerHTML = `<div class="item">표시할 로그가 없습니다.</div>`;
    return;
  }
  for (const log of items || []) {
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-head">
        <strong>${log.level}</strong>
        <span class="chip">${new Date(log.created_at).toLocaleString()}</span>
      </div>
      <div>${log.message}</div>
    `;
    el.resultLogs.appendChild(row);
  }
}

function renderLogs(items) {
  el.logList.innerHTML = "";
  for (const item of items) {
    const card = document.createElement("div");
    card.className = "item";
    card.innerHTML = `
      <div class="item-head">
        <strong>${item.level}</strong>
        <span class="chip">${new Date(item.created_at).toLocaleString()}</span>
      </div>
      <div>${item.message}</div>
      <div class="muted">소스: ${item.source_name || "-"} | Job: ${item.job_id || "-"}</div>
    `;
    el.logList.appendChild(card);
  }
}

function renderSourceSettings(sources) {
  el.sourceSettingsList.innerHTML = "";
  for (const source of sources) {
    const card = document.createElement("div");
    card.className = "item";
    card.innerHTML = `
      <div class="item-head">
        <strong>${source.code}</strong>
        <span class="chip">${source.display_name}</span>
      </div>
      <div class="row">
        <label class="checkline"><input type="checkbox" data-source-enable="${source.id}" ${source.is_enabled ? "checked" : ""}> 활성</label>
        <input type="number" min="1" value="${source.timeout_seconds}" data-source-timeout="${source.id}" placeholder="타임아웃(초)">
        <input type="number" min="1" value="${source.max_items}" data-source-max="${source.id}" placeholder="최대 수집 수">
        <button class="secondary" data-source-save="${source.id}">저장</button>
      </div>
    `;
    el.sourceSettingsList.appendChild(card);
  }
}

function renderRunSourceSelect(sources) {
  el.runSourceSelect.innerHTML = "";
  const first = document.createElement("option");
  first.value = "";
  first.textContent = "소스 선택 (개별 실행용)";
  el.runSourceSelect.appendChild(first);
  for (const source of sources || []) {
    const opt = document.createElement("option");
    opt.value = source.code;
    opt.textContent = `${source.display_name} (${source.code})`;
    el.runSourceSelect.appendChild(opt);
  }
}

function renderEmailHistory(items) {
  el.emailHistoryList.innerHTML = "";
  for (const item of items) {
    const card = document.createElement("div");
    card.className = "item";
    card.innerHTML = `
      <div class="item-head">
        <strong>${formatCampaignSubject(item.subject, item.team_names || [])}</strong>
        <span class="chip ${item.status === "failed" ? "warn" : ""}">${item.status}</span>
      </div>
      <div>기사 수: ${item.article_count}</div>
      <div class="chips">${(item.team_names || []).map((t) => `<span class="chip">${t}</span>`).join("")}</div>
      <div>생성: ${new Date(item.created_at).toLocaleString()}</div>
      <div class="item-actions">
        <button class="secondary" data-email-campaign="${item.id}">상세 보기</button>
      </div>
    `;
    el.emailHistoryList.appendChild(card);
  }
}

function renderEmailDetail(detail) {
  el.emailDetailMeta.textContent =
    `${formatCampaignSubject(detail.subject, detail.team_names || [])} | 상태: ${detail.status} | 팀: ${(detail.team_names || []).join(", ") || "-"} | ` +
    `생성: ${new Date(detail.created_at).toLocaleString()}`;
  el.emailDetailDeliveries.innerHTML = "";
  for (const d of detail.deliveries || []) {
    const row = document.createElement("div");
    row.className = "item";
    row.innerHTML = `
      <div class="item-head">
        <strong>${d.full_name || d.email}</strong>
        <span class="chip ${d.status === "failed" ? "warn" : ""}">${d.status}</span>
      </div>
      <div>${d.email}</div>
      <div class="chips">${(d.team_names || []).map((t) => `<span class="chip">${t}</span>`).join("")}</div>
      <div>유형: ${d.delivery_type}</div>
      ${d.error_message ? `<div class="error">${d.error_message}</div>` : ""}
    `;
    el.emailDetailDeliveries.appendChild(row);
  }
  el.emailDetailBody.innerHTML = detail.body_html || "<p>(HTML 본문 없음)</p>";
}

function fillSelect(selectEl, values, firstLabel) {
  selectEl.innerHTML = "";
  const first = document.createElement("option");
  first.value = "";
  first.textContent = firstLabel;
  selectEl.appendChild(first);
  for (const v of values) {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    selectEl.appendChild(opt);
  }
}

function fillTeamSelect(teams) {
  el.rcTeamFilter.innerHTML = "";
  const first = document.createElement("option");
  first.value = "";
  first.textContent = "전체 팀";
  el.rcTeamFilter.appendChild(first);

  fillSelect(
    el.rcTeamPick,
    teams.map((t) => t.name),
    "기존 팀 선택"
  );

  for (const t of teams) {
    const opt = document.createElement("option");
    opt.value = t.name;
    opt.textContent = t.name;
    el.rcTeamFilter.appendChild(opt);
  }
}

async function loadKeywordGroups() {
  const groups = await api("/keywords/groups");
  state.keywordGroups = groups || [];
  fillSelect(el.kwGroupFilter, groups, "전체 그룹");
  fillSelect(el.kwCategoryPick, groups, "기존 카테고리 선택");
  if (state.teamRoutingLoaded) {
    renderTeamRouting(state.teamRouting);
  }
}

async function loadKeywordLanguages() {
  const languages = await api("/keywords/languages");
  fillSelect(el.kwLanguageFilter, languages, "전체 언어");
}

async function loadTeams() {
  const teams = await api("/recipients/teams");
  fillTeamSelect(teams);
}

async function loadTeamRouting() {
  if (!el.teamRoutingList) return;
  state.teamRoutingLoaded = false;
  setTeamRoutingLoadingState();
  setLoading(el.teamRoutingList);
  const teams = await api("/recipients/team-routing");
  renderTeamRouting(teams);
}

async function loadMe() {
  state.me = await api("/auth/me");
  el.userMeta.textContent = `${state.me.username || state.me.email} (${state.me.roles.join(", ")})`;
}

async function loadServerTime() {
  const data = await api("/system/time");
  serverTimeBaseMs = new Date(data.server_time).getTime();
  serverTimeLoadedAtMs = Date.now();
  serverTimeZone = data.timezone || "";
  renderServerTime();
}

function renderServerTime() {
  if (!serverTimeBaseMs || !serverTimeLoadedAtMs) {
    el.serverTime.textContent = "";
    return;
  }
  const currentMs = serverTimeBaseMs + (Date.now() - serverTimeLoadedAtMs);
  const dt = new Date(currentMs);
  el.serverTime.textContent = `서버 시간: ${dt.toLocaleString()} (${serverTimeZone})`;
}

function startServerTimeTicker() {
  if (serverTimeTimer) clearInterval(serverTimeTimer);
  serverTimeTimer = setInterval(() => {
    renderServerTime();
  }, 1000);
}

async function loadKeywords() {
  setLoading(el.keywordList);
  const params = new URLSearchParams();
  const q = el.kwSearch.value.trim();
  const group = el.kwGroupFilter.value;
  const languageCode = el.kwLanguageFilter.value;
  if (q) params.set("q", q);
  if (group) params.set("group", group);
  if (languageCode) params.set("language_code", languageCode);
  const data = await api(`/keywords${params.toString() ? `?${params.toString()}` : ""}`);
  renderKeywords(data);
}

async function loadRecipients() {
  setLoading(el.recipientList);
  const params = new URLSearchParams();
  const q = el.rcSearch.value.trim();
  const teamName = el.rcTeamFilter.value;
  if (q) params.set("q", q);
  if (teamName) params.set("team_name", teamName);
  const data = await api(`/recipients${params.toString() ? `?${params.toString()}` : ""}`);
  renderRecipients(data);
}

async function loadRuns() {
  setLoading(el.runList);
  const params = new URLSearchParams();
  if (el.runStatusFilter.value) params.set("status", el.runStatusFilter.value);
  const data = await api(`/runs${params.toString() ? `?${params.toString()}` : ""}`);
  renderRuns(data);
}

async function loadResultJobs() {
  const successRuns = await api("/runs?status=success&limit=200");
  el.resultJobSelect.innerHTML = "";
  const first = document.createElement("option");
  first.value = "";
  first.textContent = "성공한 실행 선택";
  el.resultJobSelect.appendChild(first);
  for (const run of successRuns) {
    const opt = document.createElement("option");
    opt.value = run.id;
    opt.textContent = `${run.job_type} | ${new Date(run.created_at).toLocaleString()} | ${run.id}`;
    el.resultJobSelect.appendChild(opt);
  }
}

async function loadRunResult(jobId) {
  setLoading(el.resultArticles);
  setLoading(el.resultLogs);
  const result = await api(`/runs/${jobId}/result`);
  renderResultSummary(result);
  renderResultArticles(result.articles || []);
  renderResultLogs(result.logs || []);
}

function syncRunSelectorState() {
  const single = el.runModeSelect.value === "single_source";
  el.runSourceSelect.disabled = !single;
}

async function loadRunSources(jobId) {
  setLoading(el.runSourceList);
  const data = await api(`/runs/${jobId}/sources`);
  renderRunSources(data);
}

async function loadLogs() {
  setLoading(el.logList);
  const params = new URLSearchParams();
  if (el.logLevelFilter.value) params.set("level", el.logLevelFilter.value);
  if (el.logSearch.value.trim()) params.set("q", el.logSearch.value.trim());
  const data = await api(`/logs${params.toString() ? `?${params.toString()}` : ""}`);
  renderLogs(data);
}

async function loadSourceHealth() {
  setLoading(el.sourceHealthList);
  try {
    const data = await api("/source-health");
    renderSourceHealth(data);
  } catch (err) {
    el.sourceHealthSummary.textContent = "진단 파일이 아직 없습니다.";
    el.sourceHealthList.innerHTML = `<div class="item">${err.message}</div>`;
  }
}

async function loadAdminReport() {
  setLoading(el.adminReportCampaigns);
  const data = await api("/admin-report?days=7");
  renderAdminReport(data);
}

async function loadSettings() {
  const data = await api("/settings/overview");
  state.generalSettings.scrapeFrequencyMinutes = data.general.scrape_frequency_minutes;
  if (el.setFrequency) {
    el.setFrequency.value = data.general.scrape_frequency_minutes;
  }
  el.setMaxArticles.value = data.general.max_total_articles;
  el.setCron.value = cronToTime(data.schedule.cron_expr);
  if (el.setTimezone) {
    el.setTimezone.value = data.schedule.timezone;
  }
  el.setScheduleEnabled.checked = data.schedule.is_enabled;
  renderSourceSettings(data.sources);
  renderRunSourceSelect(data.sources);
}

async function loadEmailHistory() {
  setLoading(el.emailHistoryList);
  const params = new URLSearchParams();
  const q = el.emailHistorySearch.value.trim();
  const team = el.emailHistoryTeam.value.trim();
  const status = el.emailHistoryStatus.value;
  if (q) params.set("q", q);
  if (team) params.set("team", team);
  if (status) params.set("status", status);
  const items = await api(`/emails/history${params.toString() ? `?${params.toString()}` : ""}`);
  renderEmailHistory(items);
}

async function loadEmailDetail(campaignId) {
  const detail = await api(`/emails/history/${campaignId}`);
  renderEmailDetail(detail);
}

async function refreshAll() {
  await Promise.all([
    loadKeywordGroups(),
    loadKeywordLanguages(),
    loadTeams(),
    loadTeamRouting(),
    loadMe(),
    loadServerTime(),
    loadAdminReport(),
    loadKeywords(),
    loadRecipients(),
    loadRuns(),
    loadSourceHealth(),
    loadResultJobs(),
    loadLogs(),
    loadSettings(),
    loadEmailHistory(),
  ]);
}

el.loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  el.loginError.textContent = "";
  try {
    const res = await api("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        username: el.loginUsername.value.trim(),
        password: el.loginPassword.value,
      }),
    });
    state.token = res.access_token;
    localStorage.setItem("admin_token", state.token);
    showDashboard();
    await refreshAll();
    syncRunSelectorState();
    startServerTimeTicker();
    showToast("로그인되었습니다.", "success");
  } catch (err) {
    el.loginError.textContent = err.message;
    showToast(err.message || "로그인 실패", "error");
  }
});

el.logoutBtn.addEventListener("click", () => logout());
el.refreshBtn.addEventListener("click", () => refreshAll().catch((err) => alert(err.message)));

el.keywordForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const categoryNames = mergeCsvValues(el.kwCategories.value, el.kwCategoryPick.value);
  try {
    await api("/keywords", {
      method: "POST",
      body: JSON.stringify({
        keyword: el.kwName.value.trim(),
        category_names: categoryNames,
        language_code: el.kwLanguage.value.trim() || "ko",
        is_active: el.kwActive.checked,
      }),
    });
    el.keywordForm.reset();
    el.kwLanguage.value = "ko";
    el.kwActive.checked = true;
    await loadKeywordGroups();
    await loadKeywordLanguages();
    await loadKeywords();
    await loadTeamRouting();
    showToast("키워드가 추가되었습니다.", "success");
  } catch (err) {
    alert(`키워드 생성 실패: ${err.message}`);
  }
});

el.kwCategoryAddBtn.addEventListener("click", () => {
  const selected = (el.kwCategoryPick.value || "").trim();
  if (!selected) return;
  const existing = splitCsv(el.kwCategories.value);
  if (!existing.includes(selected)) {
    existing.push(selected);
  }
  el.kwCategories.value = existing.join(", ");
  el.kwCategoryPick.value = "";
});

el.recipientForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const teamNames = mergeCsvValues(el.rcTeams.value, el.rcTeamPick.value);
  try {
    await api("/recipients", {
      method: "POST",
      body: JSON.stringify({
        email: el.rcEmail.value.trim(),
        full_name: el.rcName.value.trim() || null,
        team_names: teamNames,
        is_active: el.rcActive.checked,
        receives_test_emails: el.rcTest.checked,
      }),
    });
    el.recipientForm.reset();
    el.rcActive.checked = true;
    await loadTeams();
    await loadRecipients();
    await loadTeamRouting();
    showToast("수신자가 추가되었습니다.", "success");
  } catch (err) {
    alert(`수신자 생성 실패: ${err.message}`);
  }
});

el.rcTeamAddBtn.addEventListener("click", () => {
  const selected = (el.rcTeamPick.value || "").trim();
  if (!selected) return;
  const existing = splitCsv(el.rcTeams.value);
  if (!existing.includes(selected)) {
    existing.push(selected);
  }
  el.rcTeams.value = existing.join(", ");
  el.rcTeamPick.value = "";
});

el.keywordList.addEventListener("click", async (e) => {
  const target = e.target;
  if (!(target instanceof HTMLElement)) return;
  const button = target.closest("button[data-del]");
  if (!(button instanceof HTMLButtonElement)) return;
  const id = button.dataset.del;
  if (!id) return;
  if (button.dataset.busy === "1") return;
  if (!confirm("이 키워드를 삭제할까요?")) return;
  button.dataset.busy = "1";
  button.disabled = true;
  try {
    await api(`/keywords/${id}`, { method: "DELETE" });
    await loadKeywordGroups();
    await loadKeywordLanguages();
    await loadKeywords();
    await loadTeamRouting();
    showToast("키워드가 삭제되었습니다.", "success");
  } catch (err) {
    alert(`삭제 실패: ${err.message}`);
  } finally {
    button.dataset.busy = "0";
    button.disabled = false;
  }
});

el.recipientList.addEventListener("click", async (e) => {
  const target = e.target;
  if (!(target instanceof HTMLElement)) return;
  const button = target.closest("button[data-del]");
  if (!(button instanceof HTMLButtonElement)) return;
  const id = button.dataset.del;
  if (!id) return;
  if (button.dataset.busy === "1") return;
  if (!confirm("이 수신자를 삭제할까요?")) return;
  button.dataset.busy = "1";
  button.disabled = true;
  try {
    await api(`/recipients/${id}`, { method: "DELETE" });
    await loadTeams();
    await loadRecipients();
    await loadTeamRouting();
    showToast("수신자가 삭제되었습니다.", "success");
  } catch (err) {
    alert(`삭제 실패: ${err.message}`);
  } finally {
    button.dataset.busy = "0";
    button.disabled = false;
  }
});

if (el.teamRoutingSelect) {
  el.teamRoutingSelect.addEventListener("change", () => {
    state.selectedTeamRoutingId = String(el.teamRoutingSelect.value || "");
    renderTeamRouting(state.teamRouting);
  });
}

el.teamRoutingList.addEventListener("click", async (e) => {
  const target = e.target;
  if (!(target instanceof HTMLElement)) return;
  const trigger = target.closest("button") || target;

  const keywordAddId = trigger.dataset.teamKeywordAdd;
  if (keywordAddId) {
    const input = el.teamRoutingList.querySelector(`[data-team-keyword-input="${keywordAddId}"]`);
    const select = el.teamRoutingList.querySelector(`[data-team-keyword-category="${keywordAddId}"]`);
    const keyword = input ? String(input.value || "").trim() : "";
    const category = select ? String(select.value || "").trim() : "";
    if (!keyword) return alert("추가할 키워드를 입력하세요.");
    if (!category) return alert("키워드를 추가할 그룹을 먼저 선택하세요.");

    try {
      await api("/keywords", {
        method: "POST",
        body: JSON.stringify({
          keyword,
          category_names: [category],
          language_code: guessLanguageCode(keyword),
          is_active: true,
        }),
      });
      if (input) input.value = "";
      await loadKeywordGroups();
      await loadKeywordLanguages();
      await loadKeywords();
      await loadTeamRouting();
      showToast("팀 그룹에 키워드가 추가되었습니다.", "success");
    } catch (err) {
      alert(`팀 키워드 추가 실패: ${err.message}`);
    }
    return;
  }

  const addId = trigger.dataset.teamRoutingAdd;
  if (addId) {
    const pick = el.teamRoutingList.querySelector(`[data-team-routing-pick="${addId}"]`);
    const input = el.teamRoutingList.querySelector(`[data-team-routing-input="${addId}"]`);
    const selected = pick ? String(pick.value || "").trim() : "";
    if (!selected || !input) return;
    const values = splitCsv(input.value);
    if (!values.includes(selected)) {
      values.push(selected);
    }
    input.value = values.join(", ");
    if (pick) pick.value = "";
    return;
  }

  const saveId = trigger.dataset.teamRoutingSave;
  if (!saveId) return;

  const input = el.teamRoutingList.querySelector(`[data-team-routing-input="${saveId}"]`);
  if (!input) return;

  try {
    await api(`/recipients/teams/${saveId}/routing`, {
      method: "PUT",
      body: JSON.stringify({
        category_names: splitCsv(input.value),
      }),
    });
    await loadKeywordGroups();
    await loadTeamRouting();
    showToast("팀 수신 그룹이 저장되었습니다.", "success");
  } catch (err) {
    alert(`팀 수신 그룹 저장 실패: ${err.message}`);
  }
});

el.kwSearch.addEventListener("input", () => loadKeywords().catch((err) => alert(err.message)));
el.kwGroupFilter.addEventListener("change", () => loadKeywords().catch((err) => alert(err.message)));
el.kwLanguageFilter.addEventListener("change", () => loadKeywords().catch((err) => alert(err.message)));
el.rcSearch.addEventListener("input", () => loadRecipients().catch((err) => alert(err.message)));
el.rcTeamFilter.addEventListener("change", () => loadRecipients().catch((err) => alert(err.message)));
el.runRefreshBtn.addEventListener("click", () => Promise.all([loadRuns(), loadResultJobs(), loadSourceHealth()]).catch((err) => alert(err.message)));
el.runStatusFilter.addEventListener("change", () => loadRuns().catch((err) => alert(err.message)));
el.logRefreshBtn.addEventListener("click", () => loadLogs().catch((err) => alert(err.message)));
el.logLevelFilter.addEventListener("change", () => loadLogs().catch((err) => alert(err.message)));
el.logSearch.addEventListener("input", () => loadLogs().catch((err) => alert(err.message)));

el.runList.addEventListener("click", async (e) => {
  const target = e.target;
  if (!(target instanceof HTMLElement)) return;
  const useId = target.dataset.usejob;
  if (useId) {
    el.scraperJobId.value = useId;
    el.resultJobSelect.value = useId;
    return;
  }
  const runId = target.dataset.run;
  if (!runId) return;
  try {
    await loadRunSources(runId);
  } catch (err) {
    alert(err.message);
  }
});

el.resultLoadBtn.addEventListener("click", async () => {
  const jobId = el.resultJobSelect.value;
  if (!jobId) return alert("먼저 성공한 실행을 선택하세요.");
  try {
    await loadRunResult(jobId);
  } catch (err) {
    alert(`결과 조회 실패: ${err.message}`);
  }
});

el.runModeSelect.addEventListener("change", syncRunSelectorState);

el.runExecuteBtn.addEventListener("click", async () => {
  const mode = el.runModeSelect.value;
  try {
    let res = null;
    if (mode === "pipeline_full") {
      res = await api("/scraper/run-full-pipeline", { method: "POST" });
    } else if (mode === "news_only") {
      res = await api("/scraper/run-now", {
        method: "POST",
        body: JSON.stringify({ source_codes: [] }),
      });
    } else if (mode === "html_only") {
      res = await api("/scraper/run-html-monitors", { method: "POST" });
    } else if (mode === "source_health") {
      res = await api("/scraper/run-source-health", { method: "POST" });
    } else if (mode === "single_source") {
      const code = (el.runSourceSelect.value || "").trim();
      if (!code) return alert("개별 실행은 소스를 먼저 선택하세요.");
      res = await api(`/scraper/run-source/${encodeURIComponent(code)}`, { method: "POST" });
    } else {
      return alert("실행 모드를 선택하세요.");
    }

    el.scraperMsg.textContent = `${res.message} Job: ${res.job_id}`;
    el.scraperJobId.value = res.job_id || "";
    await loadRuns();
    await loadResultJobs();
    showToast("선택한 작업 실행을 시작했습니다.", "success");
  } catch (err) {
    alert(`실행 실패: ${err.message}`);
  }
});

el.scraperStopBtn.addEventListener("click", async () => {
  const jobId = el.scraperJobId.value.trim();
  if (!jobId) return alert("Job ID를 입력하세요.");
  try {
    const res = await api(`/scraper/stop/${jobId}`, { method: "POST" });
    el.scraperMsg.textContent = res.message;
    await loadRuns();
    showToast("실행이 중지되었습니다.", "success");
  } catch (err) {
    alert(`중지 실패: ${err.message}`);
  }
});

el.scraperRetryBtn.addEventListener("click", async () => {
  const jobId = el.scraperJobId.value.trim();
  if (!jobId) return alert("Job ID를 입력하세요.");
  try {
    const res = await api(`/scraper/retry-failed/${jobId}`, { method: "POST" });
    el.scraperMsg.textContent = `${res.message} Job: ${res.job_id}`;
    el.scraperJobId.value = res.job_id || "";
    await loadRuns();
    showToast("재시도를 시작했습니다.", "success");
  } catch (err) {
    alert(`재시도 실패: ${err.message}`);
  }
});

el.generalSettingsForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/settings/general", {
      method: "PUT",
      body: JSON.stringify({
        scrape_frequency_minutes: Number(state.generalSettings.scrapeFrequencyMinutes || 1440),
        max_total_articles: Number(el.setMaxArticles.value),
      }),
    });
    showToast("일반 설정이 저장되었습니다.", "success");
  } catch (err) {
    alert(`저장 실패: ${err.message}`);
  }
});

el.scheduleForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    await api("/settings/schedule/default", {
      method: "PUT",
      body: JSON.stringify({
        cron_expr: timeToCron(el.setCron.value),
        timezone: "Asia/Seoul",
        is_enabled: el.setScheduleEnabled.checked,
      }),
    });
    showToast("스케줄이 저장되었습니다.", "success");
  } catch (err) {
    alert(`저장 실패: ${err.message}`);
  }
});

el.sourceSettingsList.addEventListener("click", async (e) => {
  const target = e.target;
  if (!(target instanceof HTMLElement)) return;
  const sourceId = target.dataset.sourceSave;
  if (!sourceId) return;

  const enabledEl = el.sourceSettingsList.querySelector(`[data-source-enable="${sourceId}"]`);
  const timeoutEl = el.sourceSettingsList.querySelector(`[data-source-timeout="${sourceId}"]`);
  const maxEl = el.sourceSettingsList.querySelector(`[data-source-max="${sourceId}"]`);
  const enabled = enabledEl ? enabledEl.checked : true;
  const timeout = Number(timeoutEl ? timeoutEl.value : "120");
  const maxItems = Number(maxEl ? maxEl.value : "200");

  try {
    await api(`/settings/sources/${sourceId}`, {
      method: "PUT",
      body: JSON.stringify({
        is_enabled: enabled,
        timeout_seconds: timeout,
        max_items: maxItems,
      }),
    });
    await loadSettings();
    showToast("소스 설정이 저장되었습니다.", "success");
  } catch (err) {
    alert(`소스 설정 저장 실패: ${err.message}`);
  }
});

el.emailHistoryRefresh.addEventListener("click", () => loadEmailHistory().catch((err) => alert(err.message)));
el.emailHistorySearch.addEventListener("input", () => loadEmailHistory().catch((err) => alert(err.message)));
el.emailHistoryTeam.addEventListener("input", () => loadEmailHistory().catch((err) => alert(err.message)));
el.emailHistoryStatus.addEventListener("change", () => loadEmailHistory().catch((err) => alert(err.message)));
el.adminReportExportBtn.addEventListener("click", async () => {
  try {
    await downloadCsv("/admin-report/export.csv?days=7", "admin_report.csv");
    showToast("리포트 CSV를 내려받았습니다.", "success");
  } catch (err) {
    alert(`리포트 내보내기 실패: ${err.message}`);
  }
});
el.emailHistoryExportBtn.addEventListener("click", async () => {
  try {
    const params = new URLSearchParams();
    const q = el.emailHistorySearch.value.trim();
    const team = el.emailHistoryTeam.value.trim();
    const status = el.emailHistoryStatus.value;
    if (q) params.set("q", q);
    if (team) params.set("team", team);
    if (status) params.set("status", status);
    await downloadCsv(`/emails/history/export.csv${params.toString() ? `?${params.toString()}` : ""}`, "email_history.csv");
    showToast("이메일 이력 CSV를 내려받았습니다.", "success");
  } catch (err) {
    alert(`이메일 이력 내보내기 실패: ${err.message}`);
  }
});

el.emailHistoryList.addEventListener("click", async (e) => {
  const target = e.target;
  if (!(target instanceof HTMLElement)) return;
  const campaignId = target.dataset.emailCampaign;
  if (!campaignId) return;
  try {
    await loadEmailDetail(campaignId);
  } catch (err) {
    alert(`이메일 상세 조회 실패: ${err.message}`);
  }
});

for (const btn of el.tabButtons) {
  btn.addEventListener("click", () => switchView(btn.dataset.view || "manage"));
}

document.addEventListener("click", (e) => {
  const t = e.target;
  if (!(t instanceof HTMLElement)) return;
  const btn = t.closest("button");
  if (!(btn instanceof HTMLElement)) return;
  const rect = btn.getBoundingClientRect();
  const ripple = document.createElement("span");
  ripple.className = "ripple";
  const size = Math.max(rect.width, rect.height) * 1.3;
  ripple.style.width = `${size}px`;
  ripple.style.height = `${size}px`;
  ripple.style.left = `${e.clientX - rect.left - size / 2}px`;
  ripple.style.top = `${e.clientY - rect.top - size / 2}px`;
  btn.appendChild(ripple);
  setTimeout(() => ripple.remove(), 560);
});

async function init() {
  if (!state.token) {
    showLogin();
    return;
  }
  try {
    showDashboard();
    setupGeneralSettingsUi();
    setupScheduleUi();
    await refreshAll();
    syncRunSelectorState();
    startServerTimeTicker();
  } catch (_) {
    logout();
  }
}

setupGeneralSettingsUi();
setupScheduleUi();
init().catch((err) => console.error(err));
