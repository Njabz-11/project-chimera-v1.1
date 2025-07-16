"use client"

import { useSession } from "next-auth/react"
import { useRouter } from "next/navigation"
import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { apiClient, SystemStatus, Mission, Lead } from "@/lib/api"
import { DashboardHeader } from "@/components/dashboard/header"
import { SystemOverview } from "@/components/dashboard/system-overview"
import { MissionsTab } from "@/components/dashboard/missions-tab"
import { LeadsTab } from "@/components/dashboard/leads-tab"
import { toast } from "sonner"

export default function DashboardPage() {
  const { data: session, status } = useSession()
  const router = useRouter()
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [missions, setMissions] = useState<Mission[]>([])
  const [leads, setLeads] = useState<Lead[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/auth/signin")
      return
    }

    if (status === "authenticated") {
      loadDashboardData()
    }
  }, [status, router])

  const loadDashboardData = async () => {
    try {
      setIsLoading(true)
      
      // Load system status
      const statusData = await apiClient.getSystemStatus()
      setSystemStatus(statusData)

      // Load missions
      const missionsData = await apiClient.getMissions()
      setMissions(missionsData.missions)

      // Load leads
      const leadsData = await apiClient.getLeads()
      setLeads(leadsData.leads)

    } catch (error) {
      console.error("Failed to load dashboard data:", error)
      toast.error("Failed to load dashboard data")
    } finally {
      setIsLoading(false)
    }
  }

  if (status === "loading" || isLoading) {
    return (
      <div className="min-h-screen cyberpunk-gradient flex items-center justify-center">
        <div className="text-center">
          <div className="cyberpunk-text-glow text-cyan-400 text-xl mb-4">
            Loading Project Chimera...
          </div>
          <div className="animate-pulse text-slate-400">
            Initializing autonomous systems...
          </div>
        </div>
      </div>
    )
  }

  if (!session) {
    return null
  }

  return (
    <div className="min-h-screen cyberpunk-gradient">
      <DashboardHeader user={session.user} onRefresh={loadDashboardData} />
      
      <main className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold cyberpunk-text-glow text-cyan-400 mb-2">
            Mission Control
          </h1>
          <p className="text-slate-400">
            Autonomous Business Operations Platform - Client Portal
          </p>
        </div>

        <SystemOverview systemStatus={systemStatus} />

        <Tabs defaultValue="missions" className="mt-8">
          <TabsList className="cyberpunk-card">
            <TabsTrigger value="missions" className="text-slate-300">Missions</TabsTrigger>
            <TabsTrigger value="leads" className="text-slate-300">Leads</TabsTrigger>
            <TabsTrigger value="analytics" className="text-slate-300">Analytics</TabsTrigger>
          </TabsList>

          <TabsContent value="missions" className="mt-6">
            <MissionsTab missions={missions} onRefresh={loadDashboardData} />
          </TabsContent>

          <TabsContent value="leads" className="mt-6">
            <LeadsTab leads={leads} missions={missions} onRefresh={loadDashboardData} />
          </TabsContent>

          <TabsContent value="analytics" className="mt-6">
            <Card className="cyberpunk-card">
              <CardHeader>
                <CardTitle className="text-cyan-400">Analytics Dashboard</CardTitle>
                <CardDescription className="text-slate-400">
                  Performance metrics and insights
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12 text-slate-400">
                  Analytics dashboard coming soon...
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  )
}
