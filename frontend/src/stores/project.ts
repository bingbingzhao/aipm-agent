import { ref } from 'vue'
import { defineStore } from 'pinia'
import { apiClient } from '@/api/client'
import type { Project } from '@/types'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const loading = ref(false)

  async function fetchProjects() {
    loading.value = true
    try {
      projects.value = await apiClient.get('/api/projects/')
    } finally {
      loading.value = false
    }
  }

  async function createProject(title: string, description: string): Promise<Project> {
    const project = await apiClient.post('/api/projects/', { title, description })
    projects.value.unshift(project)
    return project
  }

  async function getProject(id: string): Promise<Project> {
    return await apiClient.get(`/api/projects/${id}`)
  }

  async function updateProject(id: string, data: Partial<Project>): Promise<Project> {
    return await apiClient.patch(`/api/projects/${id}`, data)
  }

  async function deleteProject(id: string): Promise<void> {
    await apiClient.delete(`/api/projects/${id}`)
    projects.value = projects.value.filter(p => p.id !== id)
  }

  return { projects, loading, fetchProjects, createProject, getProject, updateProject, deleteProject }
})
