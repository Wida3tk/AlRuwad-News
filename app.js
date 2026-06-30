const seedArticles = [
  {
    id: "pak-gulf-economy",
    title: "إسلام آباد تبحث توسيع التعاون الاقتصادي مع دول الخليج",
    category: "باكستان والخليج",
    source: "Dawn",
    status: "منشور",
    importance: "مهم",
    summary: "قالت مصادر رسمية إن الحكومة الباكستانية تعمل على حزمة تفاهمات جديدة تشمل الاستثمار والطاقة والتحويلات المالية.",
    context: "يعكس التحرك رغبة باكستان في تنويع مصادر التمويل وتعزيز علاقاتها الاقتصادية مع العواصم الخليجية.",
    body: [
      "تدرس الحكومة الباكستانية توسيع التعاون الاقتصادي مع عدد من دول الخليج ضمن ملفات الاستثمار والطاقة وتحويلات العاملين في الخارج.",
      "وبحسب مصادر رسمية، تسعى إسلام آباد إلى جذب استثمارات جديدة في قطاعات البنية التحتية والطاقة، بالتزامن مع ضغوط اقتصادية داخلية.",
      "وتحظى العلاقات الخليجية الباكستانية بأهمية خاصة بسبب حجم الجالية الباكستانية في دول الخليج ودور التحويلات المالية في دعم الاقتصاد المحلي."
    ],
    tags: ["اقتصاد", "الخليج", "استثمار"],
    publishedAt: "28 يونيو 2026"
  }
];

if (location.hostname === "127.0.0.1" && location.port === "4173") {
  location.replace(`http://127.0.0.1:4174${location.pathname}${location.search}${location.hash}`);
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || "تعذر تنفيذ الطلب");
  }
  return data;
}

async function getArticles(status = "") {
  try {
    const query = status ? `?status=${encodeURIComponent(status)}` : "";
    return await api(`/api/articles${query}`);
  } catch {
    return seedArticles;
  }
}

let cachedAdminArticles = [];
let pendingDeleteId = "";
let loadedArticleSourceUrl = "";

function articleCard(article) {
  return `
    <a class="article-card" href="article.html?id=${encodeURIComponent(article.id)}">
      ${articleImage(article, "card")}
      <span class="eyebrow">${article.category}</span>
      <h3>${article.title}</h3>
      <p>${article.summary}</p>
      <div class="tag-row">${article.tags.map((tag) => `<span class="tag">${tag}</span>`).join("")}</div>
    </a>
  `;
}

function articleImage(article, variant = "card") {
  if (article.imageUrl) {
    return `<div class="news-image ${variant}"><img src="${article.imageUrl}" alt="${article.title}" loading="lazy"></div>`;
  }
  return `<div class="news-image ${variant} fallback"><span>${article.category || "الرواد"}</span></div>`;
}

function legacySlug(text) {
  const chars = [];
  for (const char of (text || "").trim().toLowerCase()) {
    if (/[\p{L}\p{N}]/u.test(char)) {
      chars.push(char);
    } else if (chars.length && chars[chars.length - 1] !== "-") {
      chars.push("-");
    }
  }
  return chars.join("").replace(/^-|-$/g, "").slice(0, 90);
}

async function findArticleByIdentifier(id) {
  try {
    return await api(`/api/articles/${encodeURIComponent(id)}`);
  } catch {
    const articles = await getArticles();
    return articles.find((article) => (
      article.id === id ||
      legacySlug(article.title) === id ||
      encodeURIComponent(article.id) === id ||
      encodeURIComponent(legacySlug(article.title)) === id
    ));
  }
}

async function renderHome() {
  const grid = document.querySelector("[data-article-grid]");
  const brief = document.querySelector("[data-brief-list]");
  const lead = document.querySelector("[data-lead-story]");
  if (!grid || !brief) return;

  const articles = await getArticles("منشور");
  if (lead && articles[0]) {
    lead.innerHTML = `
      ${articleImage(articles[0], "lead")}
      <div>
        <span class="eyebrow">${articles[0].category}</span>
        <h1>${articles[0].title}</h1>
        <p>${articles[0].summary}</p>
      </div>
      <div>
        <div class="story-meta">
          <span>المصدر: ${articles[0].source}</span>
          <span>ترجمة وتحرير: الرواد نيوز</span>
          <span>${articles[0].publishedAt}</span>
        </div>
        <div class="toolbar">
          <a class="button" href="article.html?id=${encodeURIComponent(articles[0].id)}">قراءة الخبر</a>
          <a class="button ghost" href="methodology.html">منهجيتنا</a>
        </div>
      </div>
    `;
  }
  grid.innerHTML = articles.slice(1, 7).map(articleCard).join("");
  brief.innerHTML = articles.slice(0, 5).map((article) => (
    `<li><a href="article.html?id=${encodeURIComponent(article.id)}">${article.title}</a></li>`
  )).join("");
}

function formPayload(status = "منشور") {
  return {
    id: document.querySelector("#articleId")?.value || undefined,
    title: document.querySelector("#title")?.value.trim(),
    category: document.querySelector("#category")?.value,
    source: document.querySelector("#source")?.value.trim(),
    sourceUrl: document.querySelector("#sourceUrl")?.value.trim(),
    imageUrl: document.querySelector("#imageUrl")?.value.trim(),
    originalLanguage: document.querySelector("#originalLanguage")?.value,
    originalText: document.querySelector("#originalText")?.value.trim(),
    status,
    importance: document.querySelector("#importance")?.value,
    summary: document.querySelector("#summary")?.value.trim(),
    context: document.querySelector("#context")?.value.trim(),
    body: (document.querySelector("#body")?.value || "").split(/\n+/).map((item) => item.trim()).filter(Boolean),
    tags: (document.querySelector("#tags")?.value || "").split(",").map((tag) => tag.trim()).filter(Boolean)
  };
}

function setField(selector, value) {
  const node = document.querySelector(selector);
  if (node) node.value = value || "";
}

function setSelectValue(selector, value) {
  const node = document.querySelector(selector);
  if (!node) return;
  const exists = [...node.options].some((option) => option.value === value);
  if (!exists && value) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    node.appendChild(option);
  }
  node.value = value || node.options[0]?.value || "";
}

function loadArticleIntoEditor(article) {
  setField("#articleId", article.id);
  loadedArticleSourceUrl = article.sourceUrl || "";
  setField("#source", article.source);
  setField("#sourceUrl", article.sourceUrl);
  setField("#imageUrl", article.imageUrl);
  setSelectValue("#category", article.category);
  setSelectValue("#originalLanguage", article.originalLanguage);
  setSelectValue("#importance", article.importance);
  setField("#tags", article.tags.join(", "));
  setField("#originalText", article.originalText);
  setField("#title", article.title);
  setField("#summary", article.summary);
  setField("#context", article.context);
  setField("#body", article.body.join("\n\n"));
  const title = document.querySelector("[data-editor-title]");
  if (title) title.textContent = "تعديل خبر";
  const note = document.querySelector("[data-save-note]");
  if (note) note.textContent = `تم فتح الخبر للتعديل: ${article.status}`;
  updatePreview();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetEditor() {
  setField("#articleId", "");
  loadedArticleSourceUrl = "";
  setField("#source", "Dawn");
  setField("#sourceUrl", "");
  setField("#imageUrl", "");
  setSelectValue("#category", "باكستان والخليج");
  setSelectValue("#originalLanguage", "إنجليزي");
  setSelectValue("#importance", "مهم");
  setField("#tags", "باكستان, الخليج, اقتصاد");
  setField("#originalText", "");
  setField("#title", "");
  setField("#summary", "");
  setField("#context", "");
  setField("#body", "");
  const title = document.querySelector("[data-editor-title]");
  if (title) title.textContent = "إضافة خبر جديد";
  const note = document.querySelector("[data-save-note]");
  if (note) note.textContent = "جاهز لإضافة خبر جديد.";
  updatePreview();
}

function markEditorAsNewArticle(message = "") {
  setField("#articleId", "");
  loadedArticleSourceUrl = "";
  const title = document.querySelector("[data-editor-title]");
  if (title) title.textContent = "إضافة خبر جديد";
  const note = document.querySelector("[data-save-note]");
  if (note && message) note.textContent = message;
}

function updatePreview() {
  const preview = document.querySelector("[data-preview]");
  if (!preview) return;

  const payload = formPayload();
  const title = payload.title || "عنوان الخبر العربي يظهر هنا";
  const summary = payload.summary || "ملخص قصير يوضح جوهر الخبر في سطرين.";
  const context = payload.context || "فقرة السياق تشرح لماذا يهم هذا الخبر للقارئ العربي.";
  const body = payload.body.length ? payload.body : ["نص الخبر المحرر يظهر هنا بعد الترجمة والمراجعة."];
  const source = payload.source || "المصدر الأصلي";
  const category = payload.category || "سياسة";

  preview.innerHTML = `
    ${articleImage(payload, "preview")}
    <span class="eyebrow">${category}</span>
    <h1>${title}</h1>
    <p class="summary">${summary}</p>
    <div class="context-box"><strong>السياق:</strong> ${context}</div>
    ${body.map((paragraph) => `<p>${paragraph}</p>`).join("")}
    <div class="story-meta"><span>المصدر: ${source}</span><span>ترجمة وتحرير: الرواد نيوز</span></div>
  `;
}

function setAdminState(authenticated) {
  document.querySelector("[data-login-panel]")?.classList.toggle("hidden", authenticated);
  document.querySelector("[data-editor-panel]")?.classList.toggle("hidden", !authenticated);
  document.querySelector("[data-preview]")?.classList.toggle("hidden", !authenticated);
  document.querySelector("[data-manager-panel]")?.classList.toggle("hidden", !authenticated);
  if (authenticated) loadArticleManager();
}

async function checkSession() {
  try {
    const me = await api("/api/me");
    setAdminState(me.authenticated);
  } catch {
    setAdminState(false);
  }
}

async function login() {
  const username = document.querySelector("#username")?.value.trim();
  const password = document.querySelector("#password")?.value;
  const note = document.querySelector("[data-login-note]");
  try {
    await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ username, password })
    });
    if (note) note.textContent = "";
    setAdminState(true);
    updatePreview();
  } catch (error) {
    if (note) note.textContent = error.message;
  }
}

async function logout() {
  await api("/api/logout", { method: "POST", body: "{}" }).catch(() => {});
  setAdminState(false);
}

async function generateDraftFromSource() {
  const note = document.querySelector("[data-save-note]");
  try {
    const hasSourceText = !!document.querySelector("#originalText")?.value.trim();
    const hasSourceUrl = !!document.querySelector("#sourceUrl")?.value.trim();
    if (!hasSourceText && hasSourceUrl) {
      if (note) note.textContent = "جاري استيراد الرابط قبل توليد المسودة...";
      await importFromUrl();
    }

    const payload = formPayload("مسودة");
    const draft = await api("/api/draft", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    document.querySelector("#title").value = draft.title;
    document.querySelector("#summary").value = draft.summary;
    document.querySelector("#context").value = draft.context;
    document.querySelector("#body").value = draft.body.join("\n\n");
    if (draft.title && draft.title !== "تطور جديد في باكستان يثير اهتمام الصحافة المحلية") {
      setSelectValue("#category", payload.category === "باكستان والخليج" ? "العالم" : payload.category);
    }
    if (note) note.textContent = "تم توليد مسودة عربية. راجعيها قبل النشر.";
    updatePreview();
  } catch (error) {
    if (note) note.textContent = error.message;
  }
}

async function importFromUrl() {
  const note = document.querySelector("[data-save-note]");
  const url = document.querySelector("#sourceUrl")?.value.trim();
  if (!url) {
    if (note) note.textContent = "ضعي رابط الخبر أولًا.";
    return;
  }

  try {
    markEditorAsNewArticle("سيتم إنشاء خبر جديد من هذا الرابط.");
    if (note) note.textContent = "جاري استيراد الخبر من الرابط...";
    const imported = await api("/api/import-url", {
      method: "POST",
      body: JSON.stringify({ url })
    });
    document.querySelector("#source").value = imported.source || "";
    document.querySelector("#sourceUrl").value = imported.sourceUrl || url;
    document.querySelector("#imageUrl").value = imported.imageUrl || "";
    document.querySelector("#originalLanguage").value = imported.originalLanguage === "English" ? "إنجليزي" : imported.originalLanguage || "إنجليزي";
    if (imported.category) setSelectValue("#category", imported.category);
    document.querySelector("#originalText").value = imported.originalText || "";
    if (imported.title) document.querySelector("#title").value = imported.title;
    if (imported.summary) document.querySelector("#summary").value = imported.summary;
    if (note) note.textContent = "تم استيراد النص الأصلي. اضغطي توليد مسودة عربية للصياغة.";
    updatePreview();
  } catch (error) {
    if (note) note.textContent = `تعذر الاستيراد: ${error.message}`;
  }
}

async function saveDraft(status) {
  const note = document.querySelector("[data-save-note]");
  const payload = formPayload(status);
  if (payload.id && payload.sourceUrl && loadedArticleSourceUrl && payload.sourceUrl !== loadedArticleSourceUrl) {
    payload.id = undefined;
    markEditorAsNewArticle("تم اعتبار الرابط الجديد خبرًا جديدًا.");
  }
  if (!payload.title || !payload.summary || !payload.body.length) {
    if (note) note.textContent = "العنوان والملخص ونص الخبر مطلوبة.";
    return;
  }

  try {
    const article = await api("/api/articles", {
      method: "POST",
      body: JSON.stringify(payload)
    });
    if (note) {
      note.innerHTML = status === "منشور"
        ? `تم نشر الخبر. <a href="article.html?id=${encodeURIComponent(article.id)}">افتحي الخبر</a>`
        : "تم حفظ الخبر كمسودة.";
    }
    setField("#articleId", article.id);
    await loadArticleManager();
  } catch (error) {
    if (note) note.textContent = error.message;
  }
}

function managerRow(article) {
  const statusClass = article.status === "منشور" ? "primary" : "";
  return `
    <article class="manager-row" data-row-id="${article.id}">
      <div>
        <h3>${article.title}</h3>
        <p>${article.category} | ${article.status} | ${article.source} | ${article.publishedAt}</p>
      </div>
      <div class="manager-actions">
        <button class="mini-button primary" type="button" data-edit-id="${article.id}">تعديل</button>
        <a class="mini-button ${statusClass}" href="article.html?id=${encodeURIComponent(article.id)}">فتح</a>
        <button class="mini-button" type="button" data-unpublish-id="${article.id}">إلغاء النشر</button>
        <button class="mini-button danger" type="button" data-delete-id="${article.id}">حذف</button>
      </div>
    </article>
  `;
}

function articleMatchesFilters(article) {
  const search = (document.querySelector("#managerSearch")?.value || "").trim().toLowerCase();
  const status = document.querySelector("#managerStatus")?.value || "";
  const category = document.querySelector("#managerCategory")?.value || "";
  const haystack = [
    article.title,
    article.summary,
    article.source,
    article.category,
    article.status,
    ...(article.tags || [])
  ].join(" ").toLowerCase();

  if (search && !haystack.includes(search)) return false;
  if (status && article.status !== status) return false;
  if (category && article.category !== category) return false;
  return true;
}

function populateManagerCategories() {
  const select = document.querySelector("#managerCategory");
  if (!select) return;
  const current = select.value;
  const categories = [...new Set(cachedAdminArticles.map((article) => article.category).filter(Boolean))].sort();
  select.innerHTML = `<option value="">كل التصنيفات</option>${categories.map((category) => `<option value="${category}">${category}</option>`).join("")}`;
  if (categories.includes(current)) select.value = current;
}

function renderArticleManagerList() {
  const manager = document.querySelector("[data-article-manager]");
  const count = document.querySelector("[data-manager-count]");
  if (!manager) return;

  const filtered = cachedAdminArticles.filter(articleMatchesFilters);
  if (count) {
    count.textContent = `عرض ${filtered.length} من ${cachedAdminArticles.length} خبر`;
  }
  if (!filtered.length) {
    manager.innerHTML = "<p style=\"color:var(--muted);font-weight:700;\">لا توجد نتائج مطابقة.</p>";
    return;
  }
  manager.innerHTML = filtered.map(managerRow).join("");
}

async function loadArticleManager() {
  const manager = document.querySelector("[data-article-manager]");
  if (!manager) return;
  try {
    pendingDeleteId = "";
    cachedAdminArticles = await api("/api/articles");
    populateManagerCategories();
    if (!cachedAdminArticles.length) {
      manager.innerHTML = "<p style=\"color:var(--muted);font-weight:700;\">لا توجد أخبار بعد.</p>";
      const count = document.querySelector("[data-manager-count]");
      if (count) count.textContent = "لا توجد أخبار محفوظة.";
      return;
    }
    renderArticleManagerList();
  } catch (error) {
    manager.innerHTML = `<p style="color:var(--red);font-weight:800;">${error.message}</p>`;
  }
}

async function unpublishArticle(id) {
  const article = cachedAdminArticles.find((item) => item.id === id);
  if (!article) return;
  await api("/api/articles", {
    method: "POST",
    body: JSON.stringify({ ...article, status: "مسودة" })
  });
  await loadArticleManager();
}

async function deleteArticle(id) {
  if (pendingDeleteId !== id) {
    pendingDeleteId = id;
    const button = document.querySelector(`[data-delete-id="${CSS.escape(id)}"]`);
    if (button) button.textContent = "تأكيد الحذف";
    return;
  }
  await api(`/api/articles/${encodeURIComponent(id)}`, { method: "DELETE" });
  pendingDeleteId = "";
  if (document.querySelector("#articleId")?.value === id) resetEditor();
  await loadArticleManager();
}

function handleManagerClick(event) {
  const editId = event.target.closest("[data-edit-id]")?.dataset.editId;
  const unpublishId = event.target.closest("[data-unpublish-id]")?.dataset.unpublishId;
  const deleteId = event.target.closest("[data-delete-id]")?.dataset.deleteId;

  if (editId) {
    const article = cachedAdminArticles.find((item) => item.id === editId);
    if (article) loadArticleIntoEditor(article);
  } else if (unpublishId) {
    unpublishArticle(unpublishId);
  } else if (deleteId) {
    deleteArticle(deleteId);
  }
}

async function renderAdmin() {
  if (!document.querySelector("[data-admin-page]")) return;
  await checkSession();

  document.querySelector("[data-login]")?.addEventListener("click", login);
  document.querySelector("[data-logout]")?.addEventListener("click", logout);
  document.querySelector("[data-new-article]")?.addEventListener("click", resetEditor);
  document.querySelector("[data-import-url]")?.addEventListener("click", importFromUrl);
  document.querySelector("[data-generate]")?.addEventListener("click", generateDraftFromSource);
  document.querySelector("[data-save-draft]")?.addEventListener("click", () => saveDraft("مسودة"));
  document.querySelector("[data-publish]")?.addEventListener("click", () => saveDraft("منشور"));
  document.querySelector("[data-refresh-articles]")?.addEventListener("click", loadArticleManager);
  document.querySelector("[data-article-manager]")?.addEventListener("click", handleManagerClick);
  document.querySelector("#sourceUrl")?.addEventListener("input", () => {
    const currentUrl = document.querySelector("#sourceUrl")?.value.trim() || "";
    if (document.querySelector("#articleId")?.value && currentUrl && currentUrl !== loadedArticleSourceUrl) {
      markEditorAsNewArticle("تم تغيير الرابط، وسيتم حفظ المادة كخبر جديد.");
    }
  });
  document.querySelector("#managerSearch")?.addEventListener("input", renderArticleManagerList);
  document.querySelector("#managerStatus")?.addEventListener("change", renderArticleManagerList);
  document.querySelector("#managerCategory")?.addEventListener("change", renderArticleManagerList);
  document.querySelectorAll("input, select, textarea").forEach((input) => {
    input.addEventListener("input", updatePreview);
    input.addEventListener("change", updatePreview);
  });
  updatePreview();
}

async function renderArticlePage() {
  const articleRoot = document.querySelector("[data-article-page]");
  if (!articleRoot) return;

  const params = new URLSearchParams(window.location.search);
  const id = params.get("id") || "pak-gulf-economy";
  let article;
  article = await findArticleByIdentifier(id);
  if (!article) {
    articleRoot.innerHTML = `
      <article class="article-body">
        <span class="eyebrow">غير متاح</span>
        <h1>لم يتم العثور على الخبر</h1>
        <p class="summary">قد يكون الرابط قديمًا أو أن المادة لم تعد منشورة.</p>
        <div class="toolbar">
          <a class="button" href="index.html">العودة للرئيسية</a>
          <a class="button ghost" href="methodology.html">منهجيتنا</a>
        </div>
      </article>
    `;
    return;
  }
  const articles = await getArticles("منشور");
  window.currentArticle = article;

  document.title = `${article.title} | الرواد نيوز`;
  articleRoot.innerHTML = `
    <article class="article-body">
      ${articleImage(article, "article")}
      <span class="eyebrow">${article.category}</span>
      <h1>${article.title}</h1>
      <p class="summary">${article.summary}</p>
      <div class="article-tools">
        <button class="button" type="button" data-copy-full>نسخ الخبر جاهزًا</button>
        <button class="button secondary" type="button" data-copy-brief>نسخ الملخص التنفيذي</button>
        ${article.sourceUrl ? `<a class="button ghost" href="${article.sourceUrl}" target="_blank" rel="noopener">المصدر الأصلي</a>` : ""}
        <span class="copy-note" data-copy-note></span>
      </div>
      <textarea class="copy-output hidden" data-copy-output readonly></textarea>
      <div class="story-meta">
        <span>${article.publishedAt}</span>
        <span>المصدر: ${article.source}</span>
        <span>ترجمة وتحرير: الرواد نيوز</span>
      </div>
      <div class="context-box"><strong>السياق:</strong> ${article.context}</div>
      ${article.body.map((paragraph) => `<p>${paragraph}</p>`).join("")}
      <div class="tag-row">${article.tags.map((tag) => `<span class="tag">${tag}</span>`).join("")}</div>
    </article>
    <aside class="side-panel">
      <div class="daily-brief">
        <h2>موجز اليوم</h2>
        <ul class="brief-list">
          ${articles.slice(0, 4).map((item) => `<li><a href="article.html?id=${encodeURIComponent(item.id)}">${item.title}</a></li>`).join("")}
        </ul>
      </div>
      <div class="source-box">
        <strong>منهجية الرواد</strong>
        <p>نذكر المصدر الأصلي، نعيد الصياغة عربيًا، ونضيف السياق بدون تبني موقف سياسي.</p>
      </div>
    </aside>
  `;
  articleRoot.querySelector("[data-copy-full]")?.addEventListener("click", () => copyArticleText("full"));
  articleRoot.querySelector("[data-copy-brief]")?.addEventListener("click", () => copyArticleText("brief"));
}

function buildFullArticleText(article) {
  return [
    article.title,
    "",
    article.summary,
    "",
    `السياق: ${article.context}`,
    "",
    ...article.body,
    "",
    `المصدر: ${article.source}`,
    "ترجمة وتحرير: الرواد نيوز"
  ].join("\n");
}

function buildBriefText(article) {
  return [
    `ملخص تنفيذي: ${article.title}`,
    "",
    article.summary,
    "",
    `لماذا يهم: ${article.context}`,
    "",
    `المصدر: ${article.source}`
  ].join("\n");
}

async function copyArticleText(type) {
  const article = window.currentArticle;
  const note = document.querySelector("[data-copy-note]");
  const output = document.querySelector("[data-copy-output]");
  if (!article) return;
  const text = type === "brief" ? buildBriefText(article) : buildFullArticleText(article);

  try {
    await navigator.clipboard.writeText(text);
    if (output) output.classList.add("hidden");
    if (note) note.textContent = type === "brief" ? "تم نسخ الملخص." : "تم نسخ الخبر.";
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    document.body.appendChild(area);
    area.select();
    const copied = document.execCommand("copy");
    area.remove();
    if (copied) {
      if (output) output.classList.add("hidden");
      if (note) note.textContent = "تم النسخ.";
    } else {
      showManualCopy(text, note, output);
    }
  }
}

function showManualCopy(text, note, output) {
  if (!output) return;
  output.value = text;
  output.classList.remove("hidden");
  output.focus();
  output.select();
  if (note) note.textContent = "حددي النص المنسوخ واضغطي Ctrl+C.";
}

renderHome();
renderAdmin();
renderArticlePage();
