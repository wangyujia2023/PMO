<template>
  <div class="dashboard-shell">
    <section class="topbar">
      <div>
        <h1>项目进展盘点</h1>
      </div>
      <div class="topbar-actions">
        <button class="ghost-btn" @click="openSettingsModal">系统配置</button>
        <div class="metric-chip">
          <span>项目数</span>
          <strong>{{ matrixRows.length }}</strong>
        </div>
        <div class="metric-chip">
            <span>当周记录</span>
          <strong>{{ currentWeekFilled }}</strong>
        </div>
      </div>
    </section>

    <section class="filter-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'weekly' }"
        @click="activeTab = 'weekly'; loadMatrix()"
      >
        周报明细
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'year' }"
        @click="activeTab = 'year'; loadMatrix()"
      >
        全年矩阵
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'monthly' }"
        @click="activeTab = 'monthly'; loadMonthly()"
      >
        月度盘点
      </button>
      <input
        v-model="filters.keyword"
        class="text-input compact-input"
        type="text"
        placeholder="项目名称模糊查询"
        @keyup.enter="activeTab === 'monthly' ? loadMonthly() : loadMatrix()"
      />
      <div v-if="activeTab !== 'monthly'" class="week-picker">
        <input v-model="filters.weekValue" class="text-input compact-input" type="week" />
        <span class="week-label">{{ selectedWeekLabel }}</span>
      </div>
      <div v-else class="week-picker">
        <input v-model="filters.monthValue" class="text-input compact-input" type="month" />
        <span class="week-label">{{ selectedMonthLabel }}</span>
      </div>
      <button class="ghost-btn" @click="activeTab === 'monthly' ? loadMonthly() : loadMatrix()">查询</button>
      <button class="ghost-btn" @click="resetFilters">重置</button>
      <button class="ghost-btn" @click="copyTemplate">模板样式</button>
      <button class="primary-btn" @click="openImportModal">文本导入</button>
      <button v-if="activeTab !== 'monthly'" class="danger-btn" @click="deleteWeekColumn(getSelectedWeekStart())">删除本周整列</button>
    </section>

    <section v-if="activeTab === 'weekly'" class="board-panel">
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
                  <div class="action-group">
                    <button class="cell-edit-btn" @click="openProjectEditor(row)">编辑</button>
                    <button class="cell-delete-btn" @click="deleteProject(row)">删除</button>
                  </div>
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
                <button v-else class="empty-add-btn" @click="openCellEditor(row, week)">新增</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-else-if="activeTab === 'year'" class="board-panel">
      <div class="toolbar">
        <div class="legend">
          <span><i class="legend-dot green" /> 有内容</span>
          <span><i class="legend-dot muted" /> 无内容</span>
        </div>
        <div class="toolbar-tip">{{ selectedYear }} 全年项目覆盖矩阵</div>
      </div>

      <div class="year-grid-wrapper">
        <table class="year-table">
          <thead>
            <tr>
              <th class="sticky-col project-col">项目名称</th>
              <th v-for="week in yearWeeks" :key="week.week_start" class="year-week-col">
                <div>{{ week.label }}</div>
                <small>{{ week.short_range }}</small>
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in matrixRows" :key="row.project_id">
              <td class="sticky-col project-col">
                <div class="project-name">{{ row.project_name }}</div>
              </td>
              <td
                v-for="week in yearWeeks"
                :key="`${row.project_id}-${week.week_start}`"
                class="year-cell"
                :class="{ filled: hasWeekContent(row, week.week_start) }"
                :title="`${row.project_name} ${week.label} ${hasWeekContent(row, week.week_start) ? '有内容' : '无内容'}`"
                @click="openYearCellViewer(row, week.week_start)"
              >
                {{ hasWeekContent(row, week.week_start) ? "●" : "" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <section v-else class="board-panel monthly-panel">
      <div class="toolbar">
        <div class="legend">
          <span><i class="legend-dot cyan" /> 本月周报汇总</span>
          <span><i class="legend-dot green" /> AI 补充建议</span>
        </div>
        <div class="toolbar-tip">{{ selectedMonthLabel }} 项目月度盘点</div>
      </div>

      <div class="monthly-layout">
        <div class="monthly-list">
          <div
            v-for="row in monthlyRows"
            :key="row.project_id"
            class="monthly-item"
            :class="{ active: selectedMonthlyProject && selectedMonthlyProject.project_id === row.project_id }"
            @click="selectMonthlyProject(row)"
          >
            <div class="monthly-item-head">
              <strong>{{ row.project_name }}</strong>
              <span>{{ row.weeks.length }} 周有进展</span>
            </div>
            <div class="monthly-week-statuses">
              <span
                v-for="week in row.weeks"
                :key="`${row.project_id}-${week.week_start}`"
                class="monthly-week-pill"
              >
                {{ getMonthlyWeekLabel(week.week_start) }}
              </span>
              <span v-if="!row.weeks.length" class="monthly-week-pill muted-pill">暂无内容</span>
            </div>
          </div>
        </div>

        <div class="monthly-detail" v-if="selectedMonthlyProject">
          <div class="monthly-detail-head">
            <div>
              <h3>{{ selectedMonthlyProject.project_name }}</h3>
              <p>{{ selectedMonthLabel }} · 已汇总 {{ selectedMonthlyProject.weeks.length }} 周</p>
            </div>
            <button class="primary-btn" :disabled="monthlyAnalyzing" @click="analyzeMonthlyProject">
              {{ monthlyAnalyzing ? "分析中..." : "生成AI分析" }}
            </button>
          </div>

          <div v-if="monthlyAnalysis" class="analysis-card monthly-analysis-top">
            <div class="analysis-section">
              <div class="cell-tag">本月分析</div>
              <p>{{ monthlyAnalysis.month_summary || "-" }}</p>
            </div>
            <div class="analysis-section">
              <div class="cell-tag next">需要补充完善的动作</div>
              <ul>
                <li v-for="(item, index) in monthlyAnalysis.supplementary_actions" :key="`act-${index}`">{{ item }}</li>
              </ul>
            </div>
            <div class="analysis-section">
              <div class="cell-tag">后续工作计划</div>
              <ul>
                <li v-for="(item, index) in monthlyAnalysis.next_month_plan" :key="`plan-${index}`">{{ item }}</li>
              </ul>
            </div>
            <div class="analysis-section">
              <div class="cell-tag danger-tag">风险与阻塞</div>
              <ul>
                <li v-for="(item, index) in monthlyAnalysis.risks" :key="`risk-${index}`">{{ item }}</li>
              </ul>
            </div>
          </div>

          <div class="monthly-block">
            <div class="cell-tag">本月进展汇总</div>
            <p>{{ selectedMonthlyProject.progress_digest || "-" }}</p>
          </div>

          <div class="monthly-block">
            <div class="cell-tag next">后续计划汇总</div>
            <p>{{ selectedMonthlyProject.plan_digest || "-" }}</p>
          </div>

          <div class="monthly-weeks">
            <div v-for="week in selectedMonthlyProject.weeks" :key="week.week_start" class="monthly-week-card">
              <strong>{{ week.week_start }}</strong>
              <p><b>本周：</b>{{ week.current_progress || "-" }}</p>
              <p><b>下周：</b>{{ week.next_plan || "-" }}</p>
            </div>
          </div>
        </div>

        <div v-else class="monthly-empty">
          请选择一个项目查看本月汇总，并按需生成 AI 分析。
        </div>
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

        <div v-if="importPreview" class="preview-card">
          <div class="result-summary">预览 {{ importPreview.parsed_count }} 条，低置信度项目请确认</div>
          <div v-for="item in importPreview.items" :key="item.index" class="preview-item">
            <div class="preview-head">
              <strong>{{ item.raw_project_name }}</strong>
              <span :class="['status-pill', item.match_status]">
                {{ statusText(item.match_status) }} {{ Number(item.match_confidence).toFixed(2) }}
              </span>
            </div>
            <div class="preview-match">
              <select v-model="item.matched_project_id" class="text-input">
                <option :value="null">创建新项目</option>
                <option v-for="project in projectOptions" :key="project.project_id" :value="project.project_id">
                  {{ project.project_name }}
                </option>
              </select>
              <input
                v-if="!item.matched_project_id"
                v-model="item.matched_project_name"
                class="text-input"
                type="text"
                placeholder="新项目名称"
              />
              <label class="alias-check">
                <input v-model="item.remember_alias" type="checkbox" />
                记住别名
              </label>
            </div>
            <div class="preview-content">
              <p><b>本周</b>{{ item.current_progress || "-" }}</p>
              <p><b>下周</b>{{ item.next_plan || "-" }}</p>
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="ghost-btn" @click="copyTemplate">复制模板</button>
          <button class="ghost-btn" @click="showImportModal = false">取消</button>
          <button class="ghost-btn" :disabled="submitting" @click="previewImport">
            {{ submitting ? "处理中..." : "解析预览" }}
          </button>
          <button class="primary-btn" :disabled="submitting || !importPreview" @click="commitImport">
            确认入库
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

    <div v-if="showCellViewModal" class="modal-mask" @click.self="showCellViewModal = false">
      <div class="modal-card">
        <div class="modal-head">
          <div>
            <h3>周报详情</h3>
            <p>{{ cellViewForm.project_name }} · {{ cellViewForm.week_start }}</p>
          </div>
          <button class="icon-btn" @click="showCellViewModal = false">×</button>
        </div>
        <div class="detail-block">
          <div class="cell-tag">本周</div>
          <p>{{ cellViewForm.current_progress || "-" }}</p>
          <div class="cell-tag next">下周</div>
          <p>{{ cellViewForm.next_plan || "-" }}</p>
        </div>
        <div class="modal-actions">
          <button class="ghost-btn" @click="showCellViewModal = false">关闭</button>
          <button class="primary-btn" @click="editFromViewer">编辑</button>
        </div>
      </div>
    </div>

    <div v-if="showSettingsModal" class="modal-mask" @click.self="showSettingsModal = false">
      <div class="modal-card small-modal">
        <div class="modal-head">
          <div>
            <h3>系统配置</h3>
            <p>配置导入解析与月度盘点使用的大模型</p>
          </div>
          <button class="icon-btn" @click="showSettingsModal = false">×</button>
        </div>
        <div class="settings-layout">
          <div class="settings-list">
            <button
              v-for="item in modelConfigs"
              :key="item.config_id || item.config_name"
              class="model-config-item"
              :class="{ active: settingsForm.config_id === item.config_id }"
              @click="editModelConfig(item)"
            >
              <strong>{{ item.config_name || item.model }}</strong>
              <span>{{ item.provider }} · {{ item.model }}</span>
              <em v-if="item.is_active">当前启用</em>
            </button>
            <button class="ghost-btn full-btn" @click="newModelConfig">新增模型</button>
          </div>

          <div class="modal-form">
            <label class="field-label">配置名称</label>
            <input v-model="settingsForm.config_name" class="text-input" type="text" placeholder="如 Qwen Flash / Gemini Flash" />

            <label class="field-label">模型提供商</label>
            <select v-model="settingsForm.provider" class="text-input">
              <option value="gemini">Gemini</option>
              <option value="qwen">Qwen</option>
              <option value="openai_compatible">OpenAI Compatible</option>
            </select>

            <label class="field-label">模型名称</label>
            <input v-model="settingsForm.model" class="text-input" type="text" placeholder="如 gemini-2.5-flash / qwen3.5-flash" />

            <label class="field-label">API Key</label>
            <input v-model="settingsForm.api_key" class="text-input" type="password" placeholder="请输入 API Key" />

            <label class="field-label">Base URL</label>
            <input
              v-model="settingsForm.base_url"
              class="text-input"
              type="text"
              :placeholder="settingsForm.provider === 'qwen' ? '默认可留空，自动使用 DashScope 兼容地址' : '例如 https://api.openai.com/v1'"
            />

            <label class="alias-check active-check">
              <input v-model="settingsForm.is_active" type="checkbox" />
              设为当前启用模型
            </label>
          </div>
        </div>
        <div class="modal-actions">
          <button class="ghost-btn" @click="showSettingsModal = false">取消</button>
          <button class="primary-btn" @click="saveSettings">保存</button>
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
const activeTab = ref("weekly")
const showImportModal = ref(false)
const showProjectEditModal = ref(false)
const showCellEditModal = ref(false)
const showCellViewModal = ref(false)
const showSettingsModal = ref(false)
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
const importPreview = ref(null)
const projectOptions = ref([])
const modelConfigs = ref([])
const matrixRows = ref([])
const monthlyRows = ref([])
const monthlyAnalysis = ref(null)
const monthlyAnalyzing = ref(false)
const selectedMonthlyProject = ref(null)
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
const cellViewForm = reactive({
  project_id: null,
  project_name: "",
  week_start: "",
  current_progress: "",
  next_plan: "",
})
const settingsForm = reactive({
  config_id: null,
  config_name: "",
  provider: "gemini",
  model: "gemini-2.5-flash",
  api_key: "",
  base_url: "",
  is_active: true,
})
const filters = reactive({
  keyword: "",
  weekValue: getCurrentWeekValue(),
  monthValue: getCurrentMonthValue(),
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

const selectedYear = computed(() => parseWeekValue(filters.weekValue).getFullYear())

const selectedMonthLabel = computed(() => {
  const [year, month] = filters.monthValue.split("-")
  return `${year}年${month}月`
})

const yearWeeks = computed(() => {
  const weeks = []
  const cursor = parseWeekValue(`${selectedYear.value}-W01`)
  while (cursor.getFullYear() <= selectedYear.value || weeks.length < 52) {
    const start = new Date(cursor)
    const end = new Date(start)
    end.setDate(end.getDate() + 6)
    if (start.getFullYear() > selectedYear.value && weeks.length >= 52) break
    weeks.push({
      week_start: formatDate(start),
      label: `W${String(weeks.length + 1).padStart(2, "0")}`,
      short_range: `${formatMonthDay(start)}-${formatMonthDay(end)}`,
    })
    cursor.setDate(cursor.getDate() + 7)
    if (weeks.length >= 53) break
  }
  return weeks
})

async function openImportModal() {
  showImportModal.value = true
  importPreview.value = null
  await loadProjects()
}

async function openSettingsModal() {
  await loadSettings()
  showSettingsModal.value = true
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

function openYearCellViewer(row, week) {
  const cell = getWeekCell(row, week)
  if (!cell || !hasWeekContent(row, week)) return
  cellViewForm.project_id = row.project_id
  cellViewForm.project_name = row.project_name
  cellViewForm.week_start = week
  cellViewForm.current_progress = cell.current_progress || ""
  cellViewForm.next_plan = cell.next_plan || ""
  showCellViewModal.value = true
}

function editFromViewer() {
  cellEditForm.project_id = cellViewForm.project_id
  cellEditForm.project_name = cellViewForm.project_name
  cellEditForm.week_start = cellViewForm.week_start
  cellEditForm.current_progress = cellViewForm.current_progress
  cellEditForm.next_plan = cellViewForm.next_plan
  showCellViewModal.value = false
  showCellEditModal.value = true
}

async function copyTemplate() {
  await navigator.clipboard.writeText(templateText)
  window.alert("模板已复制")
}

function getCurrentWeekValue() {
  return dateToWeekValue(new Date())
}

function getCurrentMonthValue() {
  const date = new Date()
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  return `${year}-${month}`
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

function getMonthlyWeekLabel(weekStart) {
  const start = new Date(`${weekStart}T00:00:00`)
  const end = new Date(start)
  end.setDate(end.getDate() + 6)
  return `${formatMonthDay(start)}~${formatMonthDay(end)}`
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
  filters.monthValue = getCurrentMonthValue()
  if (activeTab.value === "monthly") {
    loadMonthly()
    return
  }
  loadMatrix()
}

async function loadMatrix() {
  const lastWeek = activeTab.value === "year" ? yearWeeks.value[0].week_start : weekColumns.value[weekColumns.value.length - 1]
  const endWeek = activeTab.value === "year"
    ? yearWeeks.value[yearWeeks.value.length - 1].week_start
    : getSelectedWeekStart()
  const params = new URLSearchParams({
    keyword: filters.keyword,
    week_start: lastWeek,
    week_end: endWeek,
  })
  const response = await fetch(`${apiBase}/matrix?${params.toString()}`)
  matrixRows.value = await response.json()
}

async function loadMonthly() {
  const params = new URLSearchParams({
    keyword: filters.keyword,
    month: filters.monthValue,
  })
  const response = await fetch(`${apiBase}/monthly?${params.toString()}`)
  monthlyRows.value = await response.json()
  if (!monthlyRows.value.length) {
    selectedMonthlyProject.value = null
    monthlyAnalysis.value = null
    return
  }
  const currentId = selectedMonthlyProject.value?.project_id
  selectedMonthlyProject.value = monthlyRows.value.find((item) => item.project_id === currentId) || monthlyRows.value[0]
  monthlyAnalysis.value = selectedMonthlyProject.value?.analysis || null
}

async function loadProjects() {
  const response = await fetch(`${apiBase}/projects`)
  projectOptions.value = await response.json()
}

async function loadSettings() {
  const response = await fetch(`${apiBase}/settings`)
  if (!response.ok) {
    window.alert(await response.text() || "加载系统配置失败")
    return
  }
  const data = await response.json()
  modelConfigs.value = data.models || []
  const active = modelConfigs.value.find((item) => item.is_active) || modelConfigs.value[0]
  if (active) {
    editModelConfig(active)
  } else {
    newModelConfig()
  }
}

function hasWeekContent(row, weekStart) {
  const cell = getWeekCell(row, weekStart)
  return Boolean(cell && ((cell.current_progress || "").trim() || (cell.next_plan || "").trim()))
}

function selectMonthlyProject(row) {
  selectedMonthlyProject.value = row
  monthlyAnalysis.value = row.analysis || null
}

function editModelConfig(item) {
  settingsForm.config_id = item.config_id || null
  settingsForm.config_name = item.config_name || item.model || ""
  settingsForm.provider = item.provider || "gemini"
  settingsForm.model = item.model || "gemini-2.5-flash"
  settingsForm.api_key = item.api_key || ""
  settingsForm.base_url = item.base_url || ""
  settingsForm.is_active = Boolean(item.is_active)
}

function newModelConfig() {
  settingsForm.config_id = null
  settingsForm.config_name = ""
  settingsForm.provider = "qwen"
  settingsForm.model = "qwen3.5-flash"
  settingsForm.api_key = ""
  settingsForm.base_url = ""
  settingsForm.is_active = !modelConfigs.value.length
}

function statusText(status) {
  if (status === "auto") return "自动"
  if (status === "confirm") return "待确认"
  return "新项目"
}

async function previewImport() {
  if (!importText.value.trim()) return
  submitting.value = true
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), 30000)
  try {
    const response = await fetch(`${apiBase}/import/preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      body: JSON.stringify({
        week_start: getSelectedWeekStart(),
        raw_text: importText.value,
        auto_create_project: true,
      }),
    })
    if (!response.ok) throw new Error(await response.text())
    importPreview.value = await response.json()
    importPreview.value.items = importPreview.value.items.map((item) => ({
      ...item,
      matched_project_id: item.matched_project_id || null,
      matched_project_name: item.matched_project_name || item.raw_project_name,
      remember_alias: item.match_status !== "new",
    }))
    importResult.value = null
  } catch (error) {
    window.alert(error.name === "AbortError" ? "解析超时，请检查后端日志或稍后重试" : (error.message || "解析失败"))
  } finally {
    window.clearTimeout(timer)
    submitting.value = false
  }
}

async function commitImport() {
  if (!importPreview.value) return
  submitting.value = true
  try {
    const items = importPreview.value.items.map((item) => {
      const selected = projectOptions.value.find((project) => project.project_id === item.matched_project_id)
      return {
        raw_project_name: item.raw_project_name,
        project_id: item.matched_project_id,
        project_name: selected?.project_name || item.matched_project_name || item.raw_project_name,
        current_progress: item.current_progress,
        next_plan: item.next_plan,
        raw_text: item.raw_text,
        remember_alias: item.remember_alias,
      }
    })
    const response = await fetch(`${apiBase}/import/commit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        week_start: getSelectedWeekStart(),
        items,
      }),
    })
    if (!response.ok) throw new Error(await response.text())
    importResult.value = await response.json()
    await loadMatrix()
    if (activeTab.value === "monthly") {
      await loadMonthly()
    }
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
  if (activeTab.value === "monthly") {
    await loadMonthly()
  }
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
  if (activeTab.value === "monthly") {
    await loadMonthly()
  }
}

async function deleteProject(row) {
  const confirmed = window.confirm(`确认删除项目「${row.project_name}」？\n选择确认后，该项目所有周报内容也会一起删除。`)
  if (!confirmed) return
  const response = await fetch(`${apiBase}/project/${row.project_id}`, {
    method: "DELETE",
  })
  if (!response.ok) {
    window.alert("删除项目失败")
    return
  }
  await loadMatrix()
  if (activeTab.value === "monthly") {
    await loadMonthly()
  }
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
  if (activeTab.value === "monthly") {
    await loadMonthly()
  }
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
  if (activeTab.value === "monthly") {
    await loadMonthly()
  }
}

async function analyzeMonthlyProject() {
  if (!selectedMonthlyProject.value) return
  monthlyAnalyzing.value = true
  try {
    const response = await fetch(`${apiBase}/monthly/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: selectedMonthlyProject.value.project_id,
        month: filters.monthValue,
      }),
    })
    if (!response.ok) throw new Error(await response.text())
    monthlyAnalysis.value = await response.json()
    selectedMonthlyProject.value.analysis = monthlyAnalysis.value
  } catch (error) {
    window.alert(error.message || "月度分析失败")
  } finally {
    monthlyAnalyzing.value = false
  }
}

async function saveSettings() {
  const response = await fetch(`${apiBase}/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      llm: {
        config_id: settingsForm.config_id,
        config_name: settingsForm.config_name,
        provider: settingsForm.provider,
        model: settingsForm.model,
        api_key: settingsForm.api_key,
        base_url: settingsForm.base_url,
        is_active: settingsForm.is_active,
      },
    }),
  })
  if (!response.ok) {
    window.alert(await response.text() || "保存系统配置失败")
    return
  }
  const data = await response.json()
  modelConfigs.value = data.models || []
  const saved = modelConfigs.value.find((item) => item.config_name === settingsForm.config_name)
  if (saved) editModelConfig(saved)
  window.alert("系统配置已保存")
}

onMounted(async () => {
  await loadMatrix()
})
</script>

<style scoped>
.dashboard-shell { min-height: 100vh; padding: 8px; font-size:12px; }
.topbar,.filter-bar,.board-panel,.modal-card { background: linear-gradient(180deg, rgba(19, 39, 72, 0.94) 0%, rgba(13, 27, 50, 0.98) 100%); border: 1px solid var(--line); box-shadow: var(--shadow); border-radius: 12px; }
.topbar { display:flex; justify-content:space-between; gap:8px; align-items:center; padding:8px 10px; margin-bottom:6px; }
.eyebrow { margin:0 0 4px; color:#7f97c4; font-size:11px; letter-spacing:.12em; text-transform:uppercase; }
h1,h3,p { margin:0; }
h1 { font-size:18px; line-height:1.1; }
.topbar-actions { display:flex; gap:6px; align-items:center; }
.metric-chip { min-width:76px; padding:5px 8px; border-radius:8px; background:rgba(16,34,63,.92); }
.metric-chip span,.toolbar-tip,.project-sub,.modal-head p,.match-item span,.match-item em,.result-summary { color:var(--muted); font-size:11px; }
.metric-chip strong { display:block; margin-top:2px; font-size:16px; color:#22d4ff; }
.filter-bar { display:flex; gap:6px; align-items:center; padding:7px 8px; margin-bottom:6px; flex-wrap:wrap; }
.week-picker { display:flex; align-items:center; gap:8px; }
.text-input,.import-box { width:100%; border:1px solid rgba(98,132,191,.2); border-radius:7px; padding:6px 9px; background:rgba(10,23,44,.95); color:var(--text); }
.compact-input { width:180px; }
.week-label { color:var(--muted); font-size:11px; white-space:nowrap; }
.text-input:focus,.import-box:focus { outline:1px solid rgba(24,208,255,.45); }
.board-panel { padding:7px; }
.toolbar { display:flex; justify-content:space-between; gap:8px; align-items:center; margin-bottom:7px; }
.legend { display:flex; gap:12px; color:var(--muted); font-size:12px; }
.legend span { display:inline-flex; gap:6px; align-items:center; }
.legend-dot { width:8px; height:8px; border-radius:50%; display:inline-block; }
.legend-dot.cyan { background:var(--cyan); }
.legend-dot.green { background:var(--green); }
.grid-wrapper { overflow:auto; max-height:calc(100vh - 118px); border-radius:9px; border:1px solid var(--line); background:#0c1830; }
.matrix-table { width:100%; min-width:1280px; border-collapse:separate; border-spacing:0; font-size:11px; }
.matrix-table th,.matrix-table td { padding:7px; vertical-align:top; border-right:1px solid var(--line); border-bottom:1px solid var(--line); }
.matrix-table th { position:sticky; top:0; z-index:3; background:#182b4d; color:#b7cef1; text-align:left; }
.sticky-col { position:sticky; left:0; z-index:2; background:#10203c; }
.project-col { width:220px; min-width:220px; }
.week-col { min-width:240px; }
.week-head,.cell-actions,.project-head,.action-group { display:flex; justify-content:space-between; align-items:center; gap:8px; }
.project-name { font-size:12px; font-weight:700; }
.cell { background:#0d1930; }
.cell p { margin:6px 0 8px; color:#d8e3f5; white-space:pre-wrap; line-height:1.5; }
.cell-tag { display:inline-flex; padding:2px 7px; border-radius:999px; color:#7ceaff; background:rgba(24,208,255,.12); font-size:11px; font-weight:700; }
.cell-tag.next { color:#25e9ae; background:rgba(32,214,155,.12); }
.empty { color:#5d739b; }
.empty-add-btn { width:100%; border:1px dashed rgba(98,132,191,.28); border-radius:7px; padding:10px 0; color:#6f85a8; background:rgba(10,23,44,.35); cursor:pointer; }
.empty-add-btn:hover { color:#9fe7ff; border-color:rgba(159,231,255,.45); background:rgba(27,58,102,.45); }
.primary-btn,.ghost-btn,.icon-btn,.danger-btn,.head-delete-btn,.cell-delete-btn,.cell-edit-btn,.tab-btn { border:0; border-radius:7px; padding:6px 10px; cursor:pointer; font-weight:700; font-size:12px; }
.primary-btn { color:#04172d; background:linear-gradient(135deg, #21d9ff 0%, #24d49b 100%); }
.ghost-btn,.icon-btn,.head-delete-btn,.cell-edit-btn,.tab-btn { color:#9fe7ff; background:rgba(27,58,102,.95); }
.tab-btn.active { color:#07182d; background:#24d49b; }
.danger-btn,.cell-delete-btn { color:#ffd6db; background:rgba(133, 31, 53, .9); }
.head-delete-btn,.cell-delete-btn,.cell-edit-btn { padding:3px 6px; font-size:10px; }
.modal-mask { position:fixed; inset:0; background:rgba(2,8,18,.72); display:flex; align-items:center; justify-content:center; padding:24px; z-index:30; }
.modal-card { width:min(860px, 100%); padding:14px; }
.small-modal { width:min(760px, 100%); }
.modal-head,.modal-actions { display:flex; justify-content:space-between; gap:10px; align-items:center; }
.modal-head { margin-bottom:10px; }
.modal-form { display:grid; gap:8px; }
.field-label { color:#bfd0f2; font-size:12px; }
.import-box { min-height:300px; resize:vertical; line-height:1.6; font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.short-box { min-height:160px; font-family:"IBM Plex Sans SC", sans-serif; }
.result-card { margin-top:12px; padding:10px; border-radius:10px; background:rgba(10,23,44,.95); border:1px solid var(--line); max-height:220px; overflow:auto; }
.match-item { display:flex; flex-direction:column; gap:3px; padding:8px 0; border-top:1px solid var(--line); }
.modal-actions { margin-top:12px; }
.preview-card { margin-top:10px; padding:10px; border-radius:10px; background:rgba(10,23,44,.95); border:1px solid var(--line); max-height:320px; overflow:auto; }
.preview-item { padding:8px 0; border-top:1px solid var(--line); }
.preview-head,.preview-match { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.preview-match .text-input { width:220px; }
.preview-content p { margin:4px 0; color:#d8e3f5; white-space:pre-wrap; line-height:1.45; }
.preview-content b { display:inline-flex; margin-right:8px; color:#7ceaff; }
.status-pill { padding:2px 6px; border-radius:999px; font-size:10px; }
.status-pill.auto { color:#24d49b; background:rgba(36,212,155,.16); }
.status-pill.confirm { color:#ffd489; background:rgba(255,181,69,.16); }
.status-pill.new { color:#ffb8c2; background:rgba(133,31,53,.35); }
.alias-check { color:var(--muted); display:inline-flex; align-items:center; gap:4px; white-space:nowrap; }
.settings-layout { display:grid; grid-template-columns:240px minmax(0,1fr); gap:10px; }
.settings-list { display:grid; align-content:start; gap:8px; padding:8px; border:1px solid var(--line); border-radius:9px; background:rgba(10,23,44,.72); max-height:360px; overflow:auto; }
.model-config-item { display:grid; gap:4px; width:100%; text-align:left; border:1px solid transparent; border-radius:8px; padding:9px; cursor:pointer; color:var(--text); background:rgba(16,32,60,.82); }
.model-config-item.active { border-color:rgba(24,208,255,.38); background:rgba(21,42,77,.95); }
.model-config-item span { color:var(--muted); font-size:11px; word-break:break-all; }
.model-config-item em { color:#24d49b; font-size:10px; font-style:normal; }
.full-btn { width:100%; }
.active-check { margin-top:2px; }
.legend-dot.muted { background:#53657f; }
.year-grid-wrapper { overflow:auto; max-height:calc(100vh - 118px); border-radius:9px; border:1px solid var(--line); background:#0c1830; }
.year-table { width:100%; min-width:1500px; border-collapse:separate; border-spacing:0; font-size:11px; }
.year-table th,.year-table td { padding:6px; border-right:1px solid var(--line); border-bottom:1px solid var(--line); text-align:center; }
.year-table th { position:sticky; top:0; z-index:3; background:#182b4d; color:#b7cef1; }
.year-table small { display:block; color:var(--muted); font-size:9px; font-weight:400; }
.year-week-col { width:42px; min-width:42px; }
.year-cell { color:#53657f; background:#0d1930; }
.year-cell.filled { color:#24d49b; background:rgba(36,212,155,.12); cursor:pointer; }
.year-cell.filled:hover { background:rgba(36,212,155,.24); }
.detail-block { padding:10px; border:1px solid var(--line); border-radius:9px; background:rgba(10,23,44,.95); }
.detail-block p { margin:8px 0 12px; white-space:pre-wrap; line-height:1.6; color:#d8e3f5; }
.monthly-panel { padding:7px; }
.monthly-layout { display:grid; grid-template-columns: 320px minmax(0, 1fr); gap:10px; min-height:calc(100vh - 160px); }
.monthly-list,.monthly-detail,.monthly-empty { border:1px solid var(--line); border-radius:10px; background:#0c1830; }
.monthly-list { overflow:auto; max-height:calc(100vh - 170px); padding:8px; }
.monthly-item { padding:10px; border:1px solid transparent; border-radius:10px; background:rgba(16,32,60,.72); cursor:pointer; margin-bottom:8px; }
.monthly-item.active { border-color:rgba(24,208,255,.35); background:rgba(21,42,77,.95); box-shadow: inset 0 0 0 1px rgba(24,208,255,.08); }
.monthly-item-head { display:flex; justify-content:space-between; gap:8px; align-items:center; margin-bottom:6px; }
.monthly-item-head span { color:var(--muted); font-size:11px; }
.monthly-item p,.monthly-block p,.analysis-section p,.monthly-week-card p { margin:0; color:#d8e3f5; white-space:pre-wrap; line-height:1.55; }
.monthly-detail { padding:12px; overflow:auto; max-height:calc(100vh - 170px); }
.monthly-detail-head { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:10px; }
.monthly-block,.analysis-card,.monthly-week-card { padding:10px; border:1px solid var(--line); border-radius:10px; background:rgba(10,23,44,.95); }
.monthly-block { margin-bottom:10px; }
.monthly-week-statuses { display:flex; flex-wrap:wrap; gap:6px; }
.monthly-week-pill { display:inline-flex; align-items:center; padding:3px 8px; border-radius:999px; background:rgba(24,208,255,.10); color:#9fe7ff; border:1px solid rgba(24,208,255,.14); font-size:11px; line-height:1; }
.muted-pill { color:var(--muted); background:rgba(116,147,199,.10); border-color:rgba(116,147,199,.14); }
.monthly-weeks { display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:8px; margin-bottom:10px; }
.monthly-week-card strong { display:block; margin-bottom:6px; color:#b7cef1; }
.analysis-card { display:grid; gap:10px; }
.monthly-analysis-top { margin-bottom:10px; border-color:rgba(32,214,155,.24); }
.analysis-section ul { margin:8px 0 0; padding-left:18px; color:#d8e3f5; }
.analysis-section li { margin-bottom:6px; line-height:1.5; }
.danger-tag { color:#ffb8c2; background:rgba(133,31,53,.35); }
.monthly-empty { display:flex; align-items:center; justify-content:center; color:var(--muted); padding:20px; }
@media (max-width: 980px) {
  .topbar,.filter-bar,.modal-head,.modal-actions { flex-direction:column; align-items:stretch; }
  .topbar-actions { width:100%; flex-wrap:wrap; }
  .compact-input { width:100%; }
  .grid-wrapper { max-height:none; }
  .monthly-layout { grid-template-columns: 1fr; }
  .settings-layout { grid-template-columns: 1fr; }
  .monthly-list,.monthly-detail { max-height:none; }
}
</style>
