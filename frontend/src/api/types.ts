/** Short names for the types generated from docs/openapi.json (npm run types). */
import type { components } from './schema';

type Schemas = components['schemas'];
export type Me = Schemas['Me'];
export type UserRef = Schemas['UserRef'];
export type Profile = Schemas['Profile'];
export type Programme = Schemas['Programme'];
export type Post = Schemas['PostOut'];
export type PostPage = Schemas['PostPage'];
export type PostVersion = Schemas['PostVersionOut'];
export type Comment = Schemas['CommentOut'];
export type Community = Schemas['CommunityOut'];
export type Member = Schemas['MemberOut'];
export type Draft = Schemas['DraftOut'];
export type Conversation = Schemas['ConversationOut'];
export type Message = Schemas['MessageOut'];
export type Notification = Schemas['NotificationOut'];
export type Report = Schemas['ReportOut'];
export type Action = Schemas['ActionOut'];
export type Appeal = Schemas['AppealOut'];
export type SignedIn = Schemas['SignedIn'];
export type Visibility = Post['visibility'];
export type ReactionKind = Post['my_reactions'][number];
export type Reason = Report['reason'];
