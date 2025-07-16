import { getSession } from "next-auth/react"

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface MissionBriefing {
  business_goal: string
  target_audience: string
  brand_voice: string
  service_offerings: string[]
  contact_info: Record<string, string>
}

export interface Mission {
  id: number
  name: string
  description: string
  status: string
  progress: number
  agents: string[]
  started: string
  target?: string
  revenue?: string
  business_goal?: string
  target_audience?: string
  brand_voice?: string
}

export interface Lead {
  id: number
  company_name: string
  contact_person?: string
  email?: string
  phone?: string
  website?: string
  pain_point?: string
  status: string
  mission_id: number
  created_at: string
}

export interface SystemStatus {
  status: string
  active_agents: number
  total_leads: number
  active_missions: number
  uptime: string
  total_revenue?: string
  revenue_change?: string
  missions_change?: string
  deals_change?: string
  system_errors: number
  errors_status: string
}

class ApiClient {
  private async getAuthHeaders() {
    const session = await getSession()
    return {
      'Content-Type': 'application/json',
      ...(session?.accessToken && { 'Authorization': `Bearer ${session.accessToken}` })
    }
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = await this.getAuthHeaders()
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        ...headers,
        ...options.headers,
      },
    })

    if (!response.ok) {
      throw new Error(`API request failed: ${response.statusText}`)
    }

    return response.json()
  }

  // Mission Management
  async createMission(briefing: MissionBriefing): Promise<{ mission_id: number; message: string }> {
    return this.request('/mission/create', {
      method: 'POST',
      body: JSON.stringify(briefing),
    })
  }

  async getMissions(): Promise<{ missions: Mission[]; total: number }> {
    return this.request('/missions')
  }

  async getMissionDetails(missionId: number): Promise<Mission> {
    return this.request(`/mission/${missionId}`)
  }

  // Lead Management
  async getLeads(missionId?: number): Promise<{ leads: Lead[]; total: number }> {
    const params = missionId ? `?mission_id=${missionId}` : ''
    return this.request(`/leads${params}`)
  }

  async searchLeads(searchQuery: string, missionId: number, sources: string[] = ["google_maps", "google_search"], maxLeads: number = 25) {
    return this.request('/agent/prospector/search', {
      method: 'POST',
      body: JSON.stringify({
        search_query: searchQuery,
        mission_id: missionId,
        sources,
        max_leads: maxLeads
      }),
    })
  }

  // System Status
  async getSystemStatus(): Promise<SystemStatus> {
    return this.request('/system/status/detailed')
  }

  // Health Check
  async healthCheck(): Promise<{ status: string }> {
    return this.request('/health')
  }
}

export const apiClient = new ApiClient()
