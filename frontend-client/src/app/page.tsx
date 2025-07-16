"use client"

import { useEffect } from "react"
import { useSession } from "next-auth/react"
import { useRouter } from "next/navigation"

export default function Home() {
  const { data: session, status } = useSession()
  const router = useRouter()

  useEffect(() => {
    if (status === "loading") return // Still loading

    if (session) {
      router.push("/dashboard")
    } else {
      router.push("/auth/signin")
    }
  }, [session, status, router])

  return (
    <div className="min-h-screen cyberpunk-gradient flex items-center justify-center">
      <div className="text-center">
        <div className="cyberpunk-text-glow text-cyan-400 text-2xl mb-4">
          Project Chimera
        </div>
        <div className="animate-pulse text-slate-400">
          Initializing autonomous systems...
        </div>
      </div>
    </div>
  )
}
