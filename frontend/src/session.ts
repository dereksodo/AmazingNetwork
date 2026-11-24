import { createContext, useContext } from 'react';
import type { Me } from './api/types';

export interface SessionValue {
  me: Me;
  reload: () => Promise<void>;
  signOut: () => Promise<void>;
}

export const SessionContext = createContext<SessionValue | null>(null);

/** The signed-in user. */
export const useSession = () => useContext(SessionContext)!;
