import Collaboration from '@tiptap/extension-collaboration';
import CollaborationCaret from '@tiptap/extension-collaboration-caret';
import { EditorContent, useEditor } from '@tiptap/react';
import { useEffect } from 'react';
import { useSession } from '../session';
import type { DraftConnection } from './DraftConnection';
import { richText } from './extensions';
import { Toolbar } from './Toolbar';

const COLOURS = ['#b5174e', '#0f6b5c', '#7a4a00', '#4527a0'];

/** TipTap bound to a shared Yjs document, with the other editors' cursors. */
export function CollaborativeEditor({
  connection,
  editable,
}: {
  connection: DraftConnection;
  editable: boolean;
}) {
  const { me } = useSession();
  const editor = useEditor({
    extensions: [
      richText({ undoRedo: false }),
      Collaboration.configure({ document: connection.doc }),
      CollaborationCaret.configure({
        provider: connection,
        user: { name: me.display_name, color: COLOURS[me.id % COLOURS.length] },
      }),
    ],
    editorProps: {
      attributes: { role: 'textbox', 'aria-multiline': 'true', 'aria-label': 'Draft text' },
    },
  });
  useEffect(() => {
    editor.setEditable(editable);
  }, [editor, editable]);
  return (
    <div className="editor tall">
      <Toolbar editor={editor} />
      <EditorContent editor={editor} />
    </div>
  );
}
