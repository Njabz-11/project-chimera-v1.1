"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { apiClient, MissionBriefing } from "@/lib/api"
import { toast } from "sonner"
import { Plus, Minus } from "lucide-react"

interface CreateMissionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

export function CreateMissionDialog({ open, onOpenChange, onSuccess }: CreateMissionDialogProps) {
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState<MissionBriefing>({
    business_goal: "",
    target_audience: "",
    brand_voice: "",
    service_offerings: [""],
    contact_info: {
      email: "",
      phone: "",
      website: ""
    }
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      // Filter out empty service offerings
      const cleanedData = {
        ...formData,
        service_offerings: formData.service_offerings.filter(service => service.trim() !== "")
      }

      await apiClient.createMission(cleanedData)
      toast.success("Mission created successfully!")
      onSuccess()
      onOpenChange(false)
      
      // Reset form
      setFormData({
        business_goal: "",
        target_audience: "",
        brand_voice: "",
        service_offerings: [""],
        contact_info: {
          email: "",
          phone: "",
          website: ""
        }
      })
    } catch (error) {
      toast.error("Failed to create mission")
      console.error("Mission creation error:", error)
    } finally {
      setIsLoading(false)
    }
  }

  const addServiceOffering = () => {
    setFormData(prev => ({
      ...prev,
      service_offerings: [...prev.service_offerings, ""]
    }))
  }

  const removeServiceOffering = (index: number) => {
    setFormData(prev => ({
      ...prev,
      service_offerings: prev.service_offerings.filter((_, i) => i !== index)
    }))
  }

  const updateServiceOffering = (index: number, value: string) => {
    setFormData(prev => ({
      ...prev,
      service_offerings: prev.service_offerings.map((service, i) => 
        i === index ? value : service
      )
    }))
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="cyberpunk-card max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-cyan-400">Create New Mission</DialogTitle>
          <DialogDescription className="text-slate-400">
            Define your business objectives and let Project Chimera execute autonomously
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="business_goal" className="text-slate-300">Business Goal</Label>
            <Textarea
              id="business_goal"
              value={formData.business_goal}
              onChange={(e) => setFormData(prev => ({ ...prev, business_goal: e.target.value }))}
              placeholder="Describe your primary business objective..."
              className="cyberpunk-border bg-slate-900/50 text-slate-100"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="target_audience" className="text-slate-300">Target Audience</Label>
            <Textarea
              id="target_audience"
              value={formData.target_audience}
              onChange={(e) => setFormData(prev => ({ ...prev, target_audience: e.target.value }))}
              placeholder="Define your ideal customer profile..."
              className="cyberpunk-border bg-slate-900/50 text-slate-100"
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="brand_voice" className="text-slate-300">Brand Voice</Label>
            <Textarea
              id="brand_voice"
              value={formData.brand_voice}
              onChange={(e) => setFormData(prev => ({ ...prev, brand_voice: e.target.value }))}
              placeholder="Describe your brand personality and communication style..."
              className="cyberpunk-border bg-slate-900/50 text-slate-100"
              required
            />
          </div>

          <div className="space-y-2">
            <Label className="text-slate-300">Service Offerings</Label>
            {formData.service_offerings.map((service, index) => (
              <div key={index} className="flex space-x-2">
                <Input
                  value={service}
                  onChange={(e) => updateServiceOffering(index, e.target.value)}
                  placeholder="Enter a service or product offering..."
                  className="cyberpunk-border bg-slate-900/50 text-slate-100"
                />
                {formData.service_offerings.length > 1 && (
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => removeServiceOffering(index)}
                    className="cyberpunk-button text-red-400"
                  >
                    <Minus className="h-4 w-4" />
                  </Button>
                )}
              </div>
            ))}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={addServiceOffering}
              className="cyberpunk-button text-cyan-400"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Service
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-slate-300">Email</Label>
              <Input
                id="email"
                type="email"
                value={formData.contact_info.email}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  contact_info: { ...prev.contact_info, email: e.target.value }
                }))}
                placeholder="contact@company.com"
                className="cyberpunk-border bg-slate-900/50 text-slate-100"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone" className="text-slate-300">Phone</Label>
              <Input
                id="phone"
                value={formData.contact_info.phone}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  contact_info: { ...prev.contact_info, phone: e.target.value }
                }))}
                placeholder="+1 (555) 123-4567"
                className="cyberpunk-border bg-slate-900/50 text-slate-100"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="website" className="text-slate-300">Website</Label>
              <Input
                id="website"
                value={formData.contact_info.website}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  contact_info: { ...prev.contact_info, website: e.target.value }
                }))}
                placeholder="https://company.com"
                className="cyberpunk-border bg-slate-900/50 text-slate-100"
              />
            </div>
          </div>

          <div className="flex justify-end space-x-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="cyberpunk-button text-slate-400"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isLoading}
              className="cyberpunk-button text-cyan-400"
            >
              {isLoading ? "Creating..." : "Create Mission"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
