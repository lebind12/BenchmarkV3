// Shared refs (main-home feature will define these; placeholder for fixture-detail).

export interface LeagueRef {
  external_id: number
  slug: string
  name: string
  name_ko: string | null
  short_name_ko: string | null
  logo_url: string | null
}

export interface TeamRef {
  external_id: number
  slug: string
  name: string
  name_ko: string | null
  short_name_ko: string | null
  logo_url: string | null
}

export interface PlayerRef {
  external_id: number
  slug: string
  name: string
  name_ko: string | null
  photo_url: string | null
}
