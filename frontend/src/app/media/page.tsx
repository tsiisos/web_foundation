"use client";

import { useEffect, useState } from "react";

import { RequireAuth } from "@/components/RequireAuth";
import { Alert, Card, buttonClass, inputClass, secondaryButtonClass } from "@/components/ui";
import { api, errorText, uploadFile } from "@/lib/api";
import type { MediaAsset, Paginated, User } from "@/lib/types";

const ACCEPT = ".jpg,.jpeg,.png,.webp,.mp4,.pdf,image/jpeg,image/png,image/webp,video/mp4,application/pdf";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDuration(seconds: number): string {
  const total = Math.round(seconds);
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

// Loads pages 1..pageCount. It only returns data and never touches component state.
async function fetchAll(pageCount: number): Promise<{ items: MediaAsset[]; total: number }> {
  const items: MediaAsset[] = [];
  let total = 0;
  for (let page = 1; page <= pageCount; page++) {
    const data = await api<Paginated<MediaAsset>>(`/api/v1/media/?page=${page}`);
    items.push(...data.results);
    total = data.count;
    if (!data.next) break;
  }
  return { items, total };
}

function MediaCard({ asset, onDelete }: { asset: MediaAsset; onDelete: (asset: MediaAsset) => void }) {
  // The video link is captured when Play is pressed, so later list refreshes never restart playback
  const [playing, setPlaying] = useState<string | null>(null);

  const badge =
    asset.status === "processing"
      ? "bg-amber-100 text-amber-800"
      : asset.status === "failed"
        ? "bg-red-100 text-red-800"
        : "bg-slate-100 text-slate-700";

  return (
    <li className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <div className="flex aspect-video items-center justify-center bg-slate-100">
        {asset.kind === "video" && playing ? (
          <video className="h-full w-full bg-black" controls autoPlay playsInline src={playing} poster={asset.thumbnail_url ?? undefined} />
        ) : asset.kind === "video" && asset.url ? (
          <button type="button" className="relative h-full w-full" onClick={() => setPlaying(asset.url)} aria-label="Play video">
            {asset.thumbnail_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={asset.thumbnail_url} alt={asset.original_name} className="h-full w-full object-cover" />
            ) : null}
            <span className="absolute inset-0 flex items-center justify-center text-4xl text-white drop-shadow">▶</span>
          </button>
        ) : asset.kind === "image" && asset.url ? (
          <a href={asset.url} target="_blank" rel="noreferrer" className="block h-full w-full">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={asset.thumbnail_url ?? asset.url} alt={asset.original_name} className="h-full w-full object-cover" />
          </a>
        ) : asset.kind === "document" && asset.url ? (
          <a href={asset.url} className="text-sm font-medium underline">
            Download PDF
          </a>
        ) : (
          <span className="text-sm text-slate-500">{asset.status === "processing" ? "Processing…" : "Unavailable"}</span>
        )}
      </div>
      <div className="space-y-1 p-3 text-sm">
        <p className="truncate font-medium" title={asset.original_name}>
          {asset.original_name}
        </p>
        <p className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
          <span className={`rounded px-1.5 py-0.5 ${badge}`}>{asset.status}</span>
          <span>{asset.visibility}</span>
          <span>{formatBytes(asset.size)}</span>
          {asset.duration ? <span>{formatDuration(asset.duration)}</span> : null}
        </p>
        {asset.status === "failed" && asset.error ? <p className="text-xs text-red-700">{asset.error}</p> : null}
        <button type="button" className={`${secondaryButtonClass} mt-2`} onClick={() => onDelete(asset)}>
          Delete
        </button>
      </div>
    </li>
  );
}

function MediaLibrary({ user }: { user: User }) {
  const [items, setItems] = useState<MediaAsset[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [tick, setTick] = useState(0); // bump to reload the list
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [visibility, setVisibility] = useState("private");
  const [progress, setProgress] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const reload = () => setTick((value) => value + 1);

  // State is only set in the promise callbacks, never directly in the effect body
  useEffect(() => {
    let active = true;
    fetchAll(pages)
      .then((data) => {
        if (!active) return;
        setItems(data.items);
        setTotal(data.total);
        setError(null);
        setLoading(false);
      })
      .catch((err) => {
        if (!active) return;
        setError(errorText(err));
        setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [pages, tick]);

  // Private links expire, and videos finish processing in the background, so refresh regularly
  const hasProcessing = items.some((asset) => asset.status === "processing");
  useEffect(() => {
    const id = setInterval(() => setTick((value) => value + 1), hasProcessing ? 3000 : 4 * 60 * 1000);
    return () => clearInterval(id);
  }, [hasProcessing]);

  async function onUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setUploadError(null);
    if (!file) {
      setUploadError("Choose a file first.");
      return;
    }
    // Same limits as the server, for quick feedback. The server is the authority.
    const limitMb = file.type.startsWith("video/") ? 100 : 10;
    if (file.size > limitMb * 1024 * 1024) {
      setUploadError(`The file is larger than ${limitMb} MB.`);
      return;
    }
    setProgress(0);
    try {
      await uploadFile(file, visibility, setProgress);
      form.reset();
      setFile(null);
      reload();
    } catch (err) {
      setUploadError(errorText(err));
    } finally {
      setProgress(null);
    }
  }

  async function onDelete(asset: MediaAsset) {
    if (!window.confirm(`Delete "${asset.original_name}"?`)) return;
    try {
      await api(`/api/v1/media/${asset.id}/`, { method: "DELETE" });
      reload();
    } catch (err) {
      setError(errorText(err));
    }
  }

  return (
    <div className="space-y-6">
      <Card title="Upload">
        {!user.is_email_verified ? (
          <Alert kind="info">Verify your email address to upload files. You can resend the email from your profile.</Alert>
        ) : null}
        <form onSubmit={onUpload} className="space-y-4">
          {uploadError ? <Alert kind="error">{uploadError}</Alert> : null}
          <input
            type="file"
            accept={ACCEPT}
            className="block w-full text-sm"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            disabled={progress !== null}
          />
          <p className="text-xs text-slate-500">
            Images (JPG, PNG, WebP, up to 10 MB), MP4 videos (H.264, up to 100 MB) and PDFs (private only, up to 10 MB).
          </p>
          <div className="flex items-center gap-3">
            <select className={`${inputClass} !mt-0 !w-auto`} value={visibility} onChange={(e) => setVisibility(e.target.value)} disabled={progress !== null}>
              <option value="private">Private</option>
              <option value="public">Public</option>
            </select>
            <button type="submit" className={buttonClass} disabled={progress !== null || !user.is_email_verified}>
              {progress !== null ? `Uploading ${progress}%` : "Upload"}
            </button>
          </div>
          {progress !== null ? (
            <div className="h-2 overflow-hidden rounded bg-slate-200">
              <div className="h-full bg-slate-900 transition-all" style={{ width: `${progress}%` }} />
            </div>
          ) : null}
        </form>
      </Card>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">
          Your files <span className="text-sm font-normal text-slate-500">({total})</span>
        </h2>
        {error ? <Alert kind="error">{error}</Alert> : null}
        {loading ? <p className="text-sm text-slate-500">Loading…</p> : null}
        {!loading && items.length === 0 && !error ? <p className="text-sm text-slate-500">Nothing uploaded yet.</p> : null}
        <ul className="grid gap-4 sm:grid-cols-2">
          {items.map((asset) => (
            <MediaCard key={asset.id} asset={asset} onDelete={onDelete} />
          ))}
        </ul>
        {items.length < total ? (
          <button type="button" className={secondaryButtonClass} onClick={() => setPages(pages + 1)}>
            Load more
          </button>
        ) : null}
      </section>
    </div>
  );
}

export default function MediaPage() {
  return <RequireAuth>{(user) => <MediaLibrary user={user} />}</RequireAuth>;
}
