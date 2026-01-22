/**
 * SSE Streaming Hook for Chat
 *
 * Handles Server-Sent Events streaming with chain-of-thought display.
 * Compatible with Railway's SSE timeout limits.
 * @version 2.0.2 - Cleaned up debug logs (Jan 20, 2026)
 */
import { useState, useCallback, useRef } from 'react';
import { logger } from '../utils/logger';

// ✅ FIX: Use environment variable for API URL (needed for production)
const API_URL = import.meta.env.VITE_API_URL || '/api';

interface StreamState {
    thinking: string;
    toolStatus: string;
    response: string;
    isDone: boolean;
    error: string | null;
}

interface StreamCallbacks {
    onComplete?: (response: string, conversationId?: string) => void;
    onError?: (error: string) => void;
}

interface UseStreamingChatReturn {
    streamState: StreamState;
    isStreaming: boolean;
    sendStreamingMessage: (
        message: string,
        conversationId?: string,
        callbacks?: StreamCallbacks
    ) => Promise<void>;
    cancelStream: () => void;
    resetStream: () => void;
}

export const useStreamingChat = (): UseStreamingChatReturn => {
    const [streamState, setStreamState] = useState<StreamState>({
        thinking: '',
        toolStatus: '',
        response: '',
        isDone: false,
        error: null
    });

    const [isStreaming, setIsStreaming] = useState(false);
    const eventSourceRef = useRef<EventSource | null>(null);

    const cancelStream = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
            setIsStreaming(false);
        }
    }, []);

    const resetStream = useCallback(() => {
        setStreamState({
            thinking: '',
            toolStatus: '',
            response: '',
            isDone: false,
            error: null
        });
        setIsStreaming(false);
    }, []);

    const sendStreamingMessage = useCallback(async (
        message: string,
        conversationId?: string,
        callbacks?: StreamCallbacks
    ) => {
        // Reset state
        setStreamState({
            thinking: '',
            toolStatus: '',
            response: '',
            isDone: false,
            error: null
        });

        setIsStreaming(true);
        logger.debug('SSE sendStreamingMessage called', { message: message.substring(0, 50), conversationId });

        try {
            const token = localStorage.getItem('access_token');
            if (!token) {
                throw new Error('No authentication token found');
            }

            logger.debug('SSE Fetching stream endpoint');

            // Using fetch with streaming (better for auth)
            const response = await fetch(`${API_URL}/api/ask/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    question: message,
                    conversation_id: conversationId
                })
            });

            logger.debug('SSE Response received:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            if (!response.body) {
                throw new Error('No response body');
            }

            // Read stream with TextDecoder
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let chunkCount = 0;

            while (true) {
                const { value, done } = await reader.read();

                if (done) {
                    logger.debug('SSE Reader done after', chunkCount, 'chunks');
                    setIsStreaming(false);
                    break;
                }

                chunkCount++;
                // Decode chunk
                const decoded = decoder.decode(value, { stream: true });
                buffer += decoded;

                // Normalize newlines (handle \r\n and \r) and split by double newline
                const normalizedBuffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
                const messages = normalizedBuffer.split('\n\n');
                buffer = messages.pop() || ''; // Keep incomplete message in buffer

                for (const message of messages) {
                    const trimmedMessage = message.trim();

                    if (!trimmedMessage || trimmedMessage.startsWith(':')) {
                        // Skip empty messages and heartbeat comments
                        continue;
                    }

                    // Parse SSE format: "event: eventName\ndata: eventData" (more flexible regex)
                    const eventMatch = trimmedMessage.match(/^event:\s*(\w+)/m);
                    const dataMatch = trimmedMessage.match(/^data:\s*(.*)$/ms);

                    if (eventMatch && dataMatch) {
                        const eventType = eventMatch[1];
                        const eventData = dataMatch[1].trim();

                        switch (eventType) {
                            case 'thinking':
                                setStreamState(prev => ({
                                    ...prev,
                                    thinking: eventData.replace(/^"(.+)"$/, '$1') // Remove quotes
                                }));
                                break;

                            case 'tool_call':
                                try {
                                    const toolData = JSON.parse(eventData);
                                    setStreamState(prev => ({
                                        ...prev,
                                        toolStatus: `🔢 Ejecutando ${toolData.tool}...`
                                    }));
                                } catch (e) {
                                    logger.error('Error parsing tool_call data:', e);
                                }
                                break;

                            case 'tool_result':
                                try {
                                    const resultData = JSON.parse(eventData);
                                    setStreamState(prev => ({
                                        ...prev,
                                        toolStatus: resultData.success
                                            ? '✅ Cálculo completado'
                                            : '❌ Error en cálculo'
                                    }));

                                    // Clear tool status after 2 seconds
                                    setTimeout(() => {
                                        setStreamState(prev => ({
                                            ...prev,
                                            toolStatus: ''
                                        }));
                                    }, 2000);
                                } catch (e) {
                                    logger.error('Error parsing tool_result data:', e);
                                }
                                break;

                            case 'content':
                                // Parse JSON-encoded content (remove surrounding quotes)
                                // Also remove any "data:" prefixes that might be in multi-line content
                                let parsedContent = eventData;

                                // First, remove all "data:" prefixes from multi-line content
                                parsedContent = parsedContent.replace(/^data:\s*/gm, '');

                                // Try to parse as JSON
                                try {
                                    parsedContent = JSON.parse(parsedContent);
                                } catch {
                                    // If not valid JSON, use as-is (remove manual quotes if present)
                                    parsedContent = parsedContent.replace(/^"(.+)"$/s, '$1');
                                }

                                // Final cleanup: remove any remaining "data:" that might be in the text
                                parsedContent = parsedContent.replace(/\ndata:\s*/g, '\n');

                                // Use functional update and store in accumulator
                                setStreamState(prev => {
                                    const newResponse = parsedContent; // Replace, don't append (content is full response)
                                    return {
                                        ...prev,
                                        thinking: '', // Clear thinking when content arrives
                                        response: newResponse
                                    };
                                });
                                break;

                            case 'done':
                                logger.debug('Stream DONE event received');
                                setIsStreaming(false);
                                // Get the final response and call callback
                                setStreamState(current => {
                                    if (callbacks?.onComplete && current.response) {
                                        callbacks.onComplete(current.response, conversationId);
                                    }
                                    return { ...current, isDone: true };
                                });
                                break;

                            case 'error':
                                setStreamState(prev => ({
                                    ...prev,
                                    error: eventData
                                }));
                                setIsStreaming(false);
                                if (callbacks?.onError) {
                                    callbacks.onError(eventData);
                                }
                                break;
                        }
                    }
                }
            }

        } catch (error) {
            logger.error('Streaming error:', error);
            const errorMsg = error instanceof Error ? error.message : 'Unknown error';
            setStreamState(prev => ({
                ...prev,
                error: errorMsg
            }));
            setIsStreaming(false);
            if (callbacks?.onError) {
                callbacks.onError(errorMsg);
            }
        }
    }, []);

    return {
        streamState,
        isStreaming,
        sendStreamingMessage,
        cancelStream,
        resetStream
    };
};