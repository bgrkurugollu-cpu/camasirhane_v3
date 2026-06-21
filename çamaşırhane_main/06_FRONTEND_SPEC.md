# LaundroStar — Frontend Mimarisi ve Kuralları

> Bu doküman frontend'in nasıl organize edildiğini, state'in nerede yaşadığını ve ortak etkileşim pattern'lerini tanımlar. Ekran bazlı spesifikasyon bu dokümanda **yok** — o [[07_SCREEN_CATALOG]]'da. Bu doküman kural kitabıdır; ekran kataloğu oyun planıdır.

---

## 1. Stack ve Mimari Karar

### 1.1 v4 Stack

| Bileşen | Versiyon / Seçim | Not |
|---------|-----------------|-----|
| Dil | Vanilla JavaScript (ES2022+) | ADR-001: React/Next.js migrasyonu v5'te |
| HTML | HTML5 | Sunucu tarafından statik olarak servis edilir |
| CSS Framework | Tailwind CSS (CDN) | Hızlı geliştirme için CDN yeterli; build pipeline eklenmez |
| Grafik | Chart.js (CDN) | Dashboard grafikleri |
| QR/Barcode | html5-qrcode (CDN) | RFID simülasyonu için tarayıcı kamerası |
| Fetch | Native `fetch` API | Axios bağımlılığı eklenmiyor |

**ADR-001 Özeti:** React + TypeScript vibecoding standardının önerdiği yığındır. Ancak LaundroStar'ın ölçeği (< 20 eşzamanlı kullanıcı, < 15 ekran, dahili tesis uygulaması) ve mevcut Vanilla JS altyapısı göz önüne alındığında, v4'te modüler Vanilla JS yaklaşımı seçilmiştir. Öncelikler: güvenlik düzeltmeleri ve backend mimarisi. Next.js migrasyonu v5'te değerlendirilecektir.

### 1.2 Temel Mimari

Frontend **Single Page Application (SPA)** olarak çalışır:
- `index.html` tek entry point.
- Navigasyon `data-target` attribute ve JS routing ile yapılır; sayfa yenilenmez.
- Tüm veri `fetch` ile API'den asenkron çekilir.
- State global `AppState` objesi üzerinde tutulur.

---

## 2. Klasör Yapısı — `apps/api/static/`

```
static/
├── index.html              # Tek HTML dosyası; tüm sayfa yapısı burada
├── style.css               # Tailwind extend + custom CSS
│
└── js/
    ├── app.js              # Entry point: DOMContentLoaded, global init
    ├── state.js            # AppState: token, user, role yönetimi
    ├── api.js              # apiFetch() wrapper; token refresh interceptor
    ├── auth.js             # login(), logout(), refreshToken()
    ├── router.js           # handleNavigation(), view switch
    │
    ├── modules/
    │   ├── dashboard.js    # loadDashboard(), chart rendering
    │   ├── kirli.js        # kirliGiris(), sepetSimulasyon()
    │   ├── islem.js        # onayla(), teslim()
    │   ├── raf.js          # raf simülasyon, selectRack(), raf detay
    │   ├── tablo.js        # setupTableView(), loadTablo()
    │   ├── kiyafet.js      # RFID eşleştirme CRUD
    │   ├── kullanici.js    # Kullanıcı yönetimi (admin)
    │   ├── profil.js       # Profil güncelleme (avatar = ad/soyad baş harfleri)
    │   └── audit.js        # Audit log görüntüleme
    │
    └── utils/
        ├── toast.js        # showToast(message, type)
        ├── modal.js        # showModal(), closeModal()
        └── format.js       # formatDate(), formatRafId()
```

---

## 3. State Yönetimi

Tüm global state tek bir `AppState` objesi üzerinde tutulur:

```javascript
// state.js
const AppState = {
  accessToken: null,
  csrfToken: null,
  currentUser: null,     // { id, username, role, email, ... }
  currentView: null,     // aktif view adı

  setSession(tokenData) {
    this.accessToken = tokenData.access_token;
    this.csrfToken = tokenData.csrf_token;
    this.currentUser = tokenData.user;
  },

  clearSession() {
    this.accessToken = null;
    this.csrfToken = null;
    this.currentUser = null;
  },

  isAdmin() {
    return this.currentUser?.role === 'admin';
  }
};
```

**Kural:** `localStorage` veya `sessionStorage` token saklama **yasaktır**. Access token yalnızca `AppState.accessToken` değişkeninde (memory'de) tutulur. Refresh token httpOnly cookie'de — JS erişemez.

---

## 4. API Fetch Wrapper

Tüm API çağrıları `apiFetch()` üzerinden yapılır:

```javascript
// api.js
async function apiFetch(url, options = {}) {
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers
  };

  if (AppState.accessToken) {
    headers['Authorization'] = `Bearer ${AppState.accessToken}`;
  }

  // CSRF: state-changing method'larda zorunlu
  if (['POST', 'PATCH', 'DELETE'].includes(options.method?.toUpperCase())) {
    headers['X-CSRF-Token'] = AppState.csrfToken;
  }

  const response = await fetch(url, { ...options, headers, credentials: 'include' });

  // 401 AUTH_TOKEN_EXPIRED → silent refresh
  if (response.status === 401) {
    const error = await response.json();
    if (error?.error?.code === 'AUTH_TOKEN_EXPIRED') {
      const refreshed = await refreshToken();
      if (refreshed) {
        // Orijinal isteği yeni token ile tekrarla
        headers['Authorization'] = `Bearer ${AppState.accessToken}`;
        return fetch(url, { ...options, headers, credentials: 'include' });
      } else {
        logout();
        return;
      }
    }
  }

  return response;
}
```

**Kurallar:**
- Tüm fetch çağrıları `apiFetch()` kullanır; doğrudan `fetch()` kullanılmaz.
- CSRF header yalnızca mutating metodlarda gönderilir.
- `credentials: 'include'` her çağrıda zorunlu (cookie için).
- 401 token expired dışındaki hatalar caller'da handle edilir.

---

## 5. Auth Akışı (Frontend Tarafı)

```
Login form submit
  → POST /api/v1/auth/login
  → 200: AppState.setSession(data) → dashboard redirect
  → 401: Hata mesajı göster

API çağrısı → 401 AUTH_TOKEN_EXPIRED
  → POST /api/v1/auth/refresh (cookie otomatik gider)
  → 200: AppState.accessToken = yeni token → orijinal isteği tekrarla
  → 401: logout() → login sayfası

Logout
  → POST /api/v1/auth/logout
  → AppState.clearSession()
  → Login modal göster
```

---

## 6. Yetki Kontrollü UI Render

Admin-only elementler DOM'dan saklanır veya kaldırılır; yalnızca gizlenmez (CSS gizleme güvenlik sağlamaz — backend zaten kontrol eder, ama kullanıcı deneyimi için DOM'dan çıkarılır).

```javascript
// router.js
function renderAdminElements() {
  const adminElements = document.querySelectorAll('[data-role="admin"]');
  adminElements.forEach(el => {
    if (!AppState.isAdmin()) {
      el.remove();
    }
  });
}
```

---

## 7. Error ve Loading State Pattern

Her async operasyon üç state'i handle eder:

```javascript
async function loadDashboard() {
  showLoading('dashboard-container');
  try {
    const resp = await apiFetch('/api/v1/stats');
    const { data } = await resp.json();
    renderDashboard(data);
  } catch (err) {
    showError('dashboard-container', 'Veriler yüklenemedi.');
  } finally {
    hideLoading('dashboard-container');
  }
}
```

**Toast bildirimleri:**

```javascript
// utils/toast.js
function showToast(message, type = 'success') {
  // type: 'success' | 'error' | 'warning' | 'info'
  // ...DOM injection; 3 saniye sonra otomatik kaldır
}
```

---

## 8. Form Pattern

Form submit'ler `preventDefault()` ile handle edilir; HTTP form submit yoktur.

```javascript
document.getElementById('login-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;

  if (!username || !password) {
    showToast('Tüm alanları doldurun.', 'error');
    return;
  }

  const resp = await apiFetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  });

  if (resp.ok) {
    const { data } = await resp.json();
    AppState.setSession(data);
    handleNavigation('dashboard');
  } else {
    const { error } = await resp.json();
    showToast(getErrorMessage(error.code), 'error');
  }
});
```

---

## 9. Tablo ve Sayfalama Pattern

```javascript
// tablo.js
let tableState = { offset: 0, limit: 50, total: 0, query: '' };

async function loadTablo(type) {
  const params = new URLSearchParams({
    offset: tableState.offset,
    limit: tableState.limit,
    q: tableState.query
  });
  const resp = await apiFetch(`/api/v1/tablo/${type}?${params}`);
  const { data, meta } = await resp.json();
  renderTable(data);
  renderPagination(meta);
}
```

---

## 10. Sayfalar Arası Navigasyon

Sayfa yenilemesi olmadan SPA navigasyonu:

```javascript
// router.js
function handleNavigation(target) {
  // Tüm section'ları gizle
  document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));
  
  // Hedef section'ı göster
  const view = ROUTE_MAP[target];
  if (view) {
    document.getElementById(view.elementId)?.classList.add('active');
    document.getElementById('page-title').innerText = view.title;
    view.onEnter?.();
  }
}

const ROUTE_MAP = {
  'dashboard':       { elementId: 'dashboard',       title: 'Dashboard',         onEnter: loadDashboard },
  'kirli-giris':     { elementId: 'action-view',     title: 'Kirli Kıyafet Girişi', onEnter: setupKirliGiris },
  'tablo-kirli':     { elementId: 'tablo-view',      title: 'Kirli Bekleyenler', onEnter: () => loadTablo('kirli') },
  'tablo-temiz':     { elementId: 'tablo-view',      title: 'Temiz Kıyafetler',  onEnter: () => loadTablo('temiz') },
  'tablo-teslim':    { elementId: 'tablo-view',      title: 'Teslim Edilenler',  onEnter: () => loadTablo('teslim') },
  'raf-simulasyon':  { elementId: 'raf-simulasyon',  title: 'Raf Simülasyonu',   onEnter: () => selectRack('A') },
  'rfid-eslestirme': { elementId: 'action-view',     title: 'RFID Eşleştirme',   onEnter: setupRfidEslestirme },
  'audit-logs':      { elementId: 'audit-logs',      title: 'Audit Logları',      onEnter: loadAuditLogs },
  'kullanici-yonetimi': { elementId: 'admin-view',   title: 'Kullanıcı Yönetimi', onEnter: loadKullanicilar },
};
```

---

## 11. Güvenlik Kuralları (Frontend)

- Token **asla** `localStorage`/`sessionStorage`'a yazılmaz. Bellekte (AppState) saklanır.
- `innerHTML` kullanımı Vibecoding güvenlik standartları gereği **tamamen yasaklanmış ve sıfırlanmıştır**. Sayfadaki tüm dinamik veriler ve tablolar DOM Helper (`document.createElement`) mimarisi kullanılarak ve `.textContent` atamalarıyla DOM'a entegre edilir.
- Sayfa açılışında (`DOMContentLoaded`) Silent Token Refresh çalışarak oturumu yeniler.
- CSRF token her mutating çağrıda (POST, PATCH, DELETE) header olarak gönderilir.
- Profil avatarı: fotoğraf yükleme yoktur; avatar, kullanıcının ad/soyad baş harflerinden (`getInitials`) istemci tarafında üretilir ve `.textContent` ile basılır.
