# Frontend

React, TypeScript and Vite (container C-WEB). The editor is TipTap; drafts are shared with Yjs.

| Feature                      | Where                                                                                |
| ---------------------------- | ------------------------------------------------------------------------------------ |
| Routes, navigation, session  | `src/App.tsx`, `src/session.ts`                                                      |
| REST calls and types         | `src/api/client.ts`, `types.ts`; `schema.d.ts` is generated from `docs/openapi.json` |
| Live events and reconnection | `src/live/LiveProvider.tsx`                                                          |
| Rich-text editor             | `src/editor/RichTextEditor.tsx`, `Toolbar.tsx`, `extensions.ts`                      |
| Co-editing                   | `src/editor/DraftConnection.ts` (protocol), `CollaborativeEditor.tsx`                |
| Posts, events, reporting     | `src/components/`                                                                    |
| One file per page            | `src/pages/`                                                                         |

Rules live in the backend; the frontend only hides buttons. Server HTML is shown only by `RichText`, after the backend's allow-list cleaned it.

```bash
npm run dev
```

```bash
npm run format && npm run lint && npm run build
```

After the API changed:

```bash
npm run types
```
