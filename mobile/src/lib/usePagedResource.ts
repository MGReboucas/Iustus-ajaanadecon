import { useEffect, useRef, useState } from 'react';
import { useSession } from '../auth/SessionProvider';
import { errorMessage } from './api';
import type { Page } from './types';
import { useResource } from './useResource';

/** Additional pages belong to the first page that produced their cursor. */
export function usePagedResource<T extends { id: string }>(path: string) {
  const { api } = useSession();
  const resource = useResource<Page<T>>(path);
  const [tail, setTail] = useState<{ base: Page<T>; rows: T[]; cursor: string | null }>();
  const [moreLoading, setMoreLoading] = useState(false);
  const [moreError, setMoreError] = useState('');
  const reading = useRef(false);
  const latest = useRef(resource.data);
  useEffect(() => { latest.current = resource.data; return () => { latest.current = undefined; }; }, [resource.data]);
  const currentTail = tail?.base === resource.data ? tail : undefined;
  const cursor = currentTail ? currentTail.cursor : resource.data?.nextCursor;
  const rows = [...(resource.data?.results || []), ...(currentTail?.rows || [])]
    .filter((row, index, all) => all.findIndex(other => other.id === row.id) === index);
  async function loadMore() {
    const base = resource.data;
    if (!base || !cursor || reading.current || resource.loading) return;
    reading.current = true; setMoreLoading(true); setMoreError('');
    try {
      const page = await api<Page<T>>(`${path}?cursor=${encodeURIComponent(cursor)}`);
      if (latest.current === base) setTail({ base, rows: [...(currentTail?.rows || []), ...page.results], cursor: page.nextCursor });
    } catch (error) { if (latest.current === base) setMoreError(errorMessage(error)); }
    finally { reading.current = false; setMoreLoading(false); }
  }
  async function reload() { setMoreError(''); await resource.reload(); }
  return { ...resource, rows, cursor, loadMore, moreLoading, moreError, reload };
}
