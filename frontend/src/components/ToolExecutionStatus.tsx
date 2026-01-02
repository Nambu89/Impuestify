/**
 * ToolExecutionStatus Component
 * 
 * Displays tool execution status (calculating, completed, error)
 */
import { Code, CheckCircle, XCircle } from 'lucide-react';
import './ThinkingIndicator.css'; // Reuse styles

interface ToolExecutionStatusProps {
    status: string;
}

export const ToolExecutionStatus = ({ status }: ToolExecutionStatusProps) => {
    if (!status) return null;

    // Determine icon and style based on status
    const isSuccess = status.includes('✅') || status.includes('completado');
    const isError = status.includes('❌') || status.includes('Error');

    const Icon = isSuccess ? CheckCircle : isError ? XCircle : Code;
    const className = `tool-status-indicator ${isSuccess ? 'success' : isError ? 'error' : ''}`;

    return (
        <div className={className}>
            <Icon className="tool-status-icon" size={14} />
            <span>{status}</span>
        </div>
    );
};