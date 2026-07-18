<script setup>
import { computed, onMounted, ref } from "vue";

const apiBase = ref(import.meta.env.VITE_API_BASE?.trim() || "/api");
const jobDescriptions = ref([
  {
    id: crypto.randomUUID(),
    title: "Data Analyst",
    text: "We need a Data Analyst with Python, SQL, dashboarding, data cleaning, and stakeholder communication experience.",
  },
]);
const resumeUploadGroups = ref([
  {
    id: crypto.randomUUID(),
    files: [],
  },
]);
const topK = ref(5);
const explain = ref(true);
const loading = ref(false);
const healthLoading = ref(false);
const error = ref("");
const results = ref([]);
const health = ref(null);

const validJds = computed(() => jobDescriptions.value.filter((item) => item.text.trim().length >= 20));
const canSubmit = computed(
  () => validJds.value.length > 0 && resumeUploadGroups.value.some((group) => group.files.length > 0) && !loading.value,
);

function addJobDescription() {
  jobDescriptions.value.push({ id: crypto.randomUUID(), title: `Job description ${jobDescriptions.value.length + 1}`, text: "" });
}

function removeJobDescription(id) {
  if (jobDescriptions.value.length === 1) return;
  jobDescriptions.value = jobDescriptions.value.filter((item) => item.id !== id);
}

function addResume() {
  resumeUploadGroups.value.push({
    id: crypto.randomUUID(),
    files: [],
  });
}

function removeResumeGroup(id) {
  if (resumeUploadGroups.value.length === 1) return;
  resumeUploadGroups.value = resumeUploadGroups.value.filter((group) => group.id !== id);
}

function handleFiles(event, id) {
  const group = resumeUploadGroups.value.find((item) => item.id === id);
  if (!group) return;
  group.files = Array.from(event.target.files || []);
}

async function checkHealth() {
  healthLoading.value = true;
  try {
    const response = await fetch(`${apiBase.value}/health`);
    if (!response.ok) throw new Error(await response.text());
    health.value = await response.json();
    error.value = "";
  } catch {
    health.value = null;
    error.value = "API is not ready. Start FastAPI on port 8000, then refresh.";
  } finally {
    healthLoading.value = false;
  }
}

async function findMatches() {
  if (!canSubmit.value) return;

  loading.value = true;
  error.value = "";
  results.value = [];

  const jds = validJds.value.map((item, index) => ({
    id: item.id,
    title: item.title.trim() || `Job description ${index + 1}`,
    text: item.text.trim(),
  }));
  const resumeTexts = [];

  try {
    const form = new FormData();
    form.append("job_descriptions_json", JSON.stringify(jds));
    form.append("resume_texts_json", JSON.stringify(resumeTexts));
    form.append("top_k", String(topK.value));
    form.append("explain", String(explain.value));
    resumeUploadGroups.value.forEach((group) => {
      group.files.forEach((file) => form.append("resume_files", file));
    });

    const response = await fetch(`${apiBase.value}/match/upload`, {
      method: "POST",
      body: form,
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      throw new Error(payload?.detail || "Request failed");
    }

    const data = await response.json();
    results.value = data.results || [];
  } catch (err) {
    error.value = err.message;
  } finally {
    loading.value = false;
  }
}

function scorePercent(score) {
  return Math.round(Number(score) * 100);
}

function scoreLabel(score) {
  const percent = scorePercent(score);
  if (percent >= 75) return "Strong";
  if (percent >= 55) return "Good";
  return "Review";
}

onMounted(checkHealth);
</script>

<template>
  <main class="min-h-screen bg-slate-950 text-slate-900">
    <div class="mx-auto max-w-7xl px-4 py-6 md:px-6 lg:px-8">
      <section class="overflow-hidden rounded-[28px] border border-white/10 bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-950 shadow-[0_25px_80px_-30px_rgba(16,185,129,0.55)]">
        <div class="flex flex-col gap-4 px-5 py-5 md:flex-row md:items-center md:justify-between md:px-7">
          <div>
            <p class="text-xs font-semibold uppercase tracking-[0.28em] text-emerald-300">Resume JD Matcher</p>
            <h1 class="mt-2 text-3xl font-semibold text-white md:text-4xl">Match resumes with job descriptions in one polished workflow</h1>
          </div>

          <div class="flex flex-wrap items-center gap-3 text-sm">
            <span
              class="inline-flex items-center gap-2 rounded-full border px-3 py-2"
              :class="health ? 'border-emerald-400/40 bg-emerald-500/10 text-emerald-100' : 'border-white/10 bg-white/5 text-slate-300'"
            >
              <span class="h-2.5 w-2.5 rounded-full" :class="health ? 'bg-emerald-400' : 'bg-amber-400'"></span>
              {{ health ? `Model: ${health.embedding_model}` : healthLoading ? 'Checking API' : 'API offline' }}
            </span>
            <button class="rounded-full border border-white/15 bg-white/10 px-4 py-2 font-medium text-white transition hover:bg-white/15" type="button" @click="checkHealth">
              Refresh
            </button>
          </div>
        </div>
      </section>

      <section class="mx-auto mt-6 grid gap-5 xl:grid-cols-[520px_1fr]">
        <aside class="space-y-5">
          <section class="rounded-[24px] border border-slate-800 bg-slate-900/85 p-4 shadow-[0_18px_45px_-24px_rgba(15,23,42,0.4)] backdrop-blur">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-lg font-semibold text-slate-100">Job descriptions</h2>
              <button class="rounded-full bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700" type="button" @click="addJobDescription">Add JD</button>
            </div>

            <div class="mt-4 space-y-4">
              <article v-for="(jd, index) in jobDescriptions" :key="jd.id" class="rounded-2xl border border-slate-700 bg-slate-950/70 p-3">
                <div class="flex items-center gap-2">
                  <input v-model="jd.title" class="min-w-0 flex-1 rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-medium text-slate-100 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100" :placeholder="`Job description ${index + 1}`" />
                  <button class="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-800 disabled:opacity-40" type="button" :disabled="jobDescriptions.length === 1" @click="removeJobDescription(jd.id)">Remove</button>
                </div>
                <textarea v-model="jd.text" class="mt-3 min-h-44 w-full resize-y rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-sm leading-6 text-slate-100 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100" placeholder="Paste the full job description here"></textarea>
              </article>
            </div>
          </section>

          <section class="rounded-[24px] border border-slate-800 bg-slate-900/85 p-4 shadow-[0_18px_45px_-24px_rgba(15,23,42,0.4)] backdrop-blur">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-lg font-semibold text-slate-100">Resumes</h2>
              <button class="rounded-full bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-emerald-700" type="button" @click="addResume">Add Resume</button>
            </div>

            <div class="mt-4 space-y-4">
              <article v-for="group in resumeUploadGroups" :key="group.id" class="rounded-2xl border border-slate-700 bg-slate-950/70 p-3">
                <div class="flex items-center gap-2">
                  <label class="min-w-0 flex-1 rounded-2xl border border-dashed border-slate-700 bg-slate-950 p-3 text-sm transition hover:border-emerald-400">
                    <span class="font-semibold text-slate-100">Choose files</span>
                    <input class="mt-3 block w-full rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-slate-300 file:mr-3 file:rounded-md file:border-0 file:bg-emerald-600 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-white" type="file" accept="application/pdf" multiple @change="handleFiles($event, group.id)" />
                  </label>
                  <button class="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm font-semibold text-slate-200 transition hover:bg-slate-800 disabled:opacity-40" type="button" :disabled="resumeUploadGroups.length === 1" @click="removeResumeGroup(group.id)">Remove</button>
                </div>

                <div v-if="group.files.length" class="mt-3 rounded-xl border border-slate-700 bg-slate-900 p-3 text-sm">
                  <p class="font-semibold text-slate-100">Selected resumes</p>
                  <ul class="mt-2 space-y-1 text-slate-300">
                    <li v-for="file in group.files" :key="`${group.id}-${file.name}`">• {{ file.name }}</li>
                  </ul>
                </div>
              </article>
            </div>

            <p class="mt-3 text-xs leading-5 text-slate-400">Upload one or more PDF resumes and compare them against your selected job descriptions.</p>
          </section>

          <section class="rounded-[24px] border border-slate-800 bg-slate-900/85 p-4 shadow-[0_18px_45px_-24px_rgba(15,23,42,0.4)] backdrop-blur">
            <div class="grid grid-cols-2 gap-4">
              <label class="text-sm font-semibold text-slate-100" for="topK">
                Top matches
                <select id="topK" v-model="topK" class="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 font-normal text-slate-100 outline-none transition focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100">
                  <option v-for="count in [1, 3, 5, 10, 15, 20]" :key="count" :value="count">{{ count }}</option>
                </select>
              </label>
              <label class="flex items-end gap-3 rounded-2xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm font-semibold text-slate-100">
                <input v-model="explain" class="h-4 w-4 accent-emerald-700" type="checkbox" />
                Explain
              </label>
            </div>

            <button class="mt-4 w-full rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-3 font-semibold text-white shadow-lg shadow-emerald-900/20 transition hover:from-emerald-500 hover:to-teal-500 disabled:cursor-not-allowed disabled:from-slate-300 disabled:to-slate-300" type="button" :disabled="!canSubmit" @click="findMatches">
              {{ loading ? 'Matching...' : 'Match JD and resumes' }}
            </button>

            <p v-if="error" class="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">{{ error }}</p>
          </section>
        </aside>

        <section class="min-h-[700px] rounded-[24px] border border-slate-800 bg-slate-900/85 p-5 shadow-[0_18px_45px_-24px_rgba(15,23,42,0.4)] backdrop-blur">
          <div class="flex flex-col gap-3 border-b border-slate-700 pb-4 md:flex-row md:items-end md:justify-between">
            <div>
              <h2 class="text-xl font-semibold text-slate-100">Match results</h2>
              <p class="text-sm text-slate-400">Ranked results appear here with score badges and keyword highlights.</p>
            </div>
            <p class="text-sm font-medium text-slate-400">{{ results.length }} JD groups</p>
          </div>

          <div v-if="loading" class="grid gap-4 py-5">
            <div v-for="item in 4" :key="item" class="h-36 animate-pulse rounded-2xl bg-slate-100"></div>
          </div>

          <div v-else-if="results.length" class="space-y-6 py-5">
            <section v-for="group in results" :key="group.jd_id" class="space-y-3">
              <h3 class="text-lg font-semibold text-slate-900">{{ group.jd_title }}</h3>
              <article v-for="(match, index) in group.matches" :key="`${group.jd_id}-${match.resume_id}`" class="rounded-2xl border border-slate-700 bg-slate-950/85 p-4 shadow-sm">
                <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="rounded-full bg-slate-900 px-2.5 py-1 text-xs font-semibold text-white">#{{ index + 1 }}</span>
                      <span class="rounded-full border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700">{{ match.resume_name }}</span>
                      <span class="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-800">{{ scoreLabel(match.score) }}</span>
                    </div>

                    <div v-if="match.explanation" class="mt-3 rounded-2xl border border-emerald-800 bg-emerald-950/40 p-3">
                      <p class="text-[11px] font-semibold uppercase tracking-wide text-emerald-300">Short explanation</p>
                      <p class="mt-2 text-sm leading-6 text-emerald-100">{{ match.explanation }}</p>
                    </div>
                    <p v-else class="mt-3 rounded-2xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm leading-6 text-slate-400">
                      Explanation disabled or no Groq API key configured.
                    </p>

                    <div v-if="match.matched_keywords.length" class="mt-3 flex flex-wrap gap-2">
                      <span v-for="word in match.matched_keywords" :key="word" class="rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-800">{{ word }}</span>
                    </div>
                  </div>
                  <div class="score-ring grid h-20 w-20 shrink-0 place-items-center rounded-full" :style="{ '--score': scorePercent(match.score) }">
                    <div class="text-center">
                      <p class="text-lg font-bold text-slate-900">{{ scorePercent(match.score) }}</p>
                      <p class="text-[10px] font-semibold uppercase text-slate-500">score</p>
                    </div>
                  </div>
                </div>

                <details class="mt-4 rounded-2xl border border-slate-700 bg-slate-900">
                  <summary class="cursor-pointer px-3 py-2 text-sm font-semibold text-slate-100">Resume preview</summary>
                  <p class="whitespace-pre-line px-3 pb-3 text-sm leading-6 text-slate-300">{{ match.resume_preview }}</p>
                </details>
              </article>
            </section>
          </div>

          <div v-else class="grid min-h-[520px] place-items-center text-center">
            <div class="max-w-sm">
              <div class="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-600 text-lg font-bold text-white">JD</div>
              <h3 class="mt-4 text-lg font-semibold text-slate-900">Add a JD and resume to begin</h3>
              <p class="mt-2 text-sm leading-6 text-slate-600">Paste text, upload resume PDFs, then run the matcher to see ranked candidates and keyword overlap.</p>
            </div>
          </div>
        </section>
      </section>
    </div>
  </main>
</template>
