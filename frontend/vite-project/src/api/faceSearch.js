// 人脸检索（Face Search）相关接口

import { requestJson } from './client'

// 单张人脸图片入库
export async function indexFaceImage({ file }) {
  if (!file) {
    throw new Error('请先选择要上传的人脸图片')
  }

  const formData = new FormData()
  formData.append('file', file)

  return requestJson('/face-search/index', {
    method: 'POST',
    body: formData,
  })
}

// 使用图片检索相似人脸
export async function searchFaceByImage({ file, topK, scoreThreshold } = {}) {
  if (!file) {
    throw new Error('请先选择要上传的查询图片')
  }

  const formData = new FormData()
  formData.append('file', file)

  if (topK != null) {
    formData.append('top_k', String(topK))
  }
  if (scoreThreshold != null) {
    formData.append('score_threshold', String(scoreThreshold))
  }

  return requestJson('/face-search/query', {
    method: 'POST',
    body: formData,
  })
}

// 查询人脸库统计信息
export async function getFaceSearchStats() {
  return requestJson('/face-search/stats', {
    method: 'GET',
  })
}

// 清空人脸数据库（危险操作，需二次确认）
export async function resetFaceDatabase({ confirm = true } = {}) {
  return requestJson('/face-search/reset', {
    method: 'POST',
    body: JSON.stringify({ confirm }),
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

// 删除指定图片对应的人脸记录
export async function deleteFaceImages({ imagePaths }) {
  if (!Array.isArray(imagePaths) || imagePaths.length === 0) {
    throw new Error('请提供要删除的图片路径列表 imagePaths')
  }

  return requestJson('/face-search/delete-images', {
    method: 'POST',
    body: JSON.stringify({ image_paths: imagePaths }),
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

// 清理“孤儿”索引记录
export async function cleanupFaceOrphans() {
  return requestJson('/face-search/cleanup-orphans', {
    method: 'POST',
  })
}
