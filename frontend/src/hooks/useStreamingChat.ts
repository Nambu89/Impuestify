/**
 * SSE Streaming Hook for Chat
 *
 * Handles Server-Sent Events streaming with chain-of-thought display
 * and real-time token-by-token content streaming.
 * Compatible with Railway's SSE timeout limits.
 *
 * Uses eventsource-parser for spec-compliant SSE parsing (handles
 * multi-line data fields, partial chunks, heartbeats, etc.)
 *
 * @version 3.1.0 - eventsource-parser + AsyncOpenAI streaming fix (Mar 2026)
 */
import { useState, useCallback, useRef } from 'react';
import { createParser, type EventSourceMessage } from 'eventsource-parser';
import { logger } from '../utils/logger';

// Use environment variable for API URL (needed for production)
const API_URL = import.meta.env.VITE_API_URL || '/api';

/** A single step in the chain-of-thought timeline */
export interface TimelineStep {
    id: string;
    type: 'thinking' | 'tool_call' | 'tool_result' | 'writing';
    label: string;
    status: 'active' | 'done' | 'error';
    timestamp: number;
}

interface StreamState {
    thinking: string;
    toolStatus: string;
    response: string;
    isDone: boolean;
    error: string | null;
    /** Chain-of-thought timeline steps */
    steps: TimelineStep[];
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
        callbacks?: StreamCallbacks,
        workspaceId?: string,
        sessionDocIds?: string[]
    ) => Promise<void>;
    cancelStream: () => void;
    resetStream: () => void;
}

/** Helper: add or update a step in the timeline */
function upsertStep(steps: TimelineStep[], step: TimelineStep): TimelineStep[] {
    const existing = steps.findIndex(s => s.id === step.id);
    if (existing >= 0) {
        const updated = [...steps];
        updated[existing] = step;
        return updated;
    }
    // Mark previous active steps as done (except tool_call waiting for result)
    const updated = steps.map(s =>
        s.status === 'active' && s.type !== 'tool_call' ? { ...s, status: 'done' as const } : s
    );
    return [...updated, step];
}

export const useStreamingChat = (): UseStreamingChatReturn => {
    const [streamState, setStreamState] = useState<StreamState>({
        thinking: '',
        toolStatus: '',
        response: '',
        isDone: false,
        error: null,
        steps: []
    });

    const [isStreaming, setIsStreaming] = useState(false);
    const eventSourceRef = useRef<EventSource | null>(null);
    // Accumulator ref for content_chunk events (avoids stale closure issues)
    const responseAccRef = useRef('');

    const cancelStream = useCallback(() => {
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
            setIsStreaming(false);
        }
    }, []);

    const resetStream = useCallback(() => {
        responseAccRef.current = '';
        setStreamState({
            thinking: '',
            toolStatus: '',
            response: '',
            isDone: false,
            error: null,
            steps: []
        });
        setIsStreaming(false);
    }, []);

    const sendStreamingMessage = useCallback(async (
        message: string,
        conversationId?: string,
        callbacks?: StreamCallbacks,
        workspaceId?: string,
        sessionDocIds?: string[]
    ) => {
        // Reset state with immediate "processing" feedback
        responseAccRef.current = '';
        setStreamState({
            thinking: '',
            toolStatus: '',
            response: '',
            isDone: false,
            error: null,
            steps: [{
                id: 'connecting',
                type: 'thinking',
                label: 'Procesando tu consulta...',
                status: 'active',
                timestamp: Date.now()
            }]
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
                    conversation_id: conversationId,
                    workspace_id: workspaceId || null,
                    session_doc_ids: sessionDocIds?.length ? sessionDocIds : null
                })
            });

            logger.debug('SSE Response received:', response.status);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            if (!response.body) {
                throw new Error('No response body');
            }

            // Read stream with eventsource-parser for spec-compliant SSE parsing
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let stepCounter = 0;

            // Process a parsed SSE event
            const handleEvent = (event: EventSourceMessage) => {
                const eventType = event.event || 'message';
                const eventData = event.data.trim();

                switch (eventType) {
                    case 'thinking': {
                        const thinkingText = eventData.replace(/^"(.+)"$/, '$1');
                        const stepId = `thinking-${++stepCounter}`;
                        setStreamState(prev => ({
                            ...prev,
                            thinking: thinkingText,
                            steps: upsertStep(prev.steps, {
                                id: stepId,
                                type: 'thinking',
                                label: thinkingText,
                                status: 'active',
                                timestamp: Date.now()
                            })
                        }));
                        break;
                    }

                    case 'tool_call': {
                        try {
                            const toolData = JSON.parse(eventData);
                            const displayName = toolData.display_name || toolData.tool;
                            const stepId = `tool-${toolData.tool}`;
                            setStreamState(prev => ({
                                ...prev,
                                thinking: '',
                                toolStatus: displayName,
                                steps: upsertStep(
                                    prev.steps.map(s =>
                                        s.type === 'thinking' && s.status === 'active'
                                            ? { ...s, status: 'done' as const }
                                            : s
                                    ),
                                    {
                                        id: stepId,
                                        type: 'tool_call',
                                        label: displayName,
                                        status: 'active',
                                        timestamp: Date.now()
                                    }
                                )
                            }));
                        } catch (e) {
                            logger.error('Error parsing tool_call data:', e);
                        }
                        break;
                    }

                    case 'tool_result': {
                        try {
                            const resultData = JSON.parse(eventData);
                            const doneName = resultData.done_name || resultData.display_name || resultData.tool;
                            const displayName = resultData.display_name || resultData.tool;
                            const stepId = `tool-${resultData.tool}`;
                            setStreamState(prev => ({
                                ...prev,
                                toolStatus: resultData.success
                                    ? doneName
                                    : `Error en ${displayName}`,
                                steps: upsertStep(prev.steps, {
                                    id: stepId,
                                    type: 'tool_result',
                                    label: resultData.success
                                        ? doneName
                                        : `Error en ${displayName}`,
                                    status: resultData.success ? 'done' : 'error',
                                    timestamp: Date.now()
                                })
                            }));
                        } catch (e) {
                            logger.error('Error parsing tool_result data:', e);
                        }
                        break;
                    }

                    case 'content_chunk': {
                        // Token-by-token streaming: APPEND to accumulator
                        let chunkText = eventData;
                        try {
                            chunkText = JSON.parse(chunkText);
                        } catch {
                            chunkText = chunkText.replace(/^"(.+)"$/s, '$1');
                        }

                        responseAccRef.current += chunkText;
                        const currentAcc = responseAccRef.current;

                        setStreamState(prev => {
                            // On first chunk, add a "writing" step and clear thinking
                            let newSteps = prev.steps;
                            if (!prev.response) {
                                newSteps = upsertStep(
                                    prev.steps.map(s =>
                                        s.status === 'active' ? { ...s, status: 'done' as const } : s
                                    ),
                                    {
                                        id: 'writing',
                                        type: 'writing',
                                        label: 'Escribiendo respuesta',
                                        status: 'active',
                                        timestamp: Date.now()
                                    }
                                );
                            }
                            return {
                                ...prev,
                                thinking: '',
                                toolStatus: '',
                                response: currentAcc,
                                steps: newSteps
                            };
                        });
                        break;
                    }

                    case 'content': {
                        // Full content replacement (final authoritative version)
                        let parsedContent = eventData;

                        try {
                            parsedContent = JSON.parse(parsedContent);
                        } catch {
                            parsedContent = parsedContent.replace(/^"(.+)"$/s, '$1');
                        }

                        // Replace accumulated response with authoritative final content
                        responseAccRef.current = parsedContent;

                        setStreamState(prev => ({
                            ...prev,
                            thinking: '',
                            toolStatus: '',
                            response: parsedContent,
                            steps: prev.steps.map(s =>
                                s.status === 'active' ? { ...s, status: 'done' as const } : s
                            )
                        }));
                        break;
                    }

                    case 'done':
                        logger.debug('Stream DONE event received');
                        setIsStreaming(false);
                        // Get the final response and call callback
                        setStreamState(current => {
                            if (callbacks?.onComplete && current.response) {
                                callbacks.onComplete(current.response, conversationId);
                            }
                            return {
                                ...current,
                                isDone: true,
                                steps: current.steps.map(s =>
                                    s.status === 'active' ? { ...s, status: 'done' as const } : s
                                )
                            };
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
            };

            // Create spec-compliant SSE parser (handles multi-line data,
            // partial chunks, comments/heartbeats, retry fields, etc.)
            const parser = createParser({
                onEvent: handleEvent
            });

            // Feed raw bytes into the parser
            while (true) {
                const { value, done } = await reader.read();

                if (done) {
                    logger.debug('SSE Reader done');
                    setIsStreaming(false);
                    break;
                }

                // Feed decoded text to eventsource-parser
                parser.feed(decoder.decode(value, { stream: true }));
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
