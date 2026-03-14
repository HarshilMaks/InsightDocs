import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background text-foreground font-sans antialiased">
        <div className="container mx-auto py-8">
          <h1 className="text-4xl font-bold mb-4">InsightDocs</h1>
          <p className="text-muted-foreground">Frontend setup complete with Shadcn UI.</p>
        </div>
      </div>
    </Router>
  )
}

export default App
