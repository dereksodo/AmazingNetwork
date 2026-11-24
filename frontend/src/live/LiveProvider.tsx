/** One WebSocket to /ws per tab: live events, subscriptions and reconnection. */
import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from 'react';
import { session } from '../api/client';

export interface LiveEvent {
  channel: string;
  event: string;
  data: { post_id?: number; community_id?: number | null; conversation_id?: number };
}
type Listener = (event: LiveEvent) => void;

class LiveConnection {
  private socket!: WebSocket;
  private retryMs = 1000;
  private timer = 0;
  private stopped = false;
  private listeners = new Map<string, Set<Listener>>();

  constructor(
    private onOnline: (online: boolean) => void,
    private onSignedOut: () => void,
  ) {}

  start = () => {
    this.stopped = false;
    const socket = new WebSocket(`${location.origin.replace('http', 'ws')}/ws`);
    this.socket = socket;
    const heartbeat = window.setInterval(() => this.send({ type: 'ping' }), 25000);
    socket.onopen = () => this.send({ type: 'auth', token: session.token });
    socket.onmessage = ({ data }) => this.receive(JSON.parse(data));
    socket.onclose = ({ code }) => {
      clearInterval(heartbeat);
      if (this.stopped || socket !== this.socket) return;
      this.onOnline(false);
      if (code === 4401) return this.onSignedOut();
      this.timer = window.setTimeout(this.start, this.retryMs);
      this.retryMs = Math.min(this.retryMs * 2, 30000);
    };
  };

  stop = () => {
    this.stopped = true;
    clearTimeout(this.timer);
    this.socket.close();
  };

  listen(channel: string, listener: Listener) {
    if (!this.listeners.has(channel)) {
      this.listeners.set(channel, new Set());
      this.send({ type: 'subscribe', channel });
    }
    this.listeners.get(channel)!.add(listener);
    return () => {
      const remaining = this.listeners.get(channel)!;
      remaining.delete(listener);
      if (remaining.size === 0) {
        this.listeners.delete(channel);
        this.send({ type: 'unsubscribe', channel });
      }
    };
  }

  private send(frame: object) {
    if (this.socket?.readyState === WebSocket.OPEN) this.socket.send(JSON.stringify(frame));
  }

  private receive(frame: { type: string } & LiveEvent) {
    if (frame.type === 'ready') {
      this.retryMs = 1000;
      this.onOnline(true);
      // Events sent while we were away are lost, so every view reloads over REST.
      for (const [channel, listeners] of this.listeners) {
        this.send({ type: 'subscribe', channel });
        listeners.forEach((l) => l({ channel, event: 'resync', data: {} }));
      }
    } else if (frame.type === 'event' || frame.type === 'revoked') {
      const event = frame.type === 'event' ? frame : { ...frame, event: 'revoked', data: {} };
      this.listeners.get(frame.channel)?.forEach((l) => l(event));
    }
  }
}

const Context = createContext<LiveConnection | null>(null);

export function LiveProvider({
  onSignedOut,
  children,
}: {
  onSignedOut: () => void;
  children: ReactNode;
}) {
  const [online, setOnline] = useState(true);
  const [connection] = useState(() => new LiveConnection(setOnline, onSignedOut));
  useEffect(() => {
    connection.start();
    return connection.stop;
  }, [connection]);
  return (
    <Context value={connection}>
      {!online && (
        <p className="banner warning" role="status">
          Live updates paused. Reconnecting…
        </p>
      )}
      {children}
    </Context>
  );
}

/** Call the listener for each event on a channel ("resync" after a reconnect, "revoked" on lost access). */
export function useLive(channel: string, listener: Listener) {
  const connection = useContext(Context)!;
  const latest = useRef(listener);
  useEffect(() => {
    latest.current = listener;
  });
  useEffect(
    () => connection.listen(channel, (event) => latest.current(event)),
    [connection, channel],
  );
}
