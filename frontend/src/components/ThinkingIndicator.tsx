/**
 * ThinkingIndicator Component
 * 
 * Displays AI "thinking" status with animated spinner,
 * similar to ChatGPT/Claude's thinking indicator.
 */
import { Loader2 } from 'lucide-react';
import './ThinkingIndicator.css';

interface ThinkingIndicatorProps {
    message: string;
}

export const ThinkingIndicator = ({ message }: ThinkingIndicatorProps) => {
    if (!message) return null;

    return (
        <div className="thinking-indicator">
            <div className="thinking-content">
                <Loader2 className="thinking-spinner" size={16} />
                <span className="thinking-text">{message}</span>
            </div>
        </div>
    );
};