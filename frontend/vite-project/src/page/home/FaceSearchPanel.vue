<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'

// ===================== 1. 封装请求工具（替代requestJson） =====================
/**
 * 通用请求函数
 * @param {string} url - 请求地址
 * @param {object} options - 请求配置
 * @returns {Promise<any>}
 */
const request = async (url, options = {}) => {
  const baseUrl = '' // 若接口有前缀（如/api），请在此配置
  const fullUrl = baseUrl + url

  try {
    const response = await fetch(fullUrl, {
      headers: {
        'Accept': 'application/json',
        ...(options.headers || {})
      },
      ...options
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.message || `请求失败 [${response.status}]`)
    }

    return data
  } catch (err) {
    console.error('请求错误：', err)
    throw err
  }
}

// ===================== 2. 人脸检索接口封装（对接真实接口） =====================
/**
 * 单张人脸图片入库
 * @param {File} file - 图片文件
 * @returns {Promise<any>}
 */
const indexFaceImage = async (file) => {
  if (!file) {
    throw new Error('请先选择要上传的人脸图片')
  }

  const formData = new FormData()
  formData.append('file', file)

  return request('/face-search/index', {
    method: 'POST',
    body: formData
  })
}

/**
 * 使用图片检索相似人脸
 * @param {object} params - 参数
 * @param {File} params.file - 查询图片
 * @param {number} [params.topK=5] - 返回数量
 * @param {number} [params.scoreThreshold=0.8] - 相似度阈值
 * @returns {Promise<any>}
 */
const searchFaceByImage = async ({ file, topK = 5, scoreThreshold = 0.8 }) => {
  if (!file) {
    throw new Error('请先选择要上传的查询图片')
  }

  const formData = new FormData()
  formData.append('file', file)
  formData.append('top_k', String(topK))
  formData.append('score_threshold', String(scoreThreshold))

  return request('/face-search/query', {
    method: 'POST',
    body: formData
  })
}

/**
 * 查询人脸库统计信息
 * @returns {Promise<any>}
 */
const getFaceSearchStats = async () => {
  return request('/face-search/stats', {
    method: 'GET'
  })
}

/**
 * 清空人脸数据库
 * @param {boolean} confirm - 是否确认
 * @returns {Promise<any>}
 */
const resetFaceDatabase = async (confirm = true) => {
  return request('/face-search/reset', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ confirm })
  })
}

/**
 * 删除指定图片对应的人脸记录
 * @param {string[]} imagePaths - 图片路径列表
 * @returns {Promise<any>}
 */
const deleteFaceImages = async (imagePaths) => {
  if (!Array.isArray(imagePaths) || imagePaths.length === 0) {
    throw new Error('请提供要删除的图片路径列表 imagePaths')
  }

  return request('/face-search/delete-images', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ image_paths: imagePaths })
  })
}

// ===================== 3. 页面状态管理 =====================
// 核心业务状态
const queryFile = ref(null)        // 上传/拍照的文件对象
const previewImage = ref('')      // 预览图URL
const topK = ref(5)               // 返回结果数量（默认5）
const scoreThreshold = ref(0.8)   // 相似度阈值（默认0.8）
const searchResults = ref([])     // 搜索结果列表
const stats = ref({               // 人脸库统计
  total_faces: 0,
  total_images: 0,
  total_indexed_files: 0
})
const statusMsg = ref('')         // 操作状态提示
const isLoading = ref(false)      // 全局加载状态
const isAdmin = ref(true)         // 管理员权限标记

// 摄像头相关状态
const cameraDialog = ref(false)   // 摄像头弹窗显示状态
const videoRef = ref(null)        // video元素引用
const canvasRef = ref(null)       // canvas元素引用
const stream = ref(null)          // 媒体流对象
const cameraLoading = ref(false)  // 摄像头加载状态

// ===================== 4. 核心功能实现 =====================
/**
 * 获取人脸库统计信息
 */
const fetchStats = async () => {
  try {
    const res = await getFaceSearchStats()
    stats.value = res
    statusMsg.value = '已获取人脸库统计信息'
  } catch (err) {
    showMessage(`获取统计失败：${err.message}`, 'error')
  }
}

/**
 * 开启摄像头
 */
const openCamera = async () => {
  cameraDialog.value = true
  cameraLoading.value = true

  // 等待弹窗DOM渲染完成
  setTimeout(async () => {
    try {
      // 申请摄像头权限（仅HTTPS/localhost可用）
      stream.value = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user', // 优先前置摄像头
          width: { ideal: 640 },
          height: { ideal: 480 }
        }
      })

      // 将媒体流绑定到video元素
      if (videoRef.value) {
        videoRef.value.srcObject = stream.value
        await videoRef.value.play()
        cameraLoading.value = false
      }
    } catch (err) {
      cameraDialog.value = false
      cameraLoading.value = false
      showMessage(`摄像头开启失败：${err.message || '请允许摄像头权限'}`, 'error')
    }
  }, 300)
}

/**
 * 关闭摄像头
 */
const closeCamera = () => {
  if (stream.value) {
    // 停止所有媒体轨道，释放摄像头
    stream.value.getTracks().forEach(track => track.stop())
    stream.value = null
  }
  cameraLoading.value = false
  cameraDialog.value = false
}

/**
 * 摄像头拍照
 */
const takePhoto = () => {
  if (!videoRef.value || !canvasRef.value || cameraLoading.value) return

  // 获取视频实际尺寸
  const width = videoRef.value.videoWidth || 640
  const height = videoRef.value.videoHeight || 480

  // 设置canvas尺寸并绘制视频帧
  canvasRef.value.width = width
  canvasRef.value.height = height
  const ctx = canvasRef.value.getContext('2d')
  ctx.drawImage(videoRef.value, 0, 0, width, height)

  // 将canvas转为File对象（兼容接口上传）
  canvasRef.value.toBlob((blob) => {
    const file = new File([blob], `camera-photo-${Date.now()}.jpg`, {
      type: 'image/jpeg'
    })

    // 更新预览和文件状态
    previewImage.value = canvasRef.value.toDataURL('image/jpeg')
    queryFile.value = file
    statusMsg.value = `已拍摄照片：${file.name}`

    // 关闭摄像头弹窗
    closeCamera()
    showMessage('拍照成功！', 'success')
  }, 'image/jpeg', 0.9) // 0.9为图片质量
}

/**
 * 处理文件上传（input file change事件）
 */
const handleFileChange = (e) => {
  const file = e.target.files[0]
  if (!file) return

  // 校验文件类型
  if (!file.type.startsWith('image/')) {
    showMessage('请选择有效的图片文件！', 'warning')
    return
  }

  // 更新状态
  queryFile.value = file
  previewImage.value = URL.createObjectURL(file)
  statusMsg.value = `已选择文件：${file.name}`

  // 清空input值（避免重复选择同一文件不触发change）
  e.target.value = ''
}

/**
 * 模拟人脸检测（预览逻辑）
 */
const handleDetectFace = () => {
  if (!previewImage.value) {
    showMessage('请先上传/拍摄查询图像！', 'warning')
    return
  }
  showMessage('已检测到人脸（预览当前图像）', 'info')
}

/**
 * 执行相似人脸搜索（核心接口调用）
 */
const handleSearch = async () => {
  if (!queryFile.value) {
    showMessage('请先上传/拍摄查询图像！', 'warning')
    return
  }

  isLoading.value = true
  statusMsg.value = '正在检索相似人脸，请稍候...'

  try {
    // 调用真实的人脸搜索接口
    const res = await searchFaceByImage({
      file: queryFile.value,
      topK: topK.value,
      scoreThreshold: scoreThreshold.value
    })

    // 处理搜索结果
    if (res.success && res.matches && res.matches.length > 0) {
      searchResults.value = res.matches.map(item => ({
        url: item.image_path,       // 图片路径（需确保前端可访问）
        thumbnailUrl: item.image_path,
        distance: item.distance,    // 相似度距离（越小越相似）
        originalPath: item.original_path
      }))
      statusMsg.value = `检索成功！找到 ${res.matches.length} 张相似人脸图片`
    } else {
      searchResults.value = []
      statusMsg.value = '未检索到相似人脸，请调整搜索参数后重试'
    }
  } catch (err) {
    statusMsg.value = `检索失败：${err.message}`
    showMessage(statusMsg.value, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 图片入库（管理员功能）
 */
const handleIndexImage = async () => {
  if (!queryFile.value) {
    showMessage('请先选择要入库的人脸图片！', 'warning')
    return
  }

  if (!confirm('确认将该图片入库到人脸库吗？')) return

  isLoading.value = true
  statusMsg.value = '正在将图片入库，请稍候...'

  try {
    const res = await indexFaceImage(queryFile.value)
    statusMsg.value = res.message || '入库操作完成'
    showMessage(res.success ? '入库成功！' : `入库失败：${res.errors?.join('；')}`, res.success ? 'success' : 'error')

    // 重新获取统计信息
    await fetchStats()
  } catch (err) {
    statusMsg.value = `入库失败：${err.message}`
    showMessage(statusMsg.value, 'error')
  } finally {
    isLoading.value = false
  }
}

/**
 * 通用消息提示（原生实现）
 * @param {string} msg - 提示文本
 * @param {string} type - 类型：success/error/warning/info
 */
const showMessage = (msg, type = 'info') => {
  // 创建提示元素
  const toast = document.createElement('div')
  toast.className = `toast toast-${type}`
  toast.textContent = msg

  // 基础样式
  Object.assign(toast.style, {
    position: 'fixed',
    top: '20px',
    right: '20px',
    padding: '12px 20px',
    borderRadius: '6px',
    color: '#fff',
    zIndex: '9999',
    opacity: '0',
    transition: 'opacity 0.3s ease, transform 0.3s ease',
    transform: 'translateX(100%)',
    maxWidth: '320px',
    wordBreak: 'break-all',
    boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
  })

  // 不同类型的背景色
  const bgColors = {
    success: '#67c23a',
    error: '#f56c6c',
    warning: '#e6a23c',
    info: '#409eff'
  }
  toast.style.backgroundColor = bgColors[type] || bgColors.info

  // 添加到页面
  document.body.appendChild(toast)

  // 显示动画
  setTimeout(() => {
    toast.style.opacity = '1'
    toast.style.transform = 'translateX(0)'
  }, 10)

  // 自动关闭
  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transform = 'translateX(100%)'
    setTimeout(() => {
      document.body.removeChild(toast)
    }, 300)
  }, 3000)
}

// ===================== 5. 生命周期 & 监听 =====================
// 监听参数变化，重置搜索结果
watch([topK, scoreThreshold], () => {
  searchResults.value = []
  statusMsg.value = '搜索参数已更新，请重新执行检索'
})

// 页面挂载时加载统计信息
onMounted(() => {
  fetchStats()
})

// 组件卸载时释放摄像头资源
onUnmounted(() => {
  if (stream.value) {
    stream.value.getTracks().forEach(track => track.stop())
  }
})
</script>

<template>
  <div class="face-search-container">
    <!-- 页面标题 -->
    <header class="page-header">
      <h1>人脸检索系统</h1>
      <p class="page-desc">支持图片上传/摄像头拍照，检索相似人脸并管理人脸库</p>
    </header>

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 左侧操作面板 -->
      <div class="left-panel">
        <div class="card">
          <!-- 1. 图像来源区域 -->
          <div class="section">
            <h3 class="section-title">1. 选择图像来源</h3>

            <!-- 上传区域 -->
            <div class="upload-area">
              <label class="upload-label" for="file-upload">
                <div class="upload-placeholder" v-if="!previewImage">
                  <svg class="upload-icon" viewBox="0 0 24 24" width="48" height="48">
                    <path d="M19 8h-1V3H6v5H5c-1.66 0-3 1.34-3 3v6h4v4h12v-4h4v-6c0-1.66-1.34-3-3-3zM8 5h8v3H8V5zm8 12v2H8v-2H6v-4h12v4h-2z" fill="#909399"/>
                    <path d="M12 10l4 4h-2v4h-4v-4H8l4-4z" fill="#909399"/>
                  </svg>
                  <p class="upload-text">拖拽图片到此处</p>
                  <p class="upload-tip">或点击选择文件</p>
                </div>
                <img v-else :src="previewImage" class="preview-img" alt="预览图" />
              </label>
              <input
                type="file"
                id="file-upload"
                accept="image/*"
                class="file-input"
                @change="handleFileChange"
              />
            </div>

            <!-- 操作按钮组 -->
            <div class="btn-group">
              <button class="btn btn-primary" @click="openCamera">
                <svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16">
                  <path d="M12 10c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm7-7H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.11 0 2-.9 2-2V5c0-1.1-.89-2-2-2zm-1.75 9c0 2.9-2.35 5.25-5.25 5.25S6.75 14.9 6.75 12 9.1 6.75 12 6.75 17.25 9.1 17.25 12z" fill="#fff"/>
                </svg>
                摄像头拍照
              </button>
              <button class="btn btn-secondary" @click="handleDetectFace" :disabled="!previewImage">
                <svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16">
                  <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" fill="#fff"/>
                </svg>
                检测人脸
              </button>
              <button
                class="btn btn-success"
                @click="handleIndexImage"
                :disabled="!previewImage || isLoading"
                v-if="isAdmin"
              >
                <svg class="btn-icon" viewBox="0 0 24 24" width="16" height="16">
                  <path d="M19 3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.11 0 2-.9 2-2V5c0-1.1-.89-2-2-2zm-2 10h-4v4h-2v-4H7v-2h4V7h2v4h4v2z" fill="#fff"/>
                </svg>
                图片入库
              </button>
            </div>
          </div>

          <!-- 2. 搜索参数配置 -->
          <div class="section">
            <h3 class="section-title">2. 检索参数配置</h3>

            <!-- 返回结果数量 -->
            <div class="param-item">
              <label class="param-label">返回结果数量 (top_k)</label>
              <div class="param-control">
                <input
                  type="number"
                  v-model="topK"
                  min="1"
                  max="100"
                  class="param-input"
                />
                <input
                  type="range"
                  v-model="topK"
                  min="1"
                  max="100"
                  class="param-slider"
                />
              </div>
            </div>

            <!-- 相似度阈值 -->
            <div class="param-item">
              <label class="param-label">相似度阈值 (score_threshold)</label>
              <div class="param-control">
                <input
                  type="number"
                  v-model="scoreThreshold"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  class="param-input"
                />
                <input
                  type="range"
                  v-model="scoreThreshold"
                  min="0.1"
                  max="1.0"
                  step="0.05"
                  class="param-slider"
                />
              </div>
              <p class="param-tip">阈值越小，检索结果越相似（推荐0.7-0.9）</p>
            </div>
          </div>

          <!-- 3. 执行检索 -->
          <div class="section">
            <button
              class="btn btn-primary btn-large"
              @click="handleSearch"
              :disabled="!previewImage || isLoading"
            >
              <span v-if="isLoading" class="loading-spinner"></span>
              <svg v-else class="btn-icon" viewBox="0 0 24 24" width="18" height="18">
                <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" fill="#fff"/>
              </svg>
              检索相似人脸
            </button>
          </div>

          <!-- 4. 状态提示 -->
          <div class="section status-section" v-if="statusMsg">
            <div class="status-box">
              {{ statusMsg }}
            </div>
          </div>

          <!-- 5. 人脸库统计 -->
          <div class="section stats-section">
            <h3 class="section-title">3. 人脸库统计</h3>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">总人脸数：</span>
                <span class="stat-value">{{ stats.total_faces }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">唯一图像数：</span>
                <span class="stat-value">{{ stats.total_images }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">已索引文件数：</span>
                <span class="stat-value">{{ stats.total_indexed_files }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧结果面板 -->
      <div class="right-panel">
        <div class="card">
          <h3 class="section-title">检索结果 ({{ searchResults.length }})</h3>

          <!-- 空结果提示 -->
          <div class="empty-result" v-if="searchResults.length === 0 && !isLoading">
            <svg class="empty-icon" viewBox="0 0 24 24" width="64" height="64">
              <path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z" fill="#ccc"/>
            </svg>
            <p class="empty-text">暂无检索结果，请上传图片并执行检索</p>
          </div>

          <!-- 加载中提示 -->
          <div class="loading-result" v-if="isLoading">
            <div class="loading-spinner large"></div>
            <p>正在检索相似人脸...</p>
          </div>

          <!-- 结果列表 -->
          <div class="results-grid" v-if="searchResults.length > 0 && !isLoading">
            <div class="result-item" v-for="(item, index) in searchResults" :key="index">
              <div class="result-img-container">
                <img :src="item.url" :alt="`相似人脸${index+1}`" class="result-img" />
              </div>
              <div class="result-info">
                <p class="distance">相似度距离：{{ item.distance.toFixed(4) }}</p>
                <p class="path" v-if="item.originalPath">
                  路径：{{ item.originalPath }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- 摄像头弹窗 -->
    <div class="modal" v-if="cameraDialog">
      <div class="modal-overlay" @click="closeCamera"></div>
      <div class="modal-content">
        <div class="modal-header">
          <h3>摄像头拍照</h3>
          <button class="modal-close" @click="closeCamera">×</button>
        </div>
        <div class="modal-body">
          <div class="camera-container">
            <!-- 视频预览 -->
            <video ref="videoRef" class="camera-video" autoplay playsinline></video>
            <!-- 用于截图的canvas（隐藏） -->
            <canvas ref="canvasRef" class="camera-canvas"></canvas>

            <!-- 摄像头加载提示 -->
            <div class="camera-loading" v-if="cameraLoading">
              <div class="loading-spinner"></div>
              <p>正在初始化摄像头...</p>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="closeCamera">取消</button>
          <button class="btn btn-primary" @click="takePhoto" :disabled="cameraLoading">
            拍摄照片
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.face-search-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
  min-height: 100vh;
  background-color: #f5f7fa;
}

/* 页面头部 */
.page-header {
  text-align: center;
  margin-bottom: 30px;
}

.page-header h1 {
  font-size: 28px;
  color: #1f2937;
  margin-bottom: 8px;
}

.page-desc {
  color: #6b7280;
  font-size: 16px;
}

/* 主内容区 */
.main-content {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 20px;
}

/* 通用卡片样式 */
.card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  padding: 24px;
  height: 100%;
}

/* 左侧面板 */
.left-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.section {
  margin-bottom: 24px;
}

.section:last-child {
  margin-bottom: 0;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid #f0f2f5;
}

/* 上传区域 */
.upload-area {
  margin-bottom: 16px;
}

.upload-label {
  display: block;
  width: 100%;
  height: 200px;
  border: 2px dashed #d1d5db;
  border-radius: 8px;
  cursor: pointer;
  overflow: hidden;
  position: relative;
  transition: border-color 0.3s ease;
}

.upload-label:hover {
  border-color: #409eff;
}

.file-input {
  display: none;
}

.upload-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
}

.upload-text {
  margin-top: 12px;
  font-size: 14px;
}

.upload-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #d1d5db;
}

.preview-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

/* 按钮样式 */
.btn-group {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  gap: 6px;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-primary {
  background-color: #409eff;
  color: #fff;
}

.btn-primary:hover:not(:disabled) {
  background-color: #338aff;
}

.btn-secondary {
  background-color: #6c757d;
  color: #fff;
}

.btn-secondary:hover:not(:disabled) {
  background-color: #5c636a;
}

.btn-success {
  background-color: #67c23a;
  color: #fff;
}

.btn-success:hover:not(:disabled) {
  background-color: #5cb837;
}

.btn-large {
  width: 100%;
  padding: 12px 20px;
  font-size: 16px;
}

.btn-icon {
  flex-shrink: 0;
}

/* 参数配置 */
.param-item {
  margin-bottom: 16px;
}

.param-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  color: #4b5563;
}

.param-control {
  display: flex;
  align-items: center;
  gap: 12px;
}

.param-input {
  width: 80px;
  padding: 6px 8px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  font-size: 14px;
}

.param-slider {
  flex: 1;
  height: 6px;
  accent-color: #409eff;
}

.param-tip {
  margin-top: 4px;
  font-size: 12px;
  color: #9ca3af;
}

/* 状态提示 */
.status-section {
  margin-bottom: 0;
}

.status-box {
  padding: 12px;
  background-color: #f0f9ff;
  color: #3399ff;
  border-radius: 6px;
  font-size: 14px;
}

/* 统计信息 */
.stats-grid {
  display: grid;
  gap: 8px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #f0f2f5;
}

.stat-label {
  color: #6b7280;
  font-size: 14px;
}

.stat-value {
  font-weight: 600;
  color: #1f2937;
}

/* 右侧面板 */
.right-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* 结果区域 */
.empty-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #9ca3af;
  text-align: center;
}

.empty-text {
  margin-top: 16px;
  font-size: 16px;
}

.loading-result {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: #6b7280;
}

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.result-item {
  background-color: #f9fafb;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.result-img-container {
  width: 100%;
  height: 180px;
  overflow: hidden;
}

.result-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.result-item:hover .result-img {
  transform: scale(1.05);
}

.result-info {
  padding: 12px;
}

.distance {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin-bottom: 4px;
}

.path {
  font-size: 12px;
  color: #6b7280;
  word-break: break-all;
}

/* 摄像头弹窗 */
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
}

.modal-content {
  width: 700px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 1;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f2f5;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.modal-close {
  background: none;
  border: none;
  font-size: 20px;
  color: #6b7280;
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: background-color 0.2s ease;
}

.modal-close:hover {
  background-color: #f0f2f5;
  color: #1f2937;
}

.modal-body {
  padding: 20px;
}

.modal-footer {
  padding: 16px 20px;
  border-top: 1px solid #f0f2f5;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

/* 摄像头容器 */
.camera-container {
  width: 100%;
  height: 450px;
  background-color: #000;
  border-radius: 6px;
  position: relative;
  overflow: hidden;
}

.camera-video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.camera-canvas {
  display: none;
}

.camera-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  background-color: rgba(0, 0, 0, 0.7);
}

/* 加载动画 */
.loading-spinner {
  width: 20px;
  height: 20px;
  border: 3px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: #fff;
  animation: spin 1s linear infinite;
  margin-right: 8px;
}

.loading-spinner.large {
  width: 40px;
  height: 40px;
  margin-right: 0;
  margin-bottom: 16px;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .modal-content {
    width: 90%;
    max-width: 600px;
  }

  .camera-container {
    height: 350px;
  }
}

@media (max-width: 768px) {
  .results-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  }

  .camera-container {
    height: 300px;
  }
}
</style>