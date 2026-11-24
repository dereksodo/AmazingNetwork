import { useState } from 'react';
import { api } from '../api/client';
import type { Community, Post, Visibility } from '../api/types';
import { RichTextEditor } from '../editor/RichTextEditor';
import { useAction } from '../hooks';
import { ErrorNote, Field } from './basics';

/** Write a post or, in a community, a discussion. */
export function Composer({ community }: { community?: Community }) {
  const [round, setRound] = useState(0);
  const [html, setHtml] = useState('');
  const [title, setTitle] = useState('');
  const [visibility, setVisibility] = useState<Visibility>(community ? 'community' : 'campus');
  const [comments, setComments] = useState(true);
  const [image, setImage] = useState<File>();
  const [alt, setAlt] = useState('');
  const { run, error, busy } = useAction();

  const publish = async () => {
    const post = await api.post<Post>('/posts', {
      type: community && title ? 'discussion' : 'post',
      community_id: community?.id ?? null,
      visibility,
      title: title || null,
      body_html: html,
      comments_enabled: comments,
    });
    if (image) {
      const form = new FormData();
      form.append('file', image);
      form.append('alt_text', alt);
      await api.post(`/posts/${post.id}/images`, form);
    }
    setHtml('');
    setTitle('');
    setImage(undefined);
    setAlt('');
    setRound(round + 1);
  };

  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        void run(publish);
      }}
    >
      <h2>New post</h2>
      {community && (
        <Field label="Title (makes it a discussion)">
          <input value={title} maxLength={120} onChange={(e) => setTitle(e.target.value)} />
        </Field>
      )}
      <RichTextEditor key={round} label="Post text" onChange={setHtml} />
      <div className="row">
        <Field label="Who can see it">
          <select value={visibility} onChange={(e) => setVisibility(e.target.value as Visibility)}>
            <option value="campus">Campus</option>
            {community ? (
              <option value="community">Members of {community.name}</option>
            ) : (
              <option value="followers">My followers</option>
            )}
          </select>
        </Field>
        <Field label="Image (optional)">
          <input
            key={round}
            type="file"
            accept="image/png,image/jpeg,image/gif,image/webp"
            onChange={(e) => setImage(e.target.files?.[0])}
          />
        </Field>
        {image && (
          <Field label="Image description">
            <input required value={alt} maxLength={200} onChange={(e) => setAlt(e.target.value)} />
          </Field>
        )}
        <label>
          <input
            type="checkbox"
            checked={comments}
            onChange={(e) => setComments(e.target.checked)}
          />{' '}
          Allow comments
        </label>
        <button disabled={busy}>Publish</button>
      </div>
      <ErrorNote message={error} />
    </form>
  );
}
