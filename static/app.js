const tokenKey = "student_portal_token";

function token() {
  return localStorage.getItem(tokenKey);
}

function requireAuth() {
  if (!token()) {
    window.location.href = "/";
  }
}

function setMessage(id, message, isSuccess = false) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = message || "";
  el.classList.toggle("success", Boolean(isSuccess));
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token()) headers.set("Authorization", `Bearer ${token()}`);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(path, { ...options, headers });
  if (response.status === 401) {
    localStorage.removeItem(tokenKey);
    window.location.href = "/";
    throw new Error("Please sign in again.");
  }

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    throw new Error(data?.detail || data?.message || "Something went wrong.");
  }
  return data;
}

function initLoginPage() {
  if (token()) window.location.href = "/dashboard";

  document.getElementById("loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("formMessage", "");
    const form = new FormData(event.currentTarget);
    const body = new URLSearchParams();
    body.set("username", form.get("username"));
    body.set("password", form.get("password"));

    try {
      const response = await fetch("/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Invalid username or password.");
      localStorage.setItem(tokenKey, data.access_token);
      window.location.href = "/dashboard";
    } catch (error) {
      setMessage("formMessage", error.message);
    }
  });
}

function initRegisterPage() {
  document.getElementById("registerForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("formMessage", "");
    const form = new FormData(event.currentTarget);

    try {
      await apiFetch("/register", {
        method: "POST",
        body: JSON.stringify({
          username: form.get("username"),
          password: form.get("password"),
        }),
      });
      setMessage("formMessage", "Account created. Redirecting to sign in...", true);
      setTimeout(() => {
        window.location.href = "/";
      }, 900);
    } catch (error) {
      setMessage("formMessage", error.message);
    }
  });
}

function bindLogout() {
  const button = document.getElementById("logoutButton");
  if (!button) return;
  button.addEventListener("click", () => {
    localStorage.removeItem(tokenKey);
    window.location.href = "/";
  });
}

function normalizeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function componentValue(component, key) {
  const variants = {
    weightage: ["weightage", "Weightage"],
    total_marks: ["total_marks", "Total_marks", "TotalMarks"],
    obtained_marks: ["obtained_marks", "Obtained_marks", "ObtainedMarks"],
  };
  const keys = variants[key] || [key];
  for (const name of keys) {
    if (component[name] !== undefined) return component[name];
  }
  return 0;
}

async function loadDashboardCourses() {
  const courses = await apiFetch("/courses");
  const grid = document.getElementById("courseGrid");
  const empty = document.getElementById("emptyState");
  grid.innerHTML = "";

  document.getElementById("courseCount").textContent = courses.length;
  empty.classList.toggle("visible", courses.length === 0);

  let componentCount = 0;
  let scoreTotal = 0;
  let scoreSeen = 0;

  for (const course of courses) {
    const card = document.createElement("a");
    card.className = "course-card";
    card.href = `/student/course/${course.course_code}`;
    card.innerHTML = `
      <span class="course-code">Course ${course.course_code}</span>
      <h3>${course.course_name}</h3>
      <span>Open ledger</span>
    `;
    grid.appendChild(card);

    try {
      const components = await apiFetch(`/course/${course.course_code}`);
      componentCount += components.length;
      components.forEach((component) => {
        const total = normalizeNumber(componentValue(component, "total_marks"));
        const obtained = normalizeNumber(componentValue(component, "obtained_marks"));
        if (total > 0) {
          scoreTotal += (obtained / total) * 100;
          scoreSeen += 1;
        }
      });
    } catch {
      // Keep the dashboard useful even if one course fails to load.
    }
  }

  document.getElementById("componentCount").textContent = componentCount;
  document.getElementById("averageScore").textContent =
    scoreSeen > 0 ? `${Math.round(scoreTotal / scoreSeen)}%` : "--";
}

function initDashboardPage() {
  requireAuth();
  bindLogout();
  loadDashboardCourses();

  document.getElementById("refreshCourses").addEventListener("click", loadDashboardCourses);
  document.getElementById("courseForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("courseMessage", "");
    const form = new FormData(event.currentTarget);

    try {
      await apiFetch("/addcourse", {
        method: "POST",
        body: JSON.stringify({
          course_code: Number(form.get("course_code")),
          course_name: form.get("course_name"),
        }),
      });
      event.currentTarget.reset();
      setMessage("courseMessage", "Course added.", true);
      await loadDashboardCourses();
    } catch (error) {
      setMessage("courseMessage", error.message);
    }
  });
}

async function loadCourseComponents(courseCode) {
  const components = await apiFetch(`/course/${courseCode}`);
  const rows = document.getElementById("componentRows");
  const empty = document.getElementById("emptyState");
  rows.innerHTML = "";

  let weightageTotal = 0;
  let weightedScoreSum = 0;

  components.forEach((component) => {
    const weightage = normalizeNumber(componentValue(component, "weightage"));
    const total = normalizeNumber(componentValue(component, "total_marks"));
    const obtained = normalizeNumber(componentValue(component, "obtained_marks"));
    const score = total > 0 ? (obtained / total) * 100 : 0;
    weightageTotal += weightage;
    weightedScoreSum += total > 0 ? score * weightage : 0;

    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${component.component_type}</td>
      <td>${weightage}%</td>
      <td>${total}</td>
      <td>${obtained}</td>
      <td>${Math.round(score)}%</td>
    `;
    rows.appendChild(row);
  });

  const finalScore = weightageTotal > 0 ? Math.round(weightedScoreSum / weightageTotal) : 0;

  document.getElementById("componentCount").textContent = components.length;
  document.getElementById("weightageTotal").textContent = `${Math.round(weightageTotal)}%`;
  document.getElementById("courseScore").textContent =
    components.length > 0 ? `${finalScore}%` : "--";
  empty.classList.toggle("visible", components.length === 0);
}

function initCourseDetailPage(courseCode) {
  requireAuth();
  bindLogout();
  loadCourseComponents(courseCode);

  document.getElementById("componentForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    setMessage("componentMessage", "");
    const form = new FormData(event.currentTarget);

    try {
      await apiFetch(`/course/${courseCode}/addComponent`, {
        method: "POST",
        body: JSON.stringify({
          component_type: form.get("component_type"),
          Weightage: Number(form.get("weightage")),
          Total_marks: Number(form.get("total_marks")),
          Obtained_marks: Number(form.get("obtained_marks")),
        }),
      });
      event.currentTarget.reset();
      setMessage("componentMessage", "Component added.", true);
      await loadCourseComponents(courseCode);
    } catch (error) {
      setMessage("componentMessage", error.message);
    }
  });
}