import React, { Component, ReactNode } from 'react'

interface Props {
    children: ReactNode
}

interface State {
    hasError: boolean
}

class MessageErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props)
        this.state = { hasError: false }
    }

    static getDerivedStateFromError(): State {
        return { hasError: true }
    }

    componentDidCatch(error: Error, info: React.ErrorInfo) {
        console.error('[MessageErrorBoundary] Error rendering message:', error, info)
    }

    render() {
        if (this.state.hasError) {
            return (
                <p style={{ color: 'var(--color-error, #dc2626)', fontSize: '0.875rem' }}>
                    No se pudo mostrar este mensaje.
                </p>
            )
        }
        return this.props.children
    }
}

export default MessageErrorBoundary
