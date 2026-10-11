// Refreshes src/data/videos.json and src/assets/videos/* from TikTok's public oEmbed endpoint.
// Usage: npm run videos -- <tiktok video url> [...more]   (new URLs go first)
//        npm run videos                                   (re-fetch the existing list)
import { readFile, writeFile, mkdir } from 'node:fs/promises';

const DATA = new URL('../src/data/videos.json', import.meta.url);
const IMAGES = new URL('../src/assets/videos/', import.meta.url);
const MAX = 6;

// TikTok's oEmbed endpoint sometimes answers 503 under light load, so retry with a growing pause.
async function fetchWithRetry(url, attempts = 6) {
  let response;
  for (let attempt = 1; attempt <= attempts; attempt++) {
    response = await fetch(url);
    if (response.ok || attempt === attempts) break;
    await new Promise((resolve) => setTimeout(resolve, attempt * 2000));
  }
  return response;
}

const existing = JSON.parse(await readFile(DATA, 'utf8').catch(() => '[]'));
const urls = [...process.argv.slice(2), ...existing.map((video) => video.url)];
const unique = [...new Set(urls)].slice(0, MAX);

await mkdir(IMAGES, { recursive: true });

const videos = [];
for (const url of unique) {
  const id = url.match(/\/video\/(\d+)/)?.[1];
  if (!id) throw new Error(`Not a TikTok video URL: ${url}`);

  const oembed = await fetchWithRetry(`https://www.tiktok.com/oembed?url=${encodeURIComponent(url)}`);
  if (!oembed.ok) throw new Error(`oEmbed failed for ${url}: ${oembed.status}`);
  const { title, thumbnail_url, thumbnail_width, thumbnail_height } = await oembed.json();

  const image = await fetchWithRetry(thumbnail_url);
  if (!image.ok) throw new Error(`Cover download failed for ${url}: ${image.status}`);
  await writeFile(new URL(`${id}.jpg`, IMAGES), Buffer.from(await image.arrayBuffer()));

  videos.push({
    url,
    title,
    image: `${id}.jpg`,
    width: Number(thumbnail_width),
    height: Number(thumbnail_height),
  });
}

await writeFile(DATA, JSON.stringify(videos, null, 2) + '\n');
console.log(`Saved ${videos.length} videos.`);
