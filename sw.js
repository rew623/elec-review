/* 서비스워커 — 앱 파일을 바꾸면 VERSION 을 올린다(index.html 의 APP_VERSION 과 같게). */
const VERSION = '1.5.8';
const SHELL_CACHE = 'shell-' + VERSION;
const FONT_CACHE = 'fonts-v1';
const SHELL = ['./', 'index.html', 'kec-data.js', 'law-data.js', 'kds-data.js', 'pum-data.js', 'pdf.min.js', 'pdf.worker.min.js', 'manifest.json', 'icons/icon.svg', 'icons/icon-192.png', 'icons/icon-512.png'];

self.addEventListener('install', (e) => {
  // 새 버전은 대기 상태로 두고, 사용자가 "업데이트"를 누르면 SKIP_WAITING 으로 활성화
  e.waitUntil(caches.open(SHELL_CACHE).then(c => c.addAll(SHELL)));
});
self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) { if (k.startsWith('shell-') && k !== SHELL_CACHE) await caches.delete(k); }
    await self.clients.claim();
  })());
});
self.addEventListener('message', (e) => {
  if (e.data?.type === 'SKIP_WAITING') self.skipWaiting();
  if (e.data?.type === 'GET_VERSION') e.ports[0]?.postMessage(VERSION);
});
self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === 'https://fonts.googleapis.com' || url.origin === 'https://fonts.gstatic.com') { e.respondWith(staleWhileRevalidate(req, FONT_CACHE)); return; }
  if (url.origin !== location.origin) return;
  // 새 버전을 받기 전까지는 설치된 버전(캐시)을 그대로 쓴다 → 화면·코드가 섞이지 않고, 인터넷이 없어도 열림
  e.respondWith((async () => {
    const cache = await caches.open(SHELL_CACHE);
    const hit = await cache.match(req, { ignoreSearch: true }) || (req.mode === 'navigate' ? await cache.match('index.html') : null);
    if (hit) return hit;
    try { return await fetch(req); } catch (err) { return new Response('오프라인', { status: 503 }); }
  })());
});
async function staleWhileRevalidate(req, name) {
  const cache = await caches.open(name);
  const hit = await cache.match(req);
  const net = fetch(req).then(res => { if (res.ok || res.type === 'opaque') cache.put(req, res.clone()); return res; }).catch(() => hit);
  return hit || net;
}
