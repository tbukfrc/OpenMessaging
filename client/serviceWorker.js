const openMessage = "open-message-pwa-v1"
const assets = [
  "/",
  "/index.html",
  "/style.css",
  "/script.js"
]

self.addEventListener("install", installEvent => {
  installEvent.waitUntil(
    caches.open(openMessage).then(cache => {
      cache.addAll(assets)
    })
  )
})

self.addEventListener("fetch", fetchEvent => {
    fetchEvent.respondWith(
      caches.match(fetchEvent.request).then(res => {
        return res || fetch(fetchEvent.request)
      })
    )
  })  