(() => {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const setText = (id, value) => { const el = byId(id); if (el) el.textContent = String(value); };
  const make = (tag, className, text) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text !== undefined && text !== null) el.textContent = String(text);
    return el;
  };
  const safeGitHubUrl = (value) => {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && url.hostname === "github.com" ? url.href : null;
    } catch (_) { return null; }
  };
  const addLink = (parent, href, label) => {
    const safe = safeGitHubUrl(href);
    if (!safe) { parent.appendChild(document.createTextNode(label)); return; }
    const a = make("a", "", label);
    a.href = safe;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    parent.appendChild(a);
  };
  const formatDate = (value) => {
    if (!value) return "Okänd tid";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "Okänd tid" : new Intl.DateTimeFormat("sv-SE", {
      dateStyle: "medium", timeStyle: "short", timeZone: "Europe/Stockholm"
    }).format(date);
  };
  const renderItem = (container, title, meta, badge, badgeClass, href) => {
    const item = make("div", "item");
    const strong = make("strong");
    if (href) addLink(strong, href, title); else strong.textContent = title;
    item.appendChild(strong);
    item.appendChild(make("div", "meta", meta));
    if (badge) item.appendChild(make("span", "pill " + (badgeClass || ""), badge));
    container.appendChild(item);
  };
  const empty = (id, message) => {
    const el = byId(id);
    el.replaceChildren(make("div", "empty", message));
  };
  const showError = (message) => {
    const notice = byId("data-notice");
    notice.className = "notice bad";
    notice.textContent = message;
    ["work-list", "runs-list", "scheduled-runs-list", "recovered-runs-list", "failed-runs-list", "projects-list"].forEach((id) => empty(id, "Ingen verifierad live-data tillgänglig."));
  };
  const render = (data) => {
    if (!data || data.schema_version !== 1 || !Array.isArray(data.projects) ||
        !Number.isFinite(data.expected_repositories) || !Number.isFinite(data.successful_repositories)) {
      throw new Error("JSON-filen har ett okänt eller ofullständigt schema.");
    }
    const observed = new Date(data.observed_at_utc);
    if (Number.isNaN(observed.getTime())) throw new Error("Snapshot saknar giltig observationstid.");
    const ageHours = (Date.now() - observed.getTime()) / 3600000;
    const partial = data.status !== "success" ||
      data.successful_repositories !== data.expected_repositories ||
      data.failed_repositories !== 0;
    const stale = ageHours > 24;
    const notice = byId("data-notice");
    notice.className = "notice " + (partial || stale ? "bad" : "good");
    const statusText = partial
      ? "PARTIELL INSAMLING – visa inte sammanställningen som komplett. "
      : "Insamlingen lyckades för samtliga registrerade projekt. ";
    const registryText = data.registry_status === "seed"
      ? "Projektregistret är fortfarande en manuellt kuraterad seed. "
      : "";
    const freshnessText = stale
      ? "VARNING: snapshoten är äldre än 24 timmar. "
      : "Dataålder under 24 timmar. ";
    notice.textContent = statusText + registryText + freshnessText +
      "Observerad: " + formatDate(data.observed_at_utc) +
      ". Senaste 20 workflow-körningarna per repo visas; detta är inte fullständig körhistorik.";
    setText("metric-projects", data.successful_repositories + "/" + data.expected_repositories);
    const projects = data.projects;
    const work = projects.flatMap((p) => (p.open_work_items || []).map((item) => ({...item, project: p})));
    const runs = projects.flatMap((p) => (p.latest_workflow_runs || []).map((run) => ({...run, project: p})));
    const failedRuns = runs.filter((r) => r.status === "completed" && r.conclusion && r.conclusion !== "success");
    const workflowKey = (r) => String(r.workflow_id || r.workflow_path || r.name || "unknown") + "|" + r.project.repository;
    const hasLaterSuccess = (run) => runs.some((candidate) =>
      workflowKey(candidate) === workflowKey(run) &&
      candidate.status === "completed" && candidate.conclusion === "success" &&
      String(candidate.created_at || "") > String(run.created_at || ""));
    const scheduledRuns = runs.filter((r) => r.event === "schedule");
    const scheduledActive = scheduledRuns.filter((r) => r.status !== "completed");
    const scheduledFailures = scheduledRuns.filter((r) =>
      r.status === "completed" && r.conclusion && r.conclusion !== "success" && !hasLaterSuccess(r));
    const recoveredFailures = failedRuns.filter(hasLaterSuccess);
    const unresolvedFailures = failedRuns.filter((r) => !hasLaterSuccess(r));
    const successfulRuns = runs.filter((r) => r.status === "completed" && r.conclusion === "success");
    setText("metric-work", work.length);
    setText("metric-failed", unresolvedFailures.length);
    setText("metric-success", successfulRuns.length);

    const workEl = byId("work-list");
    workEl.replaceChildren();
    work.sort((a,b) => String(b.updated_at || "").localeCompare(String(a.updated_at || "")));
    if (!work.length) empty("work-list", "Inga öppna PR:er eller ärenden i snapshoten.");
    else work.slice(0, 25).forEach((item) => {
      const kind = item.kind === "pull_request" ? "PR" : "Ärende";
      renderItem(workEl, item.project.project_name + " · " + kind + " #" + item.number + " · " + (item.title || "Utan rubrik"),
        "Uppdaterad " + formatDate(item.updated_at) + (item.assignees?.length ? " · Tilldelad: " + item.assignees.join(", ") : ""),
        item.draft ? "Utkast" : "Öppen", "", item.html_url);
    });
    if (work.length > 25) workEl.appendChild(make("div", "meta", "Visar 25 av " + work.length + " öppna poster."));

    const runsEl = byId("runs-list");
    runsEl.replaceChildren();
    runs.sort((a,b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
    if (!runs.length) empty("runs-list", "Inga workflow-körningar i snapshoten.");
    else runs.slice(0, 30).forEach((run) => {
      const conclusion = run.status === "completed" ? (run.conclusion || "okänd slutsats") : run.status;
      const failed = run.status === "completed" && run.conclusion !== "success";
      renderItem(runsEl, run.project.project_name + " · " + (run.name || "Workflow"),
        "#" + run.run_number + " · " + (run.head_branch || "okänd branch") + " · " + formatDate(run.created_at),
        conclusion, failed ? "blocked" : (run.conclusion === "success" ? "done" : "next"), run.html_url);
    });

    const failedRunsEl = byId("failed-runs-list");
    failedRunsEl.replaceChildren();
    failedRuns.sort((a,b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
    if (!failedRuns.length) {
      empty("failed-runs-list", "Inga avvikande avslut bland de senaste 20 körningarna per repo.");
    } else {
      unresolvedFailures.forEach((run) => {
        renderItem(failedRunsEl, run.project.project_name + " · " + (run.name || "Workflow"),
          "#" + run.run_number + " · " + (run.head_branch || "okänd branch") + " · " + formatDate(run.created_at),
          run.conclusion || "okänd slutsats", "blocked", run.html_url);
      });
    }

    const scheduledEl = byId("scheduled-runs-list");
    scheduledEl.replaceChildren();
    scheduledActive.sort((a,b) => String(b.run_started_at || b.created_at || "").localeCompare(String(a.run_started_at || a.created_at || "")));
    scheduledFailures.sort((a,b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
    if (!scheduledActive.length && !scheduledFailures.length) {
      empty("scheduled-runs-list", "Inga pågående eller olösta schemalagda körningar i snapshoten.");
    } else {
      scheduledActive.forEach((run) => renderItem(scheduledEl,
        run.project.project_name + " · " + (run.name || "Schemalagt workflow"),
        "Pågår sedan " + formatDate(run.run_started_at || run.created_at) +
        " · " + (run.display_title || run.workflow_path || "Geografisk testnivå ej registrerad"),
        run.status, "next", run.html_url));
      scheduledFailures.forEach((run) => renderItem(scheduledEl,
        run.project.project_name + " · " + (run.name || "Schemalagt workflow"),
        "Schemalagd körning · " + (run.display_title || run.workflow_path || "Geografisk testnivå ej registrerad") +
        " · " + formatDate(run.created_at),
        run.conclusion, "blocked", run.html_url));
    }

    const recoveredEl = byId("recovered-runs-list");
    recoveredEl.replaceChildren();
    recoveredFailures.sort((a,b) => String(b.created_at || "").localeCompare(String(a.created_at || "")));
    if (!recoveredFailures.length) empty("recovered-runs-list", "Inga tidigare fel med en senare lyckad körning i urvalet.");
    else recoveredFailures.forEach((run) => {
      const recovery = runs.find((candidate) => workflowKey(candidate) === workflowKey(run) &&
        candidate.status === "completed" && candidate.conclusion === "success" &&
        String(candidate.created_at || "") > String(run.created_at || ""));
      renderItem(recoveredEl, run.project.project_name + " · " + (run.name || "Workflow"),
        "Fel " + formatDate(run.created_at) + " · senare lyckad körning " +
        formatDate(recovery?.created_at) + " · " + (run.event || "okänt event"),
        "Återhämtat", "done", run.html_url);
    });

    const projectsEl = byId("projects-list");
    projectsEl.replaceChildren();
    projects.forEach((project) => {
      const runCount = (project.latest_workflow_runs || []).length;
      const projectFailed = (project.latest_workflow_runs || []).filter((r) =>
        r.status === "completed" && r.conclusion && r.conclusion !== "success" &&
        !runs.some((candidate) => candidate.project.repository === project.repository &&
          String(candidate.workflow_id || candidate.workflow_path || candidate.name || "unknown") ===
            String(r.workflow_id || r.workflow_path || r.name || "unknown") &&
          candidate.status === "completed" && candidate.conclusion === "success" &&
          String(candidate.created_at || "") > String(r.created_at || ""))).length;
      const details = (project.open_work_items || []).length + " öppna poster · " +
        runCount + "/20 senaste körningar hämtade · " + projectFailed + " misslyckade bland dessa";
      renderItem(projectsEl, project.project_name || project.repository,
        project.repository + " · " + (project.private ? "Privat källrepo" : "Publikt källrepo") +
        " · senast avläst " + formatDate(project.observed_at_utc), details, projectFailed ? "blocked" : "done", project.html_url);
    });
  };

  const authConfig = window.PROJECT_MANAGER_AUTH;
  const authPanel = byId("auth-panel");
  const dashboard = byId("dashboard-content");
  const loginButton = byId("login-button");
  const logoutButton = byId("logout-button");
  const authMessage = byId("auth-message");
  const accessState = byId("access-state");

  const showAuthError = (message) => {
    authMessage.textContent = message;
    authPanel.hidden = false;
    dashboard.hidden = true;
    loginButton.hidden = false;
    loginButton.textContent = "Försök igen";
  };
  const setSignedIn = (account) => {
    accessState.textContent = account.username || account.name || "Inloggad";
    loginButton.hidden = true;
    loginButton.textContent = "Logga in";
    logoutButton.hidden = false;
  };
  const setSignedOut = () => {
    accessState.textContent = "Inte inloggad";
    loginButton.hidden = false;
    loginButton.textContent = "Logga in";
    logoutButton.hidden = true;
    dashboard.hidden = true;
    authPanel.hidden = false;
    authMessage.textContent = "Logga in med ett konto som har läsbehörighet till projekt-manager-containern.";
  };

  if (!window.msal || !authConfig) {
    showAuthError("Inloggningsbiblioteket eller den publika appkonfigurationen kunde inte laddas.");
    return;
  }

  const msalApp = new window.msal.PublicClientApplication({
    auth: {
      clientId: authConfig.clientId,
      authority: "https://login.microsoftonline.com/" + authConfig.tenantId,
      redirectUri: authConfig.redirectUri,
      navigateToLoginRequestUrl: false
    },
    cache: { cacheLocation: "sessionStorage", storeAuthStateInCookie: false }
  });

  const getStorageToken = async (account) => {
    const request = { scopes: [authConfig.storageScope], account };
    try {
      return await msalApp.acquireTokenSilent(request);
    } catch (error) {
      if (error instanceof window.msal.InteractionRequiredAuthError) {
        return await msalApp.acquireTokenPopup(request);
      }
      throw error;
    }
  };

  const loadPrivateSnapshot = async (account) => {
    setSignedIn(account);
    authMessage.textContent = "Hämtar behörighet för Azure Storage …";
    try {
      const tokenResult = await getStorageToken(account);
      const response = await fetch(authConfig.blobUrl, {
        method: "GET",
        cache: "no-store",
        headers: {
          "Authorization": "Bearer " + tokenResult.accessToken,
          "x-ms-date": new Date().toUTCString(),
          "x-ms-version": authConfig.storageApiVersion
        }
      });
      if (!response.ok) {
        throw new Error("Azure Blob svarade HTTP " + response.status +
          ". Kontrollera Storage Blob Data Reader, CORS och att snapshoten finns.");
      }
      const data = await response.json();
      render(data);
      authPanel.hidden = true;
      dashboard.hidden = false;
    } catch (error) {
      showAuthError("Kunde inte läsa den privata snapshoten: " + error.message +
        " Ingen projektdata visas. Kontrollera att kontot finns i rätt Entra-tenant och har läsbehörighet på project-manager-containern.");
    }
  };

  loginButton.addEventListener("click", async () => {
    loginButton.disabled = true;
    authMessage.textContent = "Öppnar Microsoft-inloggning …";
    try {
      const result = await msalApp.loginPopup({ scopes: [authConfig.storageScope] });
      msalApp.setActiveAccount(result.account);
      await loadPrivateSnapshot(result.account);
    } catch (error) {
      showAuthError("Inloggningen avbröts eller misslyckades: " + error.message);
    } finally {
      loginButton.disabled = false;
    }
  });

  logoutButton.addEventListener("click", async () => {
    const account = msalApp.getActiveAccount() || msalApp.getAllAccounts()[0];
    await msalApp.logoutPopup({ account, postLogoutRedirectUri: authConfig.redirectUri });
    setSignedOut();
  });

  const existingAccount = msalApp.getActiveAccount() || msalApp.getAllAccounts()[0];
  if (existingAccount) {
    msalApp.setActiveAccount(existingAccount);
    loadPrivateSnapshot(existingAccount);
  } else {
    setSignedOut();
  }
})();
