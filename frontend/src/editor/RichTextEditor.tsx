import { EditorContent, useEditor } from '@tiptap/react';
import { richText } from './extensions';
import { Toolbar } from './Toolbar';

interface Props {
  label: string;
  initial?: string;
  onChange: (html: string) => void;
}

/** TipTap editor for posts. Remount it (change `key`) to clear it. */
export function RichTextEditor({ label, initial = '', onChange }: Props) {
  const editor = useEditor({
    extensions: [richText()],
    content: initial,
    editorProps: {
      attributes: { role: 'textbox', 'aria-multiline': 'true', 'aria-label': label },
    },
    onUpdate: ({ editor: e }) => onChange(e.getHTML()),
  });
  return (
    <div className="editor">
      <Toolbar editor={editor} />
      <EditorContent editor={editor} />
    </div>
  );
}
