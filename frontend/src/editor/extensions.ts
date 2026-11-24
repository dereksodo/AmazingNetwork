import StarterKit from '@tiptap/starter-kit';

/** Formatting that the server's allow-list keeps; everything else is switched off. */
export const richText = (options: { undoRedo?: false } = {}) =>
  StarterKit.configure({
    heading: { levels: [2, 3] },
    strike: false,
    horizontalRule: false,
    link: { openOnClick: false, protocols: ['http', 'https', 'mailto'] },
    ...options,
  });
