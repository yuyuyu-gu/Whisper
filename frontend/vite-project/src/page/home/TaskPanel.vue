<template>
  <div class="admin-container">
    <!-- 顶部导航栏 -->
    <header class="admin-header panel">
      <div class="header-content">
        <h1 class="header-title">🎯 任务管理后台</h1>
        <div class="header-actions">
          <button class="btn refresh-btn" @click="fetchAllTasks">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            刷新列表
          </button>
          <button
            class="btn danger-btn"
            @click="batchDeleteTasks"
            :disabled="selectedTasks.length === 0"
          >
            批量删除
          </button>
        </div>
      </div>
    </header>

    <!-- 筛选工具栏 -->
    <section class="filter-toolbar panel">
      <div class="filter-group">
        <label class="filter-label">任务类型：</label>
        <select v-model="filterParams.taskType" class="form-control filter-select" @change="fetchAllTasks">
          <option value="">全部类型</option>
          <option value="TRANSCRIPTION">字幕生成</option>
          <option value="VAD">VAD检测</option>
          <option value="BGM_SEPARATION">BGM分离</option>
        </select>
      </div>

      <div class="filter-group">
        <label class="filter-label">任务状态：</label>
        <select v-model="filterParams.status" class="form-control filter-select" @change="fetchAllTasks">
          <option value="">全部状态</option>
          <option value="QUEUED">排队中</option>
          <option value="IN_PROGRESS">处理中</option>
          <option value="COMPLETED">已完成</option>
          <option value="FAILED">失败</option>
        </select>
      </div>

      <div class="filter-group search-group">
        <input
          type="text"
          v-model="filterParams.keyword"
          class="form-control search-input"
          placeholder="输入任务ID/文件名搜索"
          @keyup.enter="fetchAllTasks"
        />
        <button class="btn search-btn" @click="fetchAllTasks">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </button>
      </div>
    </section>

    <!-- 任务列表区域 -->
    <section class="task-list-container panel">
      <div class="list-header">
        <div class="list-select-all">
          <input
            type="checkbox"
            id="select-all"
            v-model="selectAll"
            @change="toggleSelectAll"
          />
          <label for="select-all">全选</label>
        </div>
        <div class="list-stats">
          共 <span class="stat-num">{{ totalTasks }}</span> 个任务 |
          已选 <span class="stat-num">{{ selectedTasks.length }}</span> 个
        </div>
      </div>

      <!-- 空状态 -->
      <div class="empty-state" v-if="tasks.length === 0 && !loading">
        <svg viewBox="0 0 24 24" width="64" height="64" fill="#e2e8f0" stroke="#94a3b8">
          <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2" />
          <path d="M12 12h.01" />
          <path d="M12 16h.01" />
          <path d="M12 8h.01" />
        </svg>
        <p class="empty-text">暂无任务数据</p>
        <button class="btn primary-btn" @click="fetchAllTasks">刷新试试</button>
      </div>

      <!-- 加载状态 -->
      <div class="loading-state" v-if="loading">
        <div class="spinner"></div>
        <p>加载任务数据中...</p>
      </div>

      <!-- 任务列表 -->
      <table class="task-table" v-if="tasks.length > 0 && !loading">
        <thead>
          <tr>
            <th width="50">
              <input type="checkbox" id="header-select" v-model="selectAll" @change="toggleSelectAll" />
            </th>
            <th width="180">任务ID</th>
            <th width="120">任务类型</th>
            <th width="100">状态</th>
            <th>文件名称</th>
            <th width="180">创建时间</th>
            <th width="180">完成时间</th>
            <th width="150">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in tasks" :key="task.identifier" :class="getStatusClass(task.status)">
            <td>
              <input
                type="checkbox"
                :value="task.identifier"
                v-model="selectedTasks"
              />
            </td>
            <td class="task-id-cell">
              <span class="task-id">{{ task.identifier }}</span>
            </td>
            <td>
              <span class="type-tag" :class="getTypeClass(task.task_type)">
                {{ getTaskTypeName(task.task_type) }}
              </span>
            </td>
            <td>
              <span class="status-tag" :class="getStatusTagClass(task.status)">
                {{ getStatusName(task.status) }}
              </span>
            </td>
            <td class="filename-cell">
              <span class="filename" :title="task.file_name">{{ task.file_name }}</span>
            </td>
            <td>{{ formatDateTime(task.created_at) }}</td>
            <td>{{ task.completed_at ? formatDateTime(task.completed_at) : '-' }}</td>
            <td class="action-cell">
              <button
                class="btn icon-btn detail-btn"
                @click="viewTaskDetail(task)"
                title="查看详情"
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor">
                  <path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z" />
                  <path d="M12 16v-4M12 8h.01" />
                </svg>
              </button>

              <button
                v-if="task.task_type === 'BGM_SEPARATION' && task.status === 'COMPLETED'"
                class="btn icon-btn download-btn"
                @click="downloadBgmFile(task.identifier)"
                title="下载BGM分离文件"
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />
                </svg>
              </button>

              <button
                class="btn icon-btn delete-btn"
                @click="deleteSingleTask(task.identifier)"
                title="删除任务"
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor">
                  <path d="M3 6h18M5 6v14c0 1.1.9 2 2 2h10a2 2 0 0 0 2-2V6m-1 0V4a2 2 0 0 0-2-2H8a2 2 0 0 0-2 2v2M9 6h6" />
                </svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <!-- 分页控件 -->
    <section class="pagination-container" v-if="totalPages > 1 && !loading">
      <div class="pagination">
        <button
          class="page-btn"
          :disabled="currentPage === 1"
          @click="changePage(currentPage - 1)"
        >
          上一页
        </button>

        <button
          v-for="page in visiblePages"
          :key="page"
          class="page-btn"
          :class="{ active: page === currentPage }"
          @click="changePage(page)"
        >
          {{ page }}
        </button>

        <button
          class="page-btn"
          :disabled="currentPage === totalPages"
          @click="changePage(currentPage + 1)"
        >
          下一页
        </button>

        <div class="page-info">
          第 {{ currentPage }} / {{ totalPages }} 页，共 {{ totalTasks }} 条
        </div>
      </div>
    </section>

    <!-- 任务详情弹窗（添加panel类） -->
    <div class="modal-overlay" v-if="showDetailModal" @click="closeDetailModal">
      <div class="modal-content panel" @click.stop>
        <div class="modal-header">
          <h3 class="modal-title">任务详情</h3>
          <button class="modal-close" @click="closeDetailModal">×</button>
        </div>

        <div class="modal-body" v-if="currentTaskDetail">
          <div class="detail-grid">
            <div class="detail-item">
              <label>任务ID：</label>
              <span>{{ currentTaskDetail.identifier }}</span>
            </div>
            <div class="detail-item">
              <label>任务类型：</label>
              <span>{{ getTaskTypeName(currentTaskDetail.task_type) }}</span>
            </div>
            <div class="detail-item">
              <label>任务状态：</label>
              <span class="status-tag" :class="getStatusTagClass(currentTaskDetail.status)">
                {{ getStatusName(currentTaskDetail.status) }}
              </span>
            </div>
            <div class="detail-item">
              <label>文件名称：</label>
              <span>{{ currentTaskDetail.file_name }}</span>
            </div>
            <div class="detail-item">
              <label>文件大小：</label>
              <span>{{ formatFileSize(currentTaskDetail.file_size) }}</span>
            </div>
            <div class="detail-item">
              <label>创建时间：</label>
              <span>{{ formatDateTime(currentTaskDetail.created_at) }}</span>
            </div>
            <div class="detail-item">
              <label>开始时间：</label>
              <span>{{ currentTaskDetail.started_at ? formatDateTime(currentTaskDetail.started_at) : '-' }}</span>
            </div>
            <div class="detail-item">
              <label>完成时间：</label>
              <span>{{ currentTaskDetail.completed_at ? formatDateTime(currentTaskDetail.completed_at) : '-' }}</span>
            </div>

            <!-- BGM分离特有字段 -->
            <div
              v-if="currentTaskDetail.task_type === 'BGM_SEPARATION' && currentTaskDetail.result"
              class="detail-item"
            >
              <label>Instrumental哈希：</label>
              <span>{{ currentTaskDetail.result.instrumental_hash || '-' }}</span>
            </div>
            <div
              v-if="currentTaskDetail.task_type === 'BGM_SEPARATION' && currentTaskDetail.result"
              class="detail-item"
            >
              <label>Vocal哈希：</label>
              <span>{{ currentTaskDetail.result.vocal_hash || '-' }}</span>
            </div>

            <!-- 失败原因 -->
            <div v-if="currentTaskDetail.error" class="detail-item error-item">
              <label>失败原因：</label>
              <span class="error-text">{{ currentTaskDetail.error }}</span>
            </div>

            <!-- 任务参数 -->
            <div class="detail-item full-width">
              <label>任务参数：</label>
              <pre class="params-json">{{ formatJson(currentTaskDetail.params) }}</pre>
            </div>

            <!-- 任务结果 -->
            <div v-if="currentTaskDetail.result && !currentTaskDetail.error" class="detail-item full-width">
              <label>任务结果：</label>
              <pre class="result-json">{{ formatJson(currentTaskDetail.result) }}</pre>
            </div>
          </div>
        </div>

        <div v-else class="loading-detail">
          <div class="spinner small"></div>
          <p>加载详情中...</p>
        </div>

        <div class="modal-footer">
          <button
            v-if="currentTaskDetail?.task_type === 'BGM_SEPARATION' && currentTaskDetail?.status === 'COMPLETED'"
            class="btn primary-btn"
            @click="downloadBgmFile(currentTaskDetail.identifier)"
          >
            下载BGM分离文件
          </button>
          <button class="btn default-btn" @click="closeDetailModal">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import {
  getTaskStatus,
  getTaskStatuses,
  deleteTask,
  downloadBgmZip
} from '../../api/task';

export default {
  name: 'TaskManagement',
  data() {
    return {
      // 筛选参数
      filterParams: {
        taskType: '',
        status: '',
        keyword: ''
      },
      // 分页参数
      currentPage: 1,
      pageSize: 10,
      totalPages: 1,
      totalTasks: 0,
      visiblePages: [],
      // 任务数据
      tasks: [],
      loading: false,
      // 选中状态
      selectAll: false,
      selectedTasks: [],
      // 详情弹窗
      showDetailModal: false,
      currentTaskDetail: null,
      // 错误提示
      errorMessage: ''
    };
  },
  mounted() {
    this.fetchAllTasks();
  },
  watch: {
    totalPages() {
      this.updateVisiblePages();
    },
    currentPage() {
      this.updateVisiblePages();
    }
  },
  methods: {
    // 获取任务列表
    async fetchAllTasks() {
      try {
        this.loading = true;
        // 构建查询参数
        const queryParams = {
          page: this.currentPage,
          page_size: this.pageSize,
          task_type: this.filterParams.taskType,
          status: this.filterParams.status,
          keyword: this.filterParams.keyword
        };

        // 调用批量获取任务列表接口
        const response = await getTaskStatuses(queryParams);

        this.tasks = response.items || [];
        this.totalTasks = response.total || 0;
        this.totalPages = Math.ceil(this.totalTasks / this.pageSize);
        this.updateVisiblePages();

        // 重置选中状态
        this.selectAll = false;
        this.selectedTasks = [];
      } catch (error) {
        console.error('获取任务列表失败：', error);
        this.errorMessage = `获取任务失败：${error.message}`;
        this.$message?.error(this.errorMessage);
      } finally {
        this.loading = false;
      }
    },

    // 更新可见页码
    updateVisiblePages() {
      const total = this.totalPages;
      const current = this.currentPage;
      const pages = [];

      // 显示当前页前后2页
      const start = Math.max(1, current - 2);
      const end = Math.min(total, current + 2);

      for (let i = start; i <= end; i++) {
        pages.push(i);
      }

      this.visiblePages = pages;
    },

    // 切换页码
    changePage(page) {
      if (page < 1 || page > this.totalPages) return;
      this.currentPage = page;
      this.fetchAllTasks();
    },

    // 全选/取消全选
    toggleSelectAll() {
      if (this.selectAll) {
        this.selectedTasks = this.tasks.map(task => task.identifier);
      } else {
        this.selectedTasks = [];
      }
    },

    // 查看任务详情
    async viewTaskDetail(task) {
      try {
        this.showDetailModal = true;
        this.currentTaskDetail = null;

        // 获取任务详情
        const detail = await getTaskStatus(task.identifier);
        this.currentTaskDetail = detail;
      } catch (error) {
        console.error('获取任务详情失败：', error);
        this.$message?.error(`获取详情失败：${error.message}`);
        this.closeDetailModal();
      }
    },

    // 关闭详情弹窗
    closeDetailModal() {
      this.showDetailModal = false;
      this.currentTaskDetail = null;
    },

    // 下载BGM分离文件
    async downloadBgmFile(identifier) {
      try {
        this.loading = true;
        const blob = await downloadBgmZip(identifier);

        // 创建下载链接
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${identifier}_bgm_separation.zip`;
        document.body.appendChild(a);
        a.click();

        // 清理
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);

        this.$message?.success('下载开始，请等待');
      } catch (error) {
        console.error('下载BGM文件失败：', error);
        this.$message?.error(`下载失败：${error.message}`);
      } finally {
        this.loading = false;
      }
    },

    // 删除单个任务
    async deleteSingleTask(identifier) {
      try {
        if (!confirm('确定要删除此任务吗？删除后将无法恢复！')) return;

        await deleteTask(identifier);
        this.$message?.success('任务删除成功');
        this.fetchAllTasks();
      } catch (error) {
        console.error('删除任务失败：', error);
        this.$message?.error(`删除失败：${error.message}`);
      }
    },

    // 批量删除任务
    async batchDeleteTasks() {
      try {
        if (this.selectedTasks.length === 0) return;
        if (!confirm(`确定要删除选中的 ${this.selectedTasks.length} 个任务吗？删除后将无法恢复！`)) return;

        // 批量删除
        const deletePromises = this.selectedTasks.map(id => deleteTask(id));
        await Promise.all(deletePromises);

        this.$message?.success(`成功删除 ${this.selectedTasks.length} 个任务`);
        this.fetchAllTasks();
      } catch (error) {
        console.error('批量删除任务失败：', error);
        this.$message?.error(`批量删除失败：${error.message}`);
      }
    },

    // 格式化日期时间
    formatDateTime(dateString) {
      if (!dateString) return '-';
      const date = new Date(dateString);
      return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
    },

    // 格式化文件大小
    formatFileSize(bytes) {
      if (!bytes) return '-';
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
      if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
      return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
    },

    // 格式化JSON显示
    formatJson(json) {
      if (!json) return '{}';
      return JSON.stringify(json, null, 2);
    },

    // 获取任务类型名称
    getTaskTypeName(type) {
      const typeMap = {
        'TRANSCRIPTION': '字幕生成',
        'VAD': 'VAD检测',
        'BGM_SEPARATION': 'BGM分离'
      };
      return typeMap[type] || type;
    },

    // 获取状态名称
    getStatusName(status) {
      const statusMap = {
        'QUEUED': '排队中',
        'IN_PROGRESS': '处理中',
        'COMPLETED': '已完成',
        'FAILED': '失败'
      };
      return statusMap[status] || status;
    },

    // 获取状态行样式类
    getStatusClass(status) {
      const classMap = {
        'QUEUED': 'status-queued',
        'IN_PROGRESS': 'status-processing',
        'COMPLETED': 'status-completed',
        'FAILED': 'status-failed'
      };
      return classMap[status] || '';
    },

    // 获取状态标签样式类
    getStatusTagClass(status) {
      const classMap = {
        'QUEUED': 'tag-queued',
        'IN_PROGRESS': 'tag-processing',
        'COMPLETED': 'tag-completed',
        'FAILED': 'tag-failed'
      };
      return classMap[status] || '';
    },

    // 获取任务类型样式类
    getTypeClass(type) {
      const classMap = {
        'TRANSCRIPTION': 'type-transcription',
        'VAD': 'type-vad',
        'BGM_SEPARATION': 'type-bgm'
      };
      return classMap[type] || '';
    }
  }
};
</script>

<style scoped>
.panel {
  background: #ffffff;
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem 1.5rem;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
  animation: panel-fade-in 480ms ease;
  margin-bottom: 1.25rem; /* 统一面板间距 */
}

.panel h2, .panel h3 {
  margin-top: 0;
}

@keyframes panel-fade-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.admin-container {
  min-height: 100vh;
  background-color: #f8f9fa;
  padding: 1rem 1.25rem;
}

.admin-header {
  padding: 1rem 1.25rem; /* 微调padding适配panel样式 */
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 0.75rem;
}

.filter-toolbar {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-label {
  font-size: 0.875rem;
  color: #4a5568;
  font-weight: 500;
}

.filter-select {
  padding: 0.375rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  font-size: 0.875rem;
  min-width: 120px;
}

.search-group {
  display: flex;
  flex: 1;
  max-width: 300px;
}

.search-input {
  flex: 1;
  padding: 0.375rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem 0 0 0.375rem;
  font-size: 0.875rem;
}

.search-btn {
  padding: 0.375rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-left: none;
  border-radius: 0 0.375rem 0.375rem 0;
  background-color: #4299e1;
  color: white;
  cursor: pointer;
}

.task-list-container {
  padding: 1.25rem;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.list-select-all {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.list-stats {
  font-size: 0.875rem;
  color: #718096;
}

.stat-num {
  color: #4299e1;
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: 3.75rem 1.25rem;
  color: #718096;
}

.empty-text {
  margin: 1rem 0 1.5rem;
  font-size: 1rem;
}

.loading-state {
  text-align: center;
  padding: 3.75rem 1.25rem;
  color: #718096;
}

.spinner {
  width: 2.5rem;
  height: 2.5rem;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #4299e1;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

.spinner.small {
  width: 1.25rem;
  height: 1.25rem;
  border-width: 2px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.task-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.task-table th {
  text-align: left;
  padding: 0.75rem 0.5rem;
  background-color: #f7fafc;
  color: #2d3748;
  font-weight: 600;
  border-bottom: 2px solid #e2e8f0;
}

.task-table td {
  padding: 0.75rem 0.5rem;
  border-bottom: 1px solid #e2e8f0;
  vertical-align: middle;
}

.status-queued {
  background-color: #fef7fb;
}

.status-processing {
  background-color: #f0f8fb;
}

.status-completed {
  background-color: #f0fdf4;
}

.status-failed {
  background-color: #fef2f2;
}

.type-tag, .status-tag {
  display: inline-block;
  padding: 0.125rem 0.5rem;
  border-radius: 1rem;
  font-size: 0.75rem;
  font-weight: 500;
}

.type-transcription {
  background-color: #e8f4f8;
  color: #3182ce;
}

.type-vad {
  background-color: #fdf2f8;
  color: #9f7aea;
}

.type-bgm {
  background-color: #eaf6fa;
  color: #38b2ac;
}

.tag-queued {
  background-color: #fef7fb;
  color: #ed8936;
}

.tag-processing {
  background-color: #e8f4f8;
  color: #4299e1;
}

.tag-completed {
  background-color: #e6fffa;
  color: #48bb78;
}

.tag-failed {
  background-color: #fed7d7;
  color: #e53e3e;
}

.task-id-cell {
  font-family: monospace;
}

.task-id {
  display: inline-block;
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filename-cell {
  max-width: 200px;
}

.filename {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-cell {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.375rem 0.75rem;
  border-radius: 0.375rem;
  border: none;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-btn {
  width: 2rem;
  height: 2rem;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 0.375rem;
  background-color: #f7fafc;
  color: #4a5568;
}

.icon-btn:hover {
  background-color: #e2e8f0;
}

.detail-btn:hover {
  color: #4299e1;
  background-color: #e8f4f8;
}

.download-btn:hover {
  color: #48bb78;
  background-color: #e6fffa;
}

.delete-btn:hover {
  color: #e53e3e;
  background-color: #fed7d7;
}

.primary-btn {
  background-color: #4299e1;
  color: white;
}

.primary-btn:hover {
  background-color: #3182ce;
}

.default-btn {
  background-color: #f7fafc;
  color: #4a5568;
}

.default-btn:hover {
  background-color: #e2e8f0;
}

.danger-btn {
  background-color: #e53e3e;
  color: white;
}

.danger-btn:hover {
  background-color: #c53030;
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background-color: #f7fafc;
  color: #4a5568;
}

.refresh-btn:hover {
  background-color: #e2e8f0;
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding: 1rem;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.page-btn {
  padding: 0.375rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  background-color: #fff;
  color: #4a5568;
  cursor: pointer;
}

.page-btn.active {
  background-color: #4299e1;
  color: white;
  border-color: #4299e1;
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  margin-left: 1rem;
  font-size: 0.875rem;
  color: #718096;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  width: 80%;
  max-width: 800px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 20px rgba(0,0,0,0.15);
  padding: 0; /* 由panel类控制padding */
}

.modal-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: #2d3748;
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  font-size: 1.25rem;
  color: #718096;
  cursor: pointer;
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-body {
  padding: 1.25rem;
}

.modal-footer {
  padding: 1rem 1.25rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item.full-width {
  grid-column: 1 / -1;
}

.detail-item label {
  font-size: 0.875rem;
  color: #718096;
  font-weight: 500;
}

.detail-item span {
  font-size: 0.875rem;
  color: #2d3748;
}

.error-item {
  grid-column: 1 / -1;
}

.error-text {
  color: #e53e3e;
  word-break: break-all;
}

.params-json, .result-json {
  background-color: #f7fafc;
  padding: 0.75rem;
  border-radius: 0.375rem;
  overflow-x: auto;
  font-family: monospace;
  font-size: 0.75rem;
  max-height: 12.5rem;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .filter-toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .search-group {
    width: 100%;
    max-width: none;
  }

  .modal-content {
    width: 95%;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .task-table {
    display: block;
    overflow-x: auto;
  }
}
</style>