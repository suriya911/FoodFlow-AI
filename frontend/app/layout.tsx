import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'FoodFlow AI — Agentic Food Dispatch',
  description:
    'Live map-based surplus food redistribution powered by NVIDIA Nemotron.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-950 text-white antialiased overflow-hidden">
        {children}
      </body>
    </html>
  )
}
