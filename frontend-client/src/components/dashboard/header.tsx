"use client"

import { signOut } from "next-auth/react"
import { Button } from "@/components/ui/button"
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu"
import { RefreshCw, User, LogOut } from "lucide-react"

interface DashboardHeaderProps {
  user: {
    name?: string | null
    email?: string | null
    role?: string
  }
  onRefresh: () => void
}

export function DashboardHeader({ user, onRefresh }: DashboardHeaderProps) {
  return (
    <header className="border-b border-cyan-500/20 bg-slate-900/50 backdrop-blur-sm">
      <div className="container mx-auto px-4 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <h1 className="text-xl font-bold cyberpunk-text-glow text-cyan-400">
            Project Chimera
          </h1>
          <span className="text-slate-400 text-sm">Client Portal</span>
        </div>

        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            size="sm"
            onClick={onRefresh}
            className="cyberpunk-button text-cyan-400"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="cyberpunk-button text-cyan-400">
                <User className="h-4 w-4 mr-2" />
                {user.name || "User"}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="cyberpunk-card" align="end">
              <DropdownMenuItem className="text-slate-300">
                <User className="h-4 w-4 mr-2" />
                Profile
              </DropdownMenuItem>
              <DropdownMenuItem 
                className="text-red-400 hover:text-red-300"
                onClick={() => signOut({ callbackUrl: "/auth/signin" })}
              >
                <LogOut className="h-4 w-4 mr-2" />
                Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  )
}
