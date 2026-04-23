<template>
  <div class="dashboard-shell">
    <section class="topbar">
      <div>
        <p class="eyebrow">PROJECT WEEKLY BOARD</p>
        <h1>项目进展盘点</h1>
      </div>
      <div class="topbar-actions">
        <div class="metric-chip">
          <span>项目数</span>
          <strong>{{ matrixRows.length }}</strong>
        </div>
        <div class="metric-chip">
          <span>当周记录</span>
          <strong>{{ currentWeekFilled }}</strong>
        </div>
        <button class="ghost-btn" @click="copyTemplate">模板样式</button>
        <button class="primary-btn" @click="openImportModal">文本导入</button>
      </div>
    </section>

    <section class="filter-bar">
      <input
        v-model="filters.keyword"
        class="text-input compact-input"
        type="text"
        placeholder="项目名称模糊查询"
        @keyup.enter="loadMatrix"
      />
      <div class="week-picker">
        <input v-model="filters.weekValue" class="text-input compact-input" type="week" />
        <span class="week-label">{{ selectedWeekLabel }}</span>
      </div>
      <button class="ghost-btn" @click="loadMatrix">查询</button>
      <button class="ghost-btn" @click="resetFilters">重置</button>
      <button class="danger-btn" @click="deleteWeekColumn(getSelectedWeekStart())">删除本周整列</button>
    </section>

    <section class="board-panel">
      <div class="toolbar">
        <div class="legend">
          <span><i class="legend-dot cyan" /> 本周进展</span>
          <span><i class="legend-dot green" /> 下周计划</span>
        </div>
        <div class="toolbar-tip">支持 JSON 模板导入，支持删除整周和单个单元格</div>
      </div>

      <div class="grid-wrapper">
        <table class="matrix-table">
          <thead>
            <tr>
              <th class="sticky-col project-col">项目名称</th>
              <th v-for="week in weekColumns" :key="week" class="week-col">
                <div class="week-head">
                  <span>{{ week }}</span>
                  <button
                    class="head-delete-btn"
                    @click="deleteWeekColumn(week)"
                  >
                    删列
                  </button>
                </div>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in matrixRows" :key="row.project_id">
              <td class="sticky-col project-col">
                <div class="project-head">
                  <div class="project-name">{{ row.project_name }}</div>
                  <button class="cell-edit-btn" @click="openProjectEditor(row)">编辑</button>
                </div>
                <div class="project-sub">P{{ String(row.project_id).padStart(3, "0") }}</div>
              </td>
              <td v-for="week in weekColumns" :key="`${row.project_id}-${week}`" class="cell">
                <template v-if="getWeekCell(row, week)">
                  <div class="cell-actions">
                    <div class="cell-tag">本周</div>
                    <div class="action-group">
                      <button class="cell-edit-btn" @click="openCellEditor(row, week)">编辑</button>
                      <button class="cell-delete-btn" @click="deleteCell(row.project_id, week)">删除</button>
                    </div>
                  </div>
                  <p>{{ getWeekCell(row, week).current_progress || "-" }}</p>
                  <div class="cell-tag next">下周</div>
                  <p>{{ getWeekCell(row, week).next_plan || "-" }}</p>
                </template>
                <span v-else class="empty">-</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="showImportModal" class="modal-mask" @click.self="showImportModal = false">
      <div class="modal-card">
        <div class="modal-head">
          <div>
            <h3>JSON 导入</h3>
            <p>按模板 JSON 粘贴后直接入库</p>
          </div>
          <button class="icon-btn" @click="showImportModal = false">×</button>
        </div>

        <div class="modal-form">
          <label class="field-label">导入周</label>
          <div class="week-picker modal-week-picker">
            <input v-model="filters.weekValue" class="text-input compact-input" type="week" />
            <span class="week-label">{{ selectedWeekLabel }}</span>
          </div>

          <label class="field-label">导入 JSON</label>
          <textarea
            v-model="importText"
            class="import-box"
            :placeholder="templateText"
          />

        </div>

        <div v-if="importResult" class="result-card">
          <div class="result-summary">已写入 {{ importResult.saved_count }} / {{ importResult.parsed_count }} 条</div>
          <div v-for="item in importResult.items" :key="item.index" class="match-item">
            <strong>{{ item.project_name }}</strong>
            <span>{{ item.matched_project_name || "未匹配" }}</span>
            <em v-if="item.match_score">匹配度 {{ Number(item.match_score).toFixed(2) }}</em>
          </div>
        </div>

        <div class="modal-actions">
          <button class="ghost-btn" @click="copyTemplate">复制模板</button>
          <button class="ghost-btn" @click="showImportModal = false">取消</button>
          <button class="primary-btn" :disabled="submitting" @click="submitImport">
            {{ submitting ? "导入中..." : "确认导入" }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showProjectEditModal" class="modal-mask" @click.self="showProjectEditModal = false">
      <div class="modal-card small-modal">
        <div class="modal-head">
          <div>
            <h3>编辑项目名称</h3>
            <p>修改列表里的项目名称</p>
          </div>
          <button class="icon-btn" @click="showProjectEditModal = false">×</button>
        </div>
        <div class="modal-form">
          <label class="field-label">项目名称</label>
          <input v-model="projectEditForm.project_name" class="text-input" type="text" />
        </div>
        <div class="modal-actions">
          <button class="ghost-btn" @click="showProjectEditModal = false">取消</button>
          <button class="primary-btn" @click="saveProjectEdit">保存</button>
        </div>
      </div>
    </div>

    <div v-if="showCellEditModal" class="modal-mask" @click.self="showCellEditModal = false">
      <div class="modal-card">
        <div class="modal-head">
          <div>
            <h3>编辑单元格</h3>
            <p>{{ cellEditForm.project_name }} · {{ cellEditForm.week_start }}</p>
          </div>
          <button class="icon-btn" @click="showCellEditModal = false">×</button>
        </div>
        <div class="modal-form">
          <label class="field-label">本周进展</label>
          <textarea v-model="cellEditForm.current_progress" class="import-box short-box" />
          <label class="field-label">下周计划</label>
          <textarea v-model="cellEditForm.next_plan" class="import-box short-box" />
        </div>
        <div class="modal-actions">
          <button class="ghost-btn" @click="showCellEditModal = false">取消</button>
          <button class="primary-btn" @click="saveCellEdit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue"

const apiHost = `${window.location.protocol}//${window.location.hostname}:28823`
const apiBase = `${apiHost}/api`
const submitting = ref(false)
const showImportModal = ref(false)
const showProjectEditModal = ref(false)
const showCellEditModal = ref(false)
const templateText = `[
  {
    "project_name": "项目名称",
    "this_week_progress": [
      "本周完成的具体事项1",
      "事项2",
      "发现的问题/卡点"
    ],
    "next_week_plan": [
      "下周待办1",
      "下周待办2"
    ],
    "people_tagged": ["提及的同事名"]
  }
]`
const importText = ref(templateText)
const importResult = ref(null)
const matrixRows = ref([])
const projectEditForm = reactive({
  project_id: null,
  project_name: "",
})
const cellEditForm = reactive({
  project_id: null,
  project_name: "",
  week_start: "",
  current_progress: "",
  next_plan: "",
})
const filters = reactive({
  keyword: "",
  weekValue: getCurrentWeekValue(),
})

const weekColumns = computed(() => {
  const start = parseWeekValue(filters.weekValue)
  return Array.from({ length: 8 }).map((_, index) => {
    const date = new Date(start)
    date.setDate(date.getDate() - index * 7)
    return formatDate(date)
  })
})

const currentWeekFilled = computed(() => {
  const currentWeek = getSelectedWeekStart()
  return matrixRows.value.filter((item) => item.weeks.some((week) => week.week_start === currentWeek)).length
})

const selectedWeekLabel = computed(() => {
  const start = parseWeekValue(filters.weekValue)
  const end = new Date(start)
  end.setDate(end.getDate() + 6)
  return `${getWeekLabel(start)} (${formatMonthDay(start)}-${formatMonthDay(end)})`
})

function openImportModal() {
  showImportModal.value = true
}

function openProjectEditor(row) {
  projectEditForm.project_id = row.project_id
  projectEditForm.project_name = row.project_name
  showProjectEditModal.value = true
}

function openCellEditor(row, week) {
  const cell = getWeekCell(row, week)
  cellEditForm.project_id = row.project_id
  cellEditForm.project_name = row.project_name
  cellEditForm.week_start = week
  cellEditForm.current_progress = cell?.current_progress || ""
  cellEditForm.next_plan = cell?.next_plan || ""
  showCellEditModal.value = true
}

async function copyTemplate() {
  await navigator.clipboard.writeText(templateText)
  window.alert("模板已复制")
}

function getCurrentWeekValue() {
  return dateToWeekValue(new Date())
}

function dateToWeekValue(date) {
  const target = new Date(date)
  const day = target.getDay() || 7
  target.setDate(target.getDate() + 4 - day)
  const yearStart = new Date(target.getFullYear(), 0, 1)
  const weekNo = Math.ceil((((target - yearStart) / 86400000) + 1) / 7)
  return `${target.getFullYear()}-W${String(weekNo).padStart(2, "0")}`
}

function parseWeekValue(weekValue) {
  const [yearText, weekText] = weekValue.split("-W")
  const year = Number(yearText)
  const week = Number(weekText)
  const jan4 = new Date(year, 0, 4)
  const day = jan4.getDay() || 7
  const monday = new Date(jan4)
  monday.setDate(jan4.getDate() - day + 1 + (week - 1) * 7)
  monday.setHours(0, 0, 0, 0)
  return monday
}

function formatDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

function formatMonthDay(date) {
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${month}-${day}`
}

function getWeekLabel(date) {
  return `${dateToWeekValue(date).replace("-W", " 第")}周`
}

function getSelectedWeekStart() {
  return formatDate(parseWeekValue(filters.weekValue))
}

function getWeekCell(row, week) {
  return row.weeks.find((item) => item.week_start === week)
}

function resetFilters() {
  filters.keyword = ""
  filters.weekValue = getCurrentWeekValue()
  loadMatrix()
}

async function loadMatrix() {
  const lastWeek = weekColumns.value[weekColumns.value.length - 1]
  const params = new URLSearchParams({
    keyword: filters.keyword,
    week_start: lastWeek,
    week_end: getSelectedWeekStart(),
  })
  const response = await fetch(`${apiBase}/matrix?${params.toString()}`)
  matrixRows.value = await response.json()
}

async function submitImport() {
  if (!importText.value.trim()) return
  submitting.value = true
  try {
    const response = await fetch(`${apiBase}/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        week_start: getSelectedWeekStart(),
        raw_text: importText.value,
        auto_create_project: true,
      }),
    })
    if (!response.ok) throw new Error(await response.text())
    importResult.value = await response.json()
    await loadMatrix()
    showImportModal.value = false
  } catch (error) {
    window.alert(error.message || "导入失败")
  } finally {
    submitting.value = false
  }
}

async function deleteWeekColumn(week) {
  if (!window.confirm(`确认删除 ${week} 整列数据？`)) return
  const response = await fetch(`${apiBase}/week`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ week_start: week }),
  })
  if (!response.ok) {
    window.alert("删除失败")
    return
  }
  await loadMatrix()
}

async function deleteCell(projectId, week) {
  if (!window.confirm(`确认删除 ${week} 这个单元格？`)) return
  const response = await fetch(`${apiBase}/cell`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project_id: projectId, week_start: week }),
  })
  if (!response.ok) {
    window.alert("删除失败")
    return
  }
  await loadMatrix()
}

async function saveProjectEdit() {
  const response = await fetch(`${apiBase}/project`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: projectEditForm.project_id,
      project_name: projectEditForm.project_name,
    }),
  })
  if (!response.ok) {
    window.alert("保存失败")
    return
  }
  showProjectEditModal.value = false
  await loadMatrix()
}

async function saveCellEdit() {
  const response = await fetch(`${apiBase}/cell`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project_id: cellEditForm.project_id,
      week_start: cellEditForm.week_start,
      current_progress: cellEditForm.current_progress,
      next_plan: cellEditForm.next_plan,
    }),
  })
  if (!response.ok) {
    window.alert("保存失败")
    return
  }
  showCellEditModal.value = false
  await loadMatrix()
}

onMounted(loadMatrix)
</script>

<style scoped>
.dashboard-shell { min-height: 100vh; padding: 14px; }
.topbar,.filter-bar,.board-panel,.modal-card { background: linear-gradient(180deg, rgba(19, 39, 72, 0.94) 0%, rgba(13, 27, 50, 0.98) 100%); border: 1px solid var(--line); box-shadow: var(--shadow); border-radius: 12px; }
.topbar { display:flex; justify-content:space-between; gap:12px; align-items:center; padding:14px 16px; margin-bottom:10px; }
.eyebrow { margin:0 0 4px; color:#7f97c4; font-size:11px; letter-spacing:.12em; text-transform:uppercase; }
h1,h3,p { margin:0; }
h1 { font-size:24px; line-height:1.1; }
.topbar-actions { display:flex; gap:10px; align-items:center; }
.metric-chip { min-width:92px; padding:8px 12px; border-radius:10px; background:rgba(16,34,63,.92); }
.metric-chip span,.toolbar-tip,.project-sub,.modal-head p,.match-item span,.match-item em,.result-summary { color:var(--muted); font-size:12px; }
.metric-chip strong { display:block; margin-top:4px; font-size:22px; color:#22d4ff; }
.filter-bar { display:flex; gap:8px; align-items:center; padding:10px 12px; margin-bottom:10px; }
.week-picker { display:flex; align-items:center; gap:8px; }
.text-input,.import-box { width:100%; border:1px solid rgba(98,132,191,.2); border-radius:8px; padding:9px 12px; background:rgba(10,23,44,.95); color:var(--text); }
.compact-input { width:220px; }
.week-label { color:var(--muted); font-size:12px; white-space:nowrap; }
.text-input:focus,.import-box:focus { outline:1px solid rgba(24,208,255,.45); }
.board-panel { padding:10px; }
.toolbar { display:flex; justify-content:space-between; gap:10px; align-items:center; margin-bottom:10px; }
.legend { display:flex; gap:12px; color:var(--muted); font-size:12px; }
.legend span { display:inline-flex; gap:6px; align-items:center; }
.legend-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
.legend-dot.cyan { background:var(--cyan); }
.legend-dot.green { background:var(--green); }
.grid-wrapper { overflow:auto; max-height:calc(100vh - 170px); border-radius:10px; border:1px solid var(--line); background:#0c1830; }
.matrix-table { width:100%; min-width:1380px; border-collapse:separate; border-spacing:0; font-size:12px; }
.matrix-table th,.matrix-table td { padding:10px; vertical-align:top; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }
.matrix-table th { position:sticky; top:0; z-index:3; background:#182b4d; color:#b7cef1; text-align:left; }
.sticky-col { position:sticky; left:0; z-index:2; background:#10203c; }
.project-col { width:210px; min-width:210px; }
.week-col { min-width:260px; }
.week-head,.cell-actions,.project-head,.action-group { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.project-name { font-size:13px; font-weight:700; }
.cell { background:#0d1930; }
.cell p { margin:6px 0 8px; color:#d8e3f5; white-space:pre-wrap; line-height:1.5; }
.cell-tag { display:inline-flex; padding:2px 7px; border-radius:999px; color:#7ceaff; background:rgba(24,208,255,.12); font-size:11px; font-weight:700; }
.cell-tag.next { color:#25e9ae; background:rgba(32,214,155,.12); }
.empty { color:#5d739b; }
.primary-btn,.ghost-btn,.icon-btn,.danger-btn,.head-delete-btn,.cell-delete-btn,.cell-edit-btn { border:0; border-radius:8px; padding:9px 14px; cursor:pointer; font-weight:700; }
.primary-btn { color:#04172d; background:linear-gradient(135deg, #21d9ff 0%, #24d49b 100%); }
.ghost-btn,.icon-btn,.head-delete-btn,.cell-edit-btn { color:#9fe7ff; background:rgba(27,58,102,.95); }
.danger-btn,.cell-delete-btn { color:#ffd6db; background:rgba(133, 31, 53, .9); }
.head-delete-btn,.cell-delete-btn,.cell-edit-btn { padding:4px 8px; font-size:11px; }
.modal-mask { position:fixed; inset:0; background:rgba(2,8,18,.72); display:flex; align-items:center; justify-content:center; padding:24px; z-index:30; }
.modal-card { width:min(860px, 100%); padding:14px; }
.small-modal { width:min(520px, 100%); }
.modal-head,.modal-actions { display:flex; justify-content:space-between; gap:10px; align-items:center; }
.modal-head { margin-bottom:10px; }
.modal-form { display:grid; gap:8px; }
.field-label { color:#bfd0f2; font-size:12px; }
.import-box { min-height:300px; resize:vertical; line-height:1.6; font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.short-box { min-height:160px; font-family:"IBM Plex Sans SC", sans-serif; }
.result-card { margin-top:12px; padding:10px; border-radius:10px; background:rgba(10,23,44,.95); border:1px solid var(--line); max-height:220px; overflow:auto; }
.match-item { display:flex; flex-direction:column; gap:3px; padding:8px 0; border-top:1px solid var(--line); }
.modal-actions { margin-top:12px; }
@media (max-width: 980px) {
  .topbar,.filter-bar,.modal-head,.modal-actions { flex-direction:column; align-items:stretch; }
  .topbar-actions { width:100%; flex-wrap:wrap; }
  .compact-input { width:100%; }
  .grid-wrapper { max-height:none; }
}
</style>
