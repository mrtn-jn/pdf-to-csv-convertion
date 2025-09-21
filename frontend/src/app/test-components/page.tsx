"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertCircle, CheckCircle2 } from "lucide-react"

export default function TestComponents() {
  const [progress, setProgress] = useState(13)
  const [inputValue, setInputValue] = useState("")

  return (
    <div className="container mx-auto p-8 space-y-8 max-w-4xl">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold">shadcn/ui Components Test</h1>
        <p className="text-muted-foreground">
          Testing all installed shadcn/ui components to verify proper installation
        </p>
      </div>

      {/* Alerts */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Alert Components</h2>
        <Alert>
          <CheckCircle2 className="h-4 w-4" />
          <AlertTitle>Success</AlertTitle>
          <AlertDescription>
            All shadcn/ui components are installed and working correctly!
          </AlertDescription>
        </Alert>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            This is an example of a destructive alert variant.
          </AlertDescription>
        </Alert>
      </div>

      {/* Cards */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Card Components</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card>
            <CardHeader>
              <CardTitle>Card Title</CardTitle>
              <CardDescription>
                This is a card description explaining what this card contains.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p>This is the card content area where you can place any content.</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Another Card</CardTitle>
              <CardDescription>
                Cards are great for organizing content into distinct sections.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <p>Cards can contain various types of content:</p>
                <ul className="list-disc list-inside space-y-1 text-sm text-muted-foreground">
                  <li>Text content</li>
                  <li>Forms and inputs</li>
                  <li>Buttons and actions</li>
                  <li>Progress indicators</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Buttons */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Button Components</h2>
        <div className="flex flex-wrap gap-2">
          <Button>Default</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="destructive">Destructive</Button>
          <Button variant="outline">Outline</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="link">Link</Button>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button size="sm">Small</Button>
          <Button size="default">Default</Button>
          <Button size="lg">Large</Button>
          <Button size="icon">
            <CheckCircle2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Form Components */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Form Components</h2>
        <Card>
          <CardHeader>
            <CardTitle>Form Example</CardTitle>
            <CardDescription>
              Testing Input and Label components together
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="Enter your email"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input id="password" type="password" placeholder="Enter your password" />
            </div>
            <Button className="w-full">Submit</Button>
          </CardContent>
        </Card>
      </div>

      {/* Progress Component */}
      <div className="space-y-4">
        <h2 className="text-2xl font-semibold">Progress Component</h2>
        <Card>
          <CardHeader>
            <CardTitle>Progress Example</CardTitle>
            <CardDescription>
              Interactive progress bar demonstration
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress</span>
                <span>{progress}%</span>
              </div>
              <Progress value={progress} className="w-full" />
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setProgress(Math.max(0, progress - 10))}
                disabled={progress <= 0}
              >
                Decrease
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setProgress(Math.min(100, progress + 10))}
                disabled={progress >= 100}
              >
                Increase
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setProgress(Math.floor(Math.random() * 101))}
              >
                Random
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Component Status Summary */}
      <Card>
        <CardHeader>
          <CardTitle>Component Installation Status</CardTitle>
          <CardDescription>
            Summary of all installed shadcn/ui components
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>Button</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>Card</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>Input</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>Label</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>Progress</span>
            </div>
            <div className="flex items-center space-x-2">
              <CheckCircle2 className="h-4 w-4 text-green-600" />
              <span>Alert</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}