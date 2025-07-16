"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Mission } from "@/lib/api"
import { Plus, Play, Pause, MoreHorizontal } from "lucide-react"
import { CreateMissionDialog } from "./create-mission-dialog"

interface MissionsTabProps {
  missions: Mission[]
  onRefresh: () => void
}

export function MissionsTab({ missions, onRefresh }: MissionsTabProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "active":
      case "running":
        return "bg-green-500/20 text-green-400 border-green-500/30"
      case "paused":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30"
      case "completed":
        return "bg-blue-500/20 text-blue-400 border-blue-500/30"
      case "failed":
        return "bg-red-500/20 text-red-400 border-red-500/30"
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/30"
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-cyan-400">Mission Control</h2>
          <p className="text-slate-400">Manage your autonomous business operations</p>
        </div>
        <Button
          onClick={() => setShowCreateDialog(true)}
          className="cyberpunk-button text-cyan-400"
        >
          <Plus className="h-4 w-4 mr-2" />
          New Mission
        </Button>
      </div>

      {missions.length === 0 ? (
        <Card className="cyberpunk-card">
          <CardContent className="text-center py-12">
            <div className="text-slate-400 mb-4">No missions found</div>
            <Button
              onClick={() => setShowCreateDialog(true)}
              className="cyberpunk-button text-cyan-400"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Your First Mission
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {missions.map((mission) => (
            <Card key={mission.id} className="cyberpunk-card hover:cyberpunk-glow transition-all">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg text-cyan-400">{mission.name}</CardTitle>
                  <Badge className={getStatusColor(mission.status)}>
                    {mission.status}
                  </Badge>
                </div>
                <CardDescription className="text-slate-400">
                  {mission.description}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-slate-400">Progress</span>
                      <span className="text-cyan-400">{mission.progress}%</span>
                    </div>
                    <div className="w-full bg-slate-700 rounded-full h-2">
                      <div
                        className="bg-cyan-400 h-2 rounded-full transition-all"
                        style={{ width: `${mission.progress}%` }}
                      />
                    </div>
                  </div>

                  {mission.business_goal && (
                    <div>
                      <span className="text-sm text-slate-400">Goal:</span>
                      <p className="text-sm text-slate-300 mt-1">{mission.business_goal}</p>
                    </div>
                  )}

                  {mission.target_audience && (
                    <div>
                      <span className="text-sm text-slate-400">Target:</span>
                      <p className="text-sm text-slate-300 mt-1">{mission.target_audience}</p>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-4">
                    <div className="text-xs text-slate-400">
                      Started: {new Date(mission.started).toLocaleDateString()}
                    </div>
                    <div className="flex space-x-2">
                      <Button size="sm" variant="outline" className="cyberpunk-button text-cyan-400">
                        <Play className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="outline" className="cyberpunk-button text-cyan-400">
                        <Pause className="h-3 w-3" />
                      </Button>
                      <Button size="sm" variant="outline" className="cyberpunk-button text-cyan-400">
                        <MoreHorizontal className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <CreateMissionDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        onSuccess={onRefresh}
      />
    </div>
  )
}
