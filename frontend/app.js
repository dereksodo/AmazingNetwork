// Minimal client for contract C-POSTS. No framework on purpose (PoC simplification).
const API_BASE = window.CONNECT_API_BASE || "http://127.0.0.1:8000";

const $ = (id) => document.getElementById(id);

async function call(method, path, body) {
  const headers = { "Content-Type": "application/json" };
  const user = $("user").value;
  if (user) headers["X-Demo-User"] = user;

  $("request").textContent =
    `${method} ${path}\n` +
    Object.entries(headers).map(([k, v]) => `${k}: ${v}`).join("\n") +
    (body ? `\n\n${JSON.stringify(body, null, 2)}` : "");

  try {
    const res = await fetch(API_BASE + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json();
    $("status").textContent = `${res.status} ${res.statusText}`;
    $("status").className = res.ok ? "ok" : "err";
    $("response").textContent = JSON.stringify(data, null, 2);
    return { ok: res.ok, data };
  } catch (err) {
    $("status").textContent = "network error";
    $("status").className = "err";
    $("response").textContent = `Is the backend running at ${API_BASE}?\n${err}`;
    return { ok: false };
  }
}

$("create-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const body = {
    type: f.get("type"),
    community_id: f.get("community_id") ? Number(f.get("community_id")) : null,
    visibility: f.get("visibility"),
    title: f.get("title") || null,
    body_html: f.get("body_html"),
  };
  const { ok, data } = await call("POST", "/api/v1/posts", body);
  if (ok) {
    $("get-form").post_id.value = data.id;
    loadFeed(false);
  }
});

$("get-form").addEventListener("submit", (e) => {
  e.preventDefault();
  call("GET", `/api/v1/posts/${e.target.post_id.value}`);
});

async function loadFeed(showExchange = true) {
  const feed = $("feed");
  feed.replaceChildren();
  if (!showExchange) {
    // Refresh the list without overwriting the request/response panel.
    const res = await fetch(API_BASE + "/api/v1/posts", { headers: { "X-Demo-User": $("user").value } });
    if (res.ok) render((await res.json()).items);
    return;
  }
  const { ok, data } = await call("GET", "/api/v1/posts");
  if (ok) render(data.items);
}

function render(items) {
  const feed = $("feed");
  if (!items.length) {
    feed.innerHTML = "<li><em>No posts visible to this user.</em></li>";
    return;
  }
  for (const p of items) {
    const li = document.createElement("li");
    const meta = document.createElement("div");
    meta.className = "meta";
    meta.textContent =
      `#${p.id} · ${p.author.display_name} · ${p.type} · visibility: ${p.visibility}` +
      (p.community_id ? ` · community ${p.community_id}` : "");
    li.append(meta);
    if (p.title) {
      const h = document.createElement("strong");
      h.textContent = p.title;
      li.append(h);
    }
    const body = document.createElement("div");
    body.innerHTML = p.body_html; // already sanitized by the server (allowlist)
    li.append(body);
    feed.append(li);
  }
}

$("feed-btn").addEventListener("click", () => loadFeed(true));
$("user").addEventListener("change", () => loadFeed(false));
loadFeed(false);
