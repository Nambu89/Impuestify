/**
 * SessionDocUploadButton — Paperclip button for uploading session documents.
 * Accepts PDF, JPEG, PNG. Shows spinner while uploading.
 */
import { useRef } from 'react'
import { Paperclip, Loader2 } from 'lucide-react'

interface Props {
    isUploading: boolean
    disabled?: boolean
    onFileSelected: (file: File) => void
}

const ACCEPTED_TYPES = '.pdf,.jpg,.jpeg,.png'

export function SessionDocUploadButton({ isUploading, disabled, onFileSelected }: Props) {
    const inputRef = useRef<HTMLInputElement>(null)

    const handleClick = () => {
        if (!isUploading && !disabled) {
            inputRef.current?.click()
        }
    }

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) {
            onFileSelected(file)
            // Reset input so the same file can be re-uploaded if removed
            e.target.value = ''
        }
    }

    return (
        <>
            <button
                type="button"
                className="btn btn-session-doc-upload"
                onClick={handleClick}
                disabled={isUploading || disabled}
                title="Adjuntar documento (PDF, imagen)"
            >
                {isUploading ? (
                    <Loader2 size={20} className="animate-spin" />
                ) : (
                    <Paperclip size={20} />
                )}
            </button>
            <input
                ref={inputRef}
                type="file"
                accept={ACCEPTED_TYPES}
                onChange={handleChange}
                style={{ display: 'none' }}
            />
        </>
    )
}
