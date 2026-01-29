import { ChatWindow } from "@/components/ChatWindow";
import { AgentFlowVisualization } from "@/components/AgentFlowVisualization";
import { LiveLogs } from "@/components/LiveLogs";
import { DetailedLogs } from "@/components/DetailedLogs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { MessageSquare, Bot, Shield, Zap } from "lucide-react";

export default function Home() {
  return (
    <main className="w-full py-4">
      {/* Header */}
      <div className="text-center mb-4 px-4">
        <div className="flex items-center justify-center gap-2 mb-2">
          <h1 className="text-3xl font-bold">Dispute Resolution</h1>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6 px-4">
        {/* Chat Window - Takes up 2 columns on large screens */}
        <div className="lg:col-span-2">
          <ChatWindow className="w-full" />
        </div>

        {/* Logs Panel */}
        <div className="space-y-6">
          {/* Agent Flow Visualization */}
          <AgentFlowVisualization />

          {/* Live Logs */}
          <LiveLogs />

          {/* Detailed Logs */}
          <DetailedLogs />
        </div>
      </div>

      {/* Footer */}
      <footer className="mt-12 pt-6 border-t text-center text-sm text-muted-foreground px-4">
        <p>Powered by OrchestrateAI</p>
        <br />
        &copy; {new Date().getFullYear()} Capgemini. All rights reserved.
      </footer>
    </main>
  );
}
