"use client"

import { ThemeProvider } from "@/contexts/theme-context"
import { CommandCenter } from "@/components/dashboard/command-center"

export default function Home() {
  return (
    <ThemeProvider>
      <CommandCenter />
    </ThemeProvider>
  )
}
