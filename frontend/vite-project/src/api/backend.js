
import { setApiBase } from './client'
import {
  createTranscriptionTask,
  createVadTask,
  createBgmSeparationTask,
  pollTask,
  downloadBgmZip,
} from './task'
import {
  indexFaceImage,
  searchFaceByImage,
  getFaceSearchStats,
  resetFaceDatabase,
  deleteFaceImages,
  cleanupFaceOrphans,
} from './faceSearch'
import {
  createOrUpdateInterviewSession,
  chatWithInterview,
  getInterviewSessionInfo,
  clearInterviewSession,
} from './interview'

export {
  // 基础配置
  setApiBase,
  // 任务相关
  createTranscriptionTask,
  createVadTask,
  createBgmSeparationTask,
  pollTask,
  downloadBgmZip,
  // Face Search
  indexFaceImage,
  searchFaceByImage,
  getFaceSearchStats,
  resetFaceDatabase,
  deleteFaceImages,
  cleanupFaceOrphans,
  // Interview RAG
  createOrUpdateInterviewSession,
  chatWithInterview,
  getInterviewSessionInfo,
  clearInterviewSession,
}

