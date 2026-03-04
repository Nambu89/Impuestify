/**
 * StreamingTimeline - Visual chain-of-thought progress for AI responses
 *
 * Shows a vertical timeline of steps as the AI processes a query:
 * thinking → tool call → tool result → writing response
 *
 * Replaces the old ThinkingIndicator + ToolExecutionStatus combo.
 */
import React from 'react'
import {
    Brain,
    Wrench,
    CheckCircle2,
    XCircle,
    PenLine,
    Loader2
} from 'lucide-react'
import { TimelineStep } from '../hooks/useStreamingChat'
import './StreamingTimeline.css'

interface StreamingTimelineProps {
    steps: TimelineStep[]
}

const STEP_ICONS: Record<TimelineStep['type'], React.ReactNode> = {
    thinking: <Brain size={16} />,
    tool_call: <Wrench size={16} />,
    tool_result: <CheckCircle2 size={16} />,
    writing: <PenLine size={16} />,
}

function StepIcon({ step }: { step: TimelineStep }) {
    if (step.status === 'active') {
        return <Loader2 size={16} className="stl-spinner" />
    }
    if (step.status === 'error') {
        return <XCircle size={16} />
    }
    // For done tool_result, show checkmark
    if (step.type === 'tool_result' && step.status === 'done') {
        return <CheckCircle2 size={16} />
    }
    return STEP_ICONS[step.type] || <Brain size={16} />
}

export const StreamingTimeline: React.FC<StreamingTimelineProps> = ({ steps }) => {
    if (steps.length === 0) return null

    return (
        <div className="stl-timeline">
            {steps.map((step, i) => (
                <div
                    key={step.id}
                    className={`stl-step stl-step--${step.status} stl-step--${step.type}`}
                >
                    {/* Connector line (not on first step) */}
                    {i > 0 && <div className="stl-connector" />}

                    <div className="stl-dot">
                        <StepIcon step={step} />
                    </div>

                    <span className="stl-label">{step.label}</span>
                </div>
            ))}
        </div>
    )
}

export default StreamingTimeline
