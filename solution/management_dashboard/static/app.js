const REFRESH_MS = 3000;

const state = {
  query: "",
  status: "",
  desk: "",
  selectedTicketRef: null,
  tickets: [],
};

let searchDebounce = null;
let refreshTimer = null;

const dom = {
  lastRefresh: document.getElementById("last-refresh"),
  kpiTotal: document.getElementById("kpi-total"),
  kpiActive: document.getElementById("kpi-active"),
  kpiAutoRate: document.getElementById("kpi-auto-rate"),
  kpiAutoCount: document.getElementById("kpi-auto-count"),
  kpiMulti: document.getElementById("kpi-multi"),
  kpiRes: document.getElementById("kpi-res"),
  kpiOver24: document.getElementById("kpi-over24"),
  kpiInbound: document.getElementById("kpi-inbound"),
  filterQuery: document.getElementById("filter-query"),
  filterStatus: document.getElementById("filter-status"),
  filterDesk: document.getElementById("filter-desk"),
  manualRefresh: document.getElementById("manual-refresh"),
  ticketCount: document.getElementById("ticket-count"),
  ticketsBody: document.getElementById("tickets-body"),
  desksList: document.getElementById("desks-list"),
  agentsList: document.getElementById("agents-list"),
  eventsList: document.getElementById("events-list"),
  detailTicketRef: document.getElementById("detail-ticket-ref"),
  detailEmpty: document.getElementById("detail-empty"),
  detailContent: document.getElementById("detail-content"),
  detailSnapshot: document.getElementById("detail-snapshot"),
  detailTrace: document.getElementById("detail-trace"),
  detailDeskJourney: document.getElementById("detail-desk-journey"),
  detailAssignments: document.getElementById("detail-assignments"),
  detailMessages: document.getElementById("detail-messages"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function toPlainText(value) {
  const raw = String(value ?? "");
  if (raw.includes("<") && raw.includes(">")) {
    const doc = new DOMParser().parseFromString(raw, "text/html");
    return (doc.body.textContent || "").trim();
  }
  return raw;
}

function fmtMinutes(value) {
  if (value === null || value === undefined) return "-";
  const total = Number(value);
  if (Number.isNaN(total)) return "-";
  if (total < 60) return `${total}m`;
  const hours = Math.floor(total / 60);
  const mins = total % 60;
  if (hours < 24) return `${hours}h ${mins}m`;
  const days = Math.floor(hours / 24);
  const remHours = hours % 24;
  return `${days}d ${remHours}h`;
}

function fmtHours(value) {
  if (value === null || value === undefined) return "-";
  const num = Number(value);
  if (Number.isNaN(num)) return "-";
  return `${num.toFixed(1)}h`;
}

function fmtTimestamp(value) {
  if (!value) return "-";
  return String(value).replace("T", " ").replace("+00:00", " UTC");
}

function statusClass(status) {
  return `status-${String(status || "").toLowerCase()}`;
}

function yesNoBadge(flag) {
  return flag
    ? '<span class="badge bool-yes">YES</span>'
    : '<span class="badge bool-no">NO</span>';
}

async function fetchJson(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} for ${path}`);
  }
  return res.json();
}

function buildTicketsUrl() {
  const params = new URLSearchParams();
  params.set("limit", "300");
  if (state.status) params.set("status", state.status);
  if (state.desk) params.set("desk", state.desk);
  if (state.query) params.set("query", state.query);
  return `/api/tickets?${params.toString()}`;
}

function renderOverview(data) {
  dom.kpiTotal.textContent = `${data.total_tickets}`;
  dom.kpiActive.textContent = `${data.active_tickets}`;
  dom.kpiAutoRate.textContent = `${data.automatable_rate_pct}%`;
  dom.kpiAutoCount.textContent = `${data.automatable_tickets} automatable tickets`;
  dom.kpiMulti.textContent = `${data.multi_desk_tickets}`;
  dom.kpiRes.textContent = fmtHours(data.avg_resolution_hours);
  dom.kpiOver24.textContent = `${data.active_over_24h}`;
  dom.kpiInbound.textContent = `${data.inbound_last_15m}`;
}

function renderDeskFilter(desks) {
  const current = dom.filterDesk.value;
  const options = ['<option value="">All desks</option>'];
  for (const desk of desks) {
    options.push(`<option value="${escapeHtml(desk.desk_code)}">${escapeHtml(desk.desk_name)} (${escapeHtml(desk.desk_code)})</option>`);
  }
  dom.filterDesk.innerHTML = options.join("");
  dom.filterDesk.value = current && desks.some((d) => d.desk_code === current) ? current : "";
  state.desk = dom.filterDesk.value;
}

function renderTickets(data) {
  state.tickets = data.tickets || [];
  dom.ticketCount.textContent = `${state.tickets.length} records`;

  if (!state.tickets.length) {
    dom.ticketsBody.innerHTML = '<tr><td colspan="8"><p class="empty">No tickets match the current filter.</p></td></tr>';
    return;
  }

  dom.ticketsBody.innerHTML = state.tickets
    .map((t) => {
      const owner = t.owner_agent_name || t.owner_agent_code || "Unassigned";
      const desk = `${t.current_desk_name || "-"} (${t.current_desk_code || "-"})`;
      return `
      <tr class="ticket-row ${state.selectedTicketRef === t.ticket_ref ? "is-selected" : ""}" data-ticket-ref="${escapeHtml(t.ticket_ref)}">
        <td>
          <strong class="ticker">${escapeHtml(t.ticket_ref)}</strong><br />
          <span class="muted">${escapeHtml(t.priority || "-")}</span>
        </td>
        <td>
          <span class="badge ${statusClass(t.status)}">${escapeHtml(t.status)}</span>
          <div style="margin-top:5px">${yesNoBadge(t.automatable)} ${yesNoBadge(t.requires_multi_desk)}</div>
        </td>
        <td>${escapeHtml(t.client_name)}<br /><span class="muted">${escapeHtml(t.requester_email)}</span></td>
        <td>${escapeHtml(t.intent_code)}<br /><span class="muted">${escapeHtml(t.intent_name)}</span></td>
        <td>${escapeHtml(owner)}</td>
        <td>${escapeHtml(desk)}</td>
        <td>${fmtMinutes(t.created_age_min)}</td>
        <td>${fmtMinutes(t.last_event_age_min)}<br /><span class="muted">${escapeHtml(fmtTimestamp(t.last_event_at))}</span></td>
      </tr>`;
    })
    .join("");
}

function renderDesks(data) {
  const desks = data.desks || [];
  renderDeskFilter(desks);

  if (!desks.length) {
    dom.desksList.innerHTML = '<li class="stat-item"><p class="empty">No desk data.</p></li>';
    return;
  }

  dom.desksList.innerHTML = desks
    .map((d) => {
      const age = Number(d.avg_active_age_hours || 0);
      return `
      <li class="stat-item">
        <div class="stat-top">
          <p class="stat-main">${escapeHtml(d.desk_name)} (${escapeHtml(d.desk_code)})</p>
          <span class="badge ${d.active_tickets > 0 ? "status-in_progress" : "status-closed"}">${d.active_tickets} active</span>
        </div>
        <p class="stat-sub">${escapeHtml(d.specialty)}</p>
        <p class="stat-sub">Escalated: ${d.escalated_tickets} | Multi-desk active: ${d.active_multi_desk} | Agents: ${d.active_agents}</p>
        <p class="stat-sub">Avg active age: ${age.toFixed(1)}h</p>
      </li>`;
    })
    .join("");
}

function renderAgents(data) {
  const agents = (data.agents || []).filter((a) => a.is_active).slice(0, 12);
  if (!agents.length) {
    dom.agentsList.innerHTML = '<li class="stat-item"><p class="empty">No active agents.</p></li>';
    return;
  }

  dom.agentsList.innerHTML = agents
    .map((a) => {
      const pct = Math.min(Math.max(Math.round(a.load_ratio * 100), 0), 100);
      return `
      <li class="stat-item">
        <div class="stat-top">
          <p class="stat-main">${escapeHtml(a.full_name)} (${escapeHtml(a.agent_code)})</p>
          <span class="badge ${pct >= 80 ? "status-escalated" : "status-in_progress"}">${pct}% load</span>
        </div>
        <p class="stat-sub">${escapeHtml(a.desk_name)} (${escapeHtml(a.desk_code)}) | ${a.open_ticket_count}/${a.max_open_tickets} open</p>
        <div class="load-track"><div class="load-fill" style="width:${pct}%"></div></div>
      </li>`;
    })
    .join("");
}

function renderEvents(data) {
  const events = data.events || [];
  if (!events.length) {
    dom.eventsList.innerHTML = '<li class="stat-item"><p class="empty">No recent exchanges.</p></li>';
    return;
  }

  dom.eventsList.innerHTML = events
    .slice(0, 15)
    .map((e) => {
      return `
      <li class="stat-item">
        <div class="stat-top">
          <p class="stat-main">${escapeHtml(e.ticket_ref)} <span class="badge ${statusClass(e.ticket_status)}">${escapeHtml(e.ticket_status)}</span></p>
          <span class="badge ${e.direction === "INBOUND" ? "status-in_progress" : "status-closed"}">${escapeHtml(e.direction)}</span>
        </div>
        <p class="stat-sub">${escapeHtml(e.subject)}</p>
        <p class="stat-sub">${escapeHtml(fmtTimestamp(e.sent_at))}</p>
      </li>`;
    })
    .join("");
}

function renderSnapshot(ticket) {
  const cells = [
    ["Ticket", ticket.ticket_ref],
    ["Status", ticket.status],
    ["Priority", ticket.priority],
    ["Client", `${ticket.client_name} (${ticket.client_code})`],
    ["Intent", `${ticket.intent_name} (${ticket.intent_code})`],
    ["Owner", ticket.owner_agent_name ? `${ticket.owner_agent_name} (${ticket.owner_agent_code})` : "Unassigned"],
    ["Current Desk", `${ticket.current_desk_name} (${ticket.current_desk_code})`],
    ["Channel", ticket.channel],
    ["Requester", ticket.requester_email],
    ["Age", fmtMinutes(ticket.age_minutes)],
    ["Created", fmtTimestamp(ticket.created_at)],
    ["First Response", fmtTimestamp(ticket.first_response_at)],
  ];

  dom.detailSnapshot.innerHTML = cells
    .map(
      ([label, value]) => `
      <div class="snapshot-cell">
        <p class="snapshot-label">${escapeHtml(label)}</p>
        <p class="snapshot-value">${escapeHtml(value || "-")}</p>
      </div>
    `
    )
    .join("");
}

function renderTrace(trace) {
  if (!trace.length) {
    dom.detailTrace.innerHTML = '<li class="detail-item"><p class="empty">No routing trace yet.</p></li>';
    return;
  }

  dom.detailTrace.innerHTML = trace
    .map((step) => {
      const actor = step.agent_name ? `${step.actor_type} (${step.agent_name})` : step.actor_type;
      return `
      <li class="detail-item">
        <p><strong>#${step.step_seq} ${escapeHtml(step.node_name)}</strong></p>
        <p>Decision: ${escapeHtml(step.decision)}</p>
        <p>Actor: ${escapeHtml(actor)}</p>
        <p class="muted">${escapeHtml(step.rationale || "")}</p>
        <p class="muted">${escapeHtml(fmtTimestamp(step.created_at))}</p>
      </li>`;
    })
    .join("");
}

function renderDeskJourney(plan, hops) {
  if (!plan.length && !hops.length) {
    dom.detailDeskJourney.innerHTML = '<li class="detail-item"><p class="empty">No desk route data.</p></li>';
    return;
  }

  const parts = [];
  if (plan.length) {
    parts.push(...plan.map((p) => `
      <li class="detail-item">
        <p><strong>Plan #${p.step_seq}: ${escapeHtml(p.desk_name)} (${escapeHtml(p.desk_code)})</strong></p>
        <p class="muted">${escapeHtml(p.step_reason || "")}</p>
      </li>`));
  }

  if (hops.length) {
    parts.push(...hops.map((h) => {
      const fromDesk = h.from_desk_code ? `${h.from_desk_name} (${h.from_desk_code})` : "Entry";
      const toDesk = `${h.to_desk_name} (${h.to_desk_code})`;
      const actor = h.agent_name ? `${h.agent_name} (${h.agent_code})` : "System";
      return `
      <li class="detail-item">
        <p><strong>Hop #${h.hop_seq}: ${escapeHtml(fromDesk)} -> ${escapeHtml(toDesk)}</strong></p>
        <p>${escapeHtml(h.hop_reason || "")}</p>
        <p class="muted">By ${escapeHtml(actor)} at ${escapeHtml(fmtTimestamp(h.hopped_at))}</p>
      </li>`;
    }));
  }

  dom.detailDeskJourney.innerHTML = parts.join("");
}

function renderAssignments(assignments) {
  if (!assignments.length) {
    dom.detailAssignments.innerHTML = '<li class="detail-item"><p class="empty">No assignment records.</p></li>';
    return;
  }

  dom.detailAssignments.innerHTML = assignments
    .map((a) => {
      return `
      <li class="detail-item">
        <p><strong>${escapeHtml(a.agent_name)} (${escapeHtml(a.agent_code)})</strong> - ${escapeHtml(a.assignment_role)}</p>
        <p>${escapeHtml(a.desk_name)} (${escapeHtml(a.desk_code)})</p>
        <p class="muted">${escapeHtml(a.assignment_reason || "")}</p>
        <p class="muted">Assigned: ${escapeHtml(fmtTimestamp(a.assigned_at))}${a.released_at ? ` | Released: ${escapeHtml(fmtTimestamp(a.released_at))}` : ""}</p>
      </li>`;
    })
    .join("");
}

function renderMessages(messages) {
  if (!messages.length) {
    dom.detailMessages.innerHTML = '<li class="exchange-item"><p class="empty">No messages available.</p></li>';
    return;
  }

  dom.detailMessages.innerHTML = messages
    .map((m) => {
      const directionClass = m.direction === "INBOUND" ? "status-in_progress" : "status-closed";
      const body = toPlainText(m.body);
      return `
      <li class="exchange-item">
        <div class="exchange-meta">
          <span><span class="badge ${directionClass}">${escapeHtml(m.direction)}</span> ${escapeHtml(m.sender_email)} -> ${escapeHtml(m.recipient_email)}</span>
          <span>${escapeHtml(fmtTimestamp(m.sent_at))}</span>
        </div>
        <p class="exchange-subject">${escapeHtml(m.subject)}</p>
        <p class="exchange-body">${escapeHtml(body)}</p>
      </li>`;
    })
    .join("");
}

async function loadDetail(ticketRef, keepSelection = true) {
  if (!ticketRef) return;

  try {
    const data = await fetchJson(`/api/tickets/${encodeURIComponent(ticketRef)}`);
    if (!keepSelection) {
      state.selectedTicketRef = ticketRef;
    }

    dom.detailTicketRef.textContent = data.ticket.ticket_ref;
    dom.detailEmpty.hidden = true;
    dom.detailContent.hidden = false;

    renderSnapshot(data.ticket);
    renderTrace(data.routing_trace || []);
    renderDeskJourney(data.desk_plan || [], data.desk_hops || []);
    renderAssignments(data.assignments || []);
    renderMessages(data.messages || []);
  } catch (error) {
    console.error("Failed to load detail", error);
    dom.detailTicketRef.textContent = "Detail unavailable";
  }
}

async function refreshDashboard(refreshDetail = true) {
  try {
    const [overview, tickets, desks, agents, events] = await Promise.all([
      fetchJson("/api/overview"),
      fetchJson(buildTicketsUrl()),
      fetchJson("/api/desks/summary"),
      fetchJson("/api/agents/load"),
      fetchJson("/api/events/recent?limit=25"),
    ]);

    renderOverview(overview);
    renderTickets(tickets);
    renderDesks(desks);
    renderAgents(agents);
    renderEvents(events);

    if (refreshDetail && state.selectedTicketRef) {
      const stillExists = state.tickets.some((t) => t.ticket_ref === state.selectedTicketRef);
      if (stillExists) {
        await loadDetail(state.selectedTicketRef, true);
      }
    }

    dom.lastRefresh.textContent = new Date().toLocaleTimeString();
  } catch (error) {
    console.error("Dashboard refresh failed", error);
    dom.lastRefresh.textContent = "Refresh error";
  }
}

function onFiltersChanged() {
  state.query = dom.filterQuery.value.trim();
  state.status = dom.filterStatus.value;
  state.desk = dom.filterDesk.value;
  refreshDashboard(false);
}

function bindEvents() {
  dom.manualRefresh.addEventListener("click", () => refreshDashboard(true));

  dom.filterStatus.addEventListener("change", onFiltersChanged);
  dom.filterDesk.addEventListener("change", onFiltersChanged);

  dom.filterQuery.addEventListener("input", () => {
    if (searchDebounce) clearTimeout(searchDebounce);
    searchDebounce = setTimeout(onFiltersChanged, 260);
  });

  dom.ticketsBody.addEventListener("click", (event) => {
    const row = event.target.closest("tr[data-ticket-ref]");
    if (!row) return;

    const ref = row.getAttribute("data-ticket-ref");
    if (!ref) return;

    state.selectedTicketRef = ref;
    renderTickets({ tickets: state.tickets });
    loadDetail(ref, true);
  });
}

async function init() {
  bindEvents();
  await refreshDashboard(true);

  refreshTimer = setInterval(() => {
    refreshDashboard(true);
  }, REFRESH_MS);

  window.addEventListener("beforeunload", () => {
    if (refreshTimer) clearInterval(refreshTimer);
  });
}

init();
