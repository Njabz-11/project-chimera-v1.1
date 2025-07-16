"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Lead, Mission, apiClient } from "@/lib/api"
import { Search, Mail, Phone, Globe, Target } from "lucide-react"
import { toast } from "sonner"

interface LeadsTabProps {
  leads: Lead[]
  missions: Mission[]
  onRefresh: () => void
}

export function LeadsTab({ leads, missions, onRefresh }: LeadsTabProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedMission, setSelectedMission] = useState<string>("")
  const [isSearching, setIsSearching] = useState(false)

  const handleLeadSearch = async () => {
    if (!searchQuery.trim() || !selectedMission) {
      toast.error("Please enter a search query and select a mission")
      return
    }

    setIsSearching(true)
    try {
      await apiClient.searchLeads(searchQuery, parseInt(selectedMission))
      toast.success("Lead search initiated! Results will appear shortly.")
      setTimeout(onRefresh, 2000) // Refresh after 2 seconds to get new leads
    } catch (error) {
      toast.error("Failed to initiate lead search")
      console.error("Lead search error:", error)
    } finally {
      setIsSearching(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "new":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30"
      case "contacted":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
      case "qualified":
        return "bg-green-500/20 text-green-400 border-green-500/30"
      case "converted":
        return "bg-purple-500/20 text-purple-400 border-purple-500/30"
      case "rejected":
        return "bg-red-500/20 text-red-400 border-red-500/30"
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/30"
    }
  }

  const getMissionName = (missionId: number) => {
    const mission = missions.find(m => m.id === missionId)
    return mission?.name || `Mission ${missionId}`
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-cyan-400">Lead Generation</h2>
          <p className="text-slate-400">Autonomous prospect discovery and qualification</p>
        </div>
      </div>

      {/* Lead Search Section */}
      <Card className="cyberpunk-card">
        <CardHeader>
          <CardTitle className="text-cyan-400">Search for New Leads</CardTitle>
          <CardDescription className="text-slate-400">
            Use AI-powered web scraping to find potential customers
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex space-x-4">
            <div className="flex-1">
              <Input
                placeholder="Enter search query (e.g., 'marketing agencies in New York')"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="cyberpunk-border bg-slate-900/50 text-slate-100"
              />
            </div>
            <Select value={selectedMission} onValueChange={setSelectedMission}>
              <SelectTrigger className="w-48 cyberpunk-border bg-slate-900/50 text-slate-100">
                <SelectValue placeholder="Select Mission" />
              </SelectTrigger>
              <SelectContent className="cyberpunk-card">
                {missions.map((mission) => (
                  <SelectItem key={mission.id} value={mission.id.toString()}>
                    {mission.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              onClick={handleLeadSearch}
              disabled={isSearching || !searchQuery.trim() || !selectedMission}
              className="cyberpunk-button text-cyan-400"
            >
              <Search className="h-4 w-4 mr-2" />
              {isSearching ? "Searching..." : "Search"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Leads List */}
      {leads.length === 0 ? (
        <Card className="cyberpunk-card">
          <CardContent className="text-center py-12">
            <Target className="h-12 w-12 text-slate-400 mx-auto mb-4" />
            <div className="text-slate-400 mb-4">No leads found</div>
            <p className="text-sm text-slate-500">
              Use the search function above to discover new prospects
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {leads.map((lead) => (
            <Card key={lead.id} className="cyberpunk-card hover:cyberpunk-glow transition-all">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg text-cyan-400">{lead.company_name}</CardTitle>
                  <Badge className={getStatusColor(lead.status)}>
                    {lead.status}
                  </Badge>
                </div>
                <CardDescription className="text-slate-400">
                  {getMissionName(lead.mission_id)}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {lead.contact_person && (
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-slate-400">Contact:</span>
                      <span className="text-sm text-slate-300">{lead.contact_person}</span>
                    </div>
                  )}

                  {lead.email && (
                    <div className="flex items-center space-x-2">
                      <Mail className="h-4 w-4 text-slate-400" />
                      <span className="text-sm text-slate-300">{lead.email}</span>
                    </div>
                  )}

                  {lead.phone && (
                    <div className="flex items-center space-x-2">
                      <Phone className="h-4 w-4 text-slate-400" />
                      <span className="text-sm text-slate-300">{lead.phone}</span>
                    </div>
                  )}

                  {lead.website && (
                    <div className="flex items-center space-x-2">
                      <Globe className="h-4 w-4 text-slate-400" />
                      <a
                        href={lead.website}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-cyan-400 hover:text-cyan-300"
                      >
                        {lead.website}
                      </a>
                    </div>
                  )}

                  {lead.pain_point && (
                    <div>
                      <span className="text-sm text-slate-400">Pain Point:</span>
                      <p className="text-sm text-slate-300 mt-1">{lead.pain_point}</p>
                    </div>
                  )}

                  <div className="text-xs text-slate-400 pt-2 border-t border-slate-700">
                    Added: {new Date(lead.created_at).toLocaleDateString()}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
