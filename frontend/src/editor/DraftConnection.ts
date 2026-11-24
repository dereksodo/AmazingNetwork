/** Yjs over /ws/drafts/{id}: sends local changes, applies remote ones, survives disconnections. */
import { applyAwarenessUpdate, Awareness, encodeAwarenessUpdate } from 'y-protocols/awareness';
import * as Y from 'yjs';
import { session } from '../api/client';
import type { UserRef } from '../api/types';

export interface DraftState {
  status: 'connecting' | 'online' | 'offline' | 'refused' | 'published';
  version: number;
  saved: boolean;
  people: Pick<UserRef, 'id' | 'display_name'>[];
  postId?: number;
}

const encode = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes));
const decode = (text: string) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

export class DraftConnection {
  readonly doc = new Y.Doc();
  readonly awareness = new Awareness(this.doc);
  private socket!: WebSocket;
  private unacknowledged = 0;
  private retryMs = 1000;
  private timer = 0;
  private stopped = false;
  private state: DraftState = { status: 'connecting', version: 0, saved: true, people: [] };

  constructor(
    private draftId: number,
    private onState: (state: DraftState) => void,
  ) {
    this.doc.on('update', (update: Uint8Array, origin: unknown) => {
      if (origin !== this) this.sendUpdate(update);
    });
    this.awareness.on('update', (_: unknown, origin: unknown) => {
      if (origin !== this) this.sendAwareness();
    });
  }

  start = () => {
    this.stopped = false;
    const socket = new WebSocket(
      `${location.origin.replace('http', 'ws')}/ws/drafts/${this.draftId}`,
    );
    this.socket = socket;
    const heartbeat = window.setInterval(() => this.send({ type: 'ping' }), 25000);
    socket.onopen = () => {
      this.send({ type: 'auth', token: session.token });
      this.send({ type: 'sync', state_vector: encode(Y.encodeStateVector(this.doc)) });
    };
    socket.onmessage = ({ data }) => this.receive(JSON.parse(data));
    socket.onclose = ({ code }) => {
      clearInterval(heartbeat);
      if (this.stopped || socket !== this.socket) return;
      if (code === 4401 || code === 4403) return this.set({ status: 'refused', people: [] });
      if (code === 4409) return this.set({ status: 'published', people: [] });
      this.set({ status: 'offline', people: [] });
      this.timer = window.setTimeout(this.start, this.retryMs);
      this.retryMs = Math.min(this.retryMs * 2, 30000);
    };
  };

  stop = () => {
    this.stopped = true;
    clearTimeout(this.timer);
    this.socket.close();
  };

  private set(change: Partial<DraftState>) {
    this.state = { ...this.state, ...change };
    this.onState(this.state);
  }

  private send(frame: object) {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify(frame));
  }

  /** Changes made offline stay in the document and are sent after the next sync. */
  private sendUpdate(update: Uint8Array) {
    this.set({ saved: false });
    if (this.state.status !== 'online') return;
    this.unacknowledged += 1;
    this.send({ type: 'update', update: encode(update) });
  }

  private sendAwareness() {
    const update = encodeAwarenessUpdate(this.awareness, [this.doc.clientID]);
    this.send({ type: 'awareness', update: encode(update) });
  }

  private receive(frame: {
    type: string;
    update: string;
    state_vector: string;
    version: number;
    users: DraftState['people'];
    post_id: number;
  }) {
    if (frame.type === 'sync') {
      Y.applyUpdate(this.doc, decode(frame.update), this);
      this.retryMs = 1000;
      this.unacknowledged = 0;
      const serverState = decode(frame.state_vector);
      const missing = Y.encodeStateAsUpdate(this.doc, serverState);
      this.set({ status: 'online', version: frame.version, saved: true });
      // An update without content is two zero bytes.
      if (missing.length > 2) this.sendUpdate(missing);
      this.sendAwareness();
    } else if (frame.type === 'update') {
      Y.applyUpdate(this.doc, decode(frame.update), this);
      this.set({ version: frame.version });
    } else if (frame.type === 'ack') {
      this.unacknowledged -= 1;
      this.set({ version: frame.version, saved: this.unacknowledged === 0 });
    } else if (frame.type === 'awareness') {
      applyAwarenessUpdate(this.awareness, decode(frame.update), this);
    } else if (frame.type === 'presence') {
      this.set({ people: frame.users });
      this.sendAwareness();
    } else if (frame.type === 'published') {
      this.set({ status: 'published', postId: frame.post_id });
    }
  }
}
