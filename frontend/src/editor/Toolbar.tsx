import { useEditorState, type Editor } from '@tiptap/react';

/** Formatting buttons. Every command also has TipTap's keyboard shortcut. */
export function Toolbar({ editor }: { editor: Editor }) {
  const active = useEditorState({
    editor,
    selector: ({ editor: e }) => ({
      bold: e.isActive('bold'),
      italic: e.isActive('italic'),
      underline: e.isActive('underline'),
      h2: e.isActive('heading', { level: 2 }),
      h3: e.isActive('heading', { level: 3 }),
      bullets: e.isActive('bulletList'),
      numbers: e.isActive('orderedList'),
      quote: e.isActive('blockquote'),
      code: e.isActive('codeBlock'),
      link: e.isActive('link'),
    }),
  });
  const chain = () => editor.chain().focus();
  const setLink = () => {
    const href = prompt('Link address (http, https or mailto). Leave empty to remove the link.');
    if (href) chain().extendMarkRange('link').setLink({ href }).run();
    else chain().unsetLink().run();
  };
  const buttons: [string, string, boolean, () => void][] = [
    ['B', 'Bold', active.bold, () => chain().toggleBold().run()],
    ['I', 'Italic', active.italic, () => chain().toggleItalic().run()],
    ['U', 'Underline', active.underline, () => chain().toggleUnderline().run()],
    ['H2', 'Heading', active.h2, () => chain().toggleHeading({ level: 2 }).run()],
    ['H3', 'Subheading', active.h3, () => chain().toggleHeading({ level: 3 }).run()],
    ['• List', 'Bullet list', active.bullets, () => chain().toggleBulletList().run()],
    ['1. List', 'Numbered list', active.numbers, () => chain().toggleOrderedList().run()],
    ['❝', 'Quote', active.quote, () => chain().toggleBlockquote().run()],
    ['</>', 'Code', active.code, () => chain().toggleCodeBlock().run()],
    ['Link', 'Link', active.link, setLink],
  ];
  return (
    <div className="toolbar" role="toolbar" aria-label="Formatting">
      {buttons.map(([text, label, pressed, act]) => (
        <button
          key={label}
          type="button"
          aria-label={`${text} ${label}`}
          aria-pressed={pressed}
          onClick={act}
        >
          {text}
        </button>
      ))}
    </div>
  );
}
