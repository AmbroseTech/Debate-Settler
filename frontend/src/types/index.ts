// Shared TypeScript types mirroring the backend schemas (§68).

export type DebateMode = 'local' | 'online'
export type DebateStatus =
  | 'draft' | 'open' | 'active' | 'voting' | 'closing_soon' | 'closed'
  | 'being_verified' | 'settled' | 'draw' | 'disputed' | 'funding_timeout'
  | 'cancelled' | 'under_review' | 'payment_pending'
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
  draw_returns_stakes: boolean
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
  has_funded: boolean
  confirmed: boolean
  username?: string | null
}

export interface VoteCounts {
  side_a: number
  side_b: number
  draw: number
  total: number
  required: number
  revealed: boolean
}

export interface DebateBrief {
  id: string
  mode: DebateMode
  status: DebateStatus
  question: string
  side_a_label: string
  side_b_label: string
  stake_amount: string
  currency: string
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
  platform_fee_percent: string
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

export interface Wallet {
  id: string
  currency: string
  is_frozen: boolean
  available_balance: string
  locked_balance: string
  pending_balance: string
  withdrawable_balance: string
}

export interface Transaction {
  id: string
  reference: string
  type: string
  amount: string
  currency: string
  status: string
  provider?: string | null
  debate_id?: string | null
  is_demo: boolean
  created_at: string
}

export interface ProviderOption {
  code: string
  display_name: string
  kind: string
  supports_deposit: boolean
  supports_payout: boolean
  is_demo: boolean
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

export interface StakePreview {
  your_stake: string
  total_pool: string
  platform_fee_percent: string
  platform_fee_amount: string
  estimated_winner_settlement: string
  currency: string
  is_demo: boolean
  real_money_enabled: boolean
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
