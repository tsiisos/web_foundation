export type User = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  is_customer: boolean;
  is_provider: boolean;
  is_email_verified: boolean;
  date_joined: string;
};

export type MediaAsset = {
  id: string;
  kind: "image" | "video" | "document";
  visibility: "public" | "private";
  status: "processing" | "ready" | "failed";
  error: string;
  original_name: string;
  content_type: string;
  size: number;
  width: number | null;
  height: number | null;
  duration: number | null;
  url: string | null;
  thumbnail_url: string | null;
  created_at: string;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};
