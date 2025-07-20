import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';

export default function Home() {
  const [url, setUrl] = useState('');
  const queryClient = useQueryClient();
  const api = process.env.NEXT_PUBLIC_API_URL;

  const { data: links } = useQuery({
    queryKey: ['links'],
    queryFn: () => axios.get(`${api}/links`).then(r => r.data),
    refetchInterval: 30_000,
  });

  const { data: scrapes } = useQuery({
    queryKey: ['scrapes'],
    queryFn: () => axios.get(`${api}/scrapes`).then(r => r.data),
    refetchInterval: 10_000,
  });

  const addLink = async () => {
    await axios.post(`${api}/links`, { url });
    setUrl('');
    queryClient.invalidateQueries(['links']);
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-4">Textile Aggregator</h1>
      <div className="flex gap-2 mb-6">
        <input
          className="border px-2 flex-1"
          placeholder="Paste textile URL…"
          value={url}
          onChange={e => setUrl(e.target.value)}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded"
          onClick={addLink}
        >
          Add
        </button>
      </div>

      <h2 className="text-xl font-semibold mb-2">Latest Scrapes</h2>
      <ul className="space-y-3">
        {scrapes?.map(s => (
          <li key={s._id} className="border p-3 rounded">
            <div className="font-bold">{s.title}</div>
            <div className="text-sm text-gray-600">{s.description}</div>
            <div className="text-xs text-gray-400">{new Date(s.scrapedAt).toLocaleString()}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}