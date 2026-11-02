import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
})

export function errorMessage(error, fallback = 'Terjadi kesalahan. Coba lagi.') {
  return (
    error?.response?.data?.error ||
    (error?.code === 'ECONNABORTED' ? 'Permintaan timeout. Coba lagi.' : null) ||
    error?.message ||
    fallback
  )
}

const data = (promise) => promise.then((response) => response.data)

export const getHealth = () => data(api.get('/health'))

export const searchTracks = (query, limit = 5) => data(api.post('/search', { query, limit }))

export const convertTrack = (track) =>
  data(
    api.post('/convert', {
      id: track.id,
      title: track.title,
      channel: track.channel,
      duration: track.duration,
      thumbnail: track.thumbnail,
    }),
  )

export const getJob = (videoId) => data(api.get(`/job/${videoId}`))

/** URL audio langsung dari YouTube — tanpa convert dan tanpa menyimpan file. */
export const streamUrl = (videoId) => `/api/stream/${videoId}`

export const cancelJob = (videoId) => data(api.delete(`/job/${videoId}`))

export const getLibrary = () => data(api.get('/library'))

export const deleteLibraryItem = (videoId) => data(api.delete(`/library/${videoId}`))

export const openFolder = (videoId) => data(api.post('/open-folder', videoId ? { id: videoId } : {}))

export const getSettings = () => data(api.get('/settings'))

export const updateSettings = (downloadDir, moveFiles = true) =>
  data(api.post('/settings', { downloadDir, moveFiles }))

export const resetSettings = () => data(api.delete('/settings'))

export const browseFolder = () => data(api.post('/settings/browse'))
