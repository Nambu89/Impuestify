/**
 * SSE Streaming Hook for Chat
 * 
 * Handles Server-Sent Events streaming with chain-of-thought display.
 * Compatible with Railway's SSE timeout limits.
 * @version 2.0.1 - Fixed JSON parsing and onComplete callback (Jan 10, 2026)
 */
import { useState, useCallback, useRef } from 'react';

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
        console.log('🚀 [SSE] sendStreamingMessage called', { message, conversationId });

        try {
            const token = localStorage.getItem('access_token'); // ✅ FIXED: match useAuth TOKEN_KEY
            console.log('🔑 [SSE] Token found:', !!token);
            if (!token) {
                throw new Error('No authentication token found');
            }

            console.log('📡 [SSE] Fetching:', `${API_URL}/api/ask/stream`);

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

            console.log('📥 [SSE] Response received:', response.status, response.ok);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            if (!response.body) {
                throw new Error('No response body');
            }

            console.log('📖 [SSE] Getting reader from response body');

            // Read stream with TextDecoder
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let chunkCount = 0;

            console.log('🔄 [SSE] Starting read loop');

            while (true) {
                const { value, done } = await reader.read();

                if (done) {
                    console.log('✅ [SSE] Reader done after', chunkCount, 'chunks');
                    setIsStreaming(false);
                    break;
                }

                chunkCount++;
                // Decode chunk
                const decoded = decoder.decode(value, { stream: true });
                buffer += decoded;
                console.log(`📦 [SSE] Chunk ${chunkCount} received (length: ${decoded.length}):`, decoded.substring(0, 200));

                // Normalize newlines (handle \r\n and \r) and split by double newline
                const normalizedBuffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
                const messages = normalizedBuffer.split('\n\n');
                buffer = messages.pop() || ''; // Keep incomplete message in buffer

                console.log(`🔄 [SSE] Buffer split into ${messages.length} messages, remaining buffer length: ${buffer.length}`);

                for (const message of messages) {
                    const trimmedMessage = message.trim();
                    console.log('🔎 [SSE] Processing message:', JSON.stringify(trimmedMessage).substring(0, 150));

                    if (!trimmedMessage || trimmedMessage.startsWith(':')) {
                        // Skip empty messages and heartbeat comments
                        console.log('⏭️ [SSE] Skipping empty/heartbeat message');
                        continue;
                    }

                    // 🔍 DEBUG: Log raw SSE message
                    console.log('📥 RAW SSE message:', trimmedMessage);

                    // Parse SSE format: "event: eventName\ndata: eventData" (more flexible regex)
                    const eventMatch = trimmedMessage.match(/^event:\s*(\w+)/m);
                    const dataMatch = trimmedMessage.match(/^data:\s*(.*)$/ms);

                    console.log('📊 Parsed event:', eventMatch?.[1], 'data:', dataMatch?.[1]?.substring(0, 80));

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
                                    console.error('Error parsing tool_call data:', e);
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
                                    console.error('Error parsing tool_result data:', e);
                                }
                                break;

                            case 'content':
                                // Parse JSON-encoded content (remove surrounding quotes)
                                let parsedContent = eventData;
                                try {
                                    parsedContent = JSON.parse(eventData);
                                } catch {
                                    // If not valid JSON, use as-is (remove manual quotes if present)
                                    parsedContent = eventData.replace(/^"(.+)"$/s, '$1');
                                }
                                console.log('📝 Content received:', parsedContent.substring(0, 100) + '...');

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
                                console.log('✅ Stream DONE event received');
                                setIsStreaming(false);
                                // Get the final response and call callback
                                setStreamState(current => {
                                    console.log('📤 Calling onComplete with response:', current.response?.substring(0, 100));
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
            console.error('Streaming error:', error);
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