"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SystemStatus } from "@/lib/api"
import { Activity, Users, Target, DollarSign, AlertTriangle } from "lucide-react"

interface SystemOverviewProps {
  systemStatus: SystemStatus | null
}

export function SystemOverview({ systemStatus }: SystemOverviewProps) {
  if (!systemStatus) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="cyberpunk-card animate-pulse">
            <CardContent className="p-6">
              <div className="h-16 bg-slate-700/50 rounded"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const statusColor = systemStatus.status === "operational" ? "text-green-400" : "text-red-400"
  const errorColor = systemStatus.system_errors > 0 ? "text-red-400" : "text-green-400"

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <Card className="cyberpunk-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-slate-300">System Status</CardTitle>
          <Activity className={`h-4 w-4 ${statusColor}`} />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${statusColor} capitalize`}>
            {systemStatus.status}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Uptime: {systemStatus.uptime}
          </p>
        </CardContent>
      </Card>

      <Card className="cyberpunk-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-slate-300">Active Agents</CardTitle>
          <Users className="h-4 w-4 text-cyan-400" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-cyan-400">
            {systemStatus.active_agents}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Autonomous systems online
          </p>
        </CardContent>
      </Card>

      <Card className="cyberpunk-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-slate-300">Total Leads</CardTitle>
          <Target className="h-4 w-4 text-blue-400" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-blue-400">
            {systemStatus.total_leads}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Prospects identified
          </p>
        </CardContent>
      </Card>

      <Card className="cyberpunk-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-slate-300">Active Missions</CardTitle>
          <DollarSign className="h-4 w-4 text-yellow-400" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-yellow-400">
            {systemStatus.active_missions}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Operations running
          </p>
        </CardContent>
      </Card>

      {systemStatus.total_revenue && (
        <Card className="cyberpunk-card">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-300">Revenue</CardTitle>
            <DollarSign className="h-4 w-4 text-green-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-400">
              {systemStatus.total_revenue}
            </div>
            {systemStatus.revenue_change && (
              <p className="text-xs text-slate-400 mt-1">
                {systemStatus.revenue_change} from last period
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card className="cyberpunk-card">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-slate-300">System Health</CardTitle>
          <AlertTriangle className={`h-4 w-4 ${errorColor}`} />
        </CardHeader>
        <CardContent>
          <div className={`text-2xl font-bold ${errorColor}`}>
            {systemStatus.system_errors}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {systemStatus.errors_status}
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
