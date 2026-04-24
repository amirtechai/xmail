import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import { Bold, Italic, Link as LinkIcon, List, ListOrdered, Undo, Redo } from 'lucide-react'

const VARIABLES = [
  { label: '{{first_name}}', desc: 'First name' },
  { label: '{{company}}', desc: 'Company' },
  { label: '{{email}}', desc: 'Email' },
  { label: '{{unsubscribe_url}}', desc: 'Unsubscribe link' },
]

interface Props {
  html: string
  onChange: (html: string, text: string) => void
  placeholder?: string
}

export default function RichEditor({ html, onChange, placeholder = 'Write your email body…' }: Props) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Link.configure({ openOnClick: false }),
      Placeholder.configure({ placeholder }),
    ],
    content: html,
    onUpdate: ({ editor }) => {
      onChange(editor.getHTML(), editor.getText())
    },
  })

  if (!editor) return null

  const btn = (active: boolean, onClick: () => void, title: string, children: React.ReactNode) => (
    <button
      type="button"
      title={title}
      onMouseDown={(e) => { e.preventDefault(); onClick() }}
      className={`p-1.5 rounded transition-colors ${
        active
          ? 'bg-accent-yellow/20 text-accent-yellow'
          : 'text-text-muted hover:text-text-primary hover:bg-bg-hover'
      }`}
    >
      {children}
    </button>
  )

  const setLink = () => {
    const url = window.prompt('URL:', editor.getAttributes('link').href ?? '')
    if (url === null) return
    if (url === '') {
      editor.chain().focus().extendMarkRange('link').unsetLink().run()
    } else {
      editor.chain().focus().extendMarkRange('link').setLink({ href: url }).run()
    }
  }

  const insertVar = (v: string) => {
    editor.chain().focus().insertContent(v).run()
  }

  return (
    <div className="border border-border rounded-md overflow-hidden">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center gap-0.5 px-2 py-1.5 border-b border-border bg-bg-secondary">
        {btn(editor.isActive('bold'), () => editor.chain().focus().toggleBold().run(), 'Bold', <Bold className="w-3.5 h-3.5" />)}
        {btn(editor.isActive('italic'), () => editor.chain().focus().toggleItalic().run(), 'Italic', <Italic className="w-3.5 h-3.5" />)}
        {btn(editor.isActive('bulletList'), () => editor.chain().focus().toggleBulletList().run(), 'Bullet list', <List className="w-3.5 h-3.5" />)}
        {btn(editor.isActive('orderedList'), () => editor.chain().focus().toggleOrderedList().run(), 'Numbered list', <ListOrdered className="w-3.5 h-3.5" />)}
        {btn(editor.isActive('link'), setLink, 'Insert link', <LinkIcon className="w-3.5 h-3.5" />)}
        <div className="w-px h-4 bg-border mx-1" />
        {btn(false, () => editor.chain().focus().undo().run(), 'Undo', <Undo className="w-3.5 h-3.5" />)}
        {btn(false, () => editor.chain().focus().redo().run(), 'Redo', <Redo className="w-3.5 h-3.5" />)}
        <div className="w-px h-4 bg-border mx-1" />
        <span className="text-xs text-text-muted mr-1">Insert:</span>
        {VARIABLES.map((v) => (
          <button
            key={v.label}
            type="button"
            title={v.desc}
            onMouseDown={(e) => { e.preventDefault(); insertVar(v.label) }}
            className="text-xs px-1.5 py-0.5 rounded bg-bg-tertiary text-accent-yellow hover:bg-accent-yellow/10 font-mono"
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* Editor area */}
      <EditorContent
        editor={editor}
        className="prose prose-invert prose-sm max-w-none min-h-[200px] px-3 py-2 text-text-primary text-sm focus:outline-none [&_.ProseMirror]:outline-none [&_.ProseMirror]:min-h-[200px] [&_.ProseMirror_p.is-editor-empty:first-child]:before:content-[attr(data-placeholder)] [&_.ProseMirror_p.is-editor-empty:first-child]:before:text-text-muted [&_.ProseMirror_p.is-editor-empty:first-child]:before:float-left [&_.ProseMirror_p.is-editor-empty:first-child]:before:pointer-events-none"
      />
    </div>
  )
}
