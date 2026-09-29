// Shared TypeScript types mirroring the backend schemas (§68).

export type DebateMode = 'local' | 'online'
export type DebateStatus =
  | 'draft' | 'open' | 'active' | 'voting' | 'closing_soon' | 'closed'
  | 'being_verified' | 'settled' | 'draw' | 'disputed'
  | 'cancelled' | 'under_review'
export type Side = 'a' | 'b'
export type VoteChoice = 'side_a' | 'side_b' | 'draw'
export type UserRole = 'user' | 'moderator' | 'admin'

export interface User {
  id: string
  username: string
  email: string
  role: UserRole
  status: string
  email_verified: boolean
  country_code?: string | null
  created_at: string
  profile?: Profile | null
}

export interface Profile {
  display_name?: string | null
  avatar_url?: string | null
  bio?: string | null
  favorite_categories?: string | null
  debates_created: number
  debates_participated: number
  wins: number
  losses: number
  draws: number
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface DebateRules {
  required_voters: number
  votes_public: boolean
  allow_draw: boolean
  allow_vote_change: boolean
  venue?: string | null
  city?: string | null
  country?: string | null
  meeting_link?: string | null
  expose_address: boolean
  settlement_source?: string | null
  settlement_rule?: string | null
  event_date?: string | null
  id?: string
}

export interface Participant {
  id: string
  user_id?: string | null
  role: 'creator' | 'challenger' | 'voter'
  side?: Side | null
  confirmed: boolean
  username?: string | null
}

export interface VoteCounts {
  side_a: number
  side_b: number
  draw: number
  side_a_pct: number
  side_b_pct: number
  draw_pct: number
  total: number
  required: number
  revealed: boolean
}

export interface Voter {
  username: string
  display_name?: string | null
  avatar_url?: string | null
}

export interface VotersPage {
  total: number
  voters: Voter[]
  identities_public: boolean
}

export interface DebateBrief {
  id: string
  mode: DebateMode
  status: DebateStatus
  question: string
  side_a_label: string
  side_b_label: string
  timezone: string
  start_at?: string | null
  end_at?: string | null
  views: number
  winner_side?: string | null
  category_name?: string | null
  participants_count: number
  votes_count: number
  required_voters: number
  settlement_source?: string | null
  venue_city?: string | null
}

export interface DebateDetail extends DebateBrief {
  is_public: boolean
  locked_at?: string | null
  settled_at?: string | null
  result_summary?: string | null
  shares: number
  comments_count: number
  rules?: DebateRules | null
  participants: Participant[]
  vote_tally?: VoteCounts | null
  my_side?: Side | null
  my_role?: 'creator' | 'challenger' | 'voter' | null
  has_voted?: VoteChoice | null
}

export interface Category {
  id: string
  name: string
  slug: string
  icon?: string | null
}

export interface Notification {
  id: string
  title: string
  body: string
  category: string
  channel: string
  link?: string | null
  read: boolean
  created_at: string
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface ApiError {
  error: { code: string; message: string; context?: Record<string, unknown> | null }
}

// --- Games (§6, §7, §8) ---

export type GameStatus = 'waiting' | 'active' | 'finished' | 'cancelled'

export interface MatchState {
  id: string
  game_type: string
  status: GameStatus
  player_one_id?: string | null
  player_two_id?: string | null
  current_turn?: string | null
  winner_id?: string | null
  board: (string | null)[]
  your_mark?: 'x' | 'o' | null
  can_play: boolean
}

export interface MoveResult {
  message: string
  match: MatchState
}

export interface GameInvitation {
  token: string
  game_id: string
  game_type: string
  status: string
  to_username?: string | null
  expires_at?: string | null
  invite_url: string
}

export interface GamePreview {
  game_id: string
  game_type: string
  status: string
  invitation_status: string
  expired: boolean
  inviter_username: string
  to_username?: string | null
}

export interface LeaderboardEntry {
  rank: number
  username: string
  display_name?: string | null
  avatar_url?: string | null
  matches: number
  wins: number
  losses: number
  draws: number
  win_pct: number
  current_streak: number
  rating?: number | null
}

export interface Leaderboard {
  game_type: string
  period: string
  entries: LeaderboardEntry[]
}
