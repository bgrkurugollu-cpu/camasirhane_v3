
// DOM Helper for XSS protection
function createEl(tag, className = '', textContent = '') {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (textContent) el.textContent = textContent;
    return el;
}


// Faz 4 & Faz 5: apiFetch wrapper ve AppState (localStorage iptal)
const AppState = { token: null };

async function apiFetch(url, options = {}) {
    options.headers = options.headers || {};
    const token = AppState.token;
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    
    // CSRF Token
    const csrfMatch = document.cookie.match(/csrf_token=([^;]+)/);
    if (csrfMatch && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method?.toUpperCase())) {
        options.headers['x-csrf-token'] = csrfMatch[1];
    }
    
    let response = await fetch(url, options);
    
    if (response.status === 401 && !url.includes('/auth/token') && !url.includes('/auth/refresh') && !url.includes('/auth/mfa/verify')) {
        const refreshRes = await fetch('/api/v1/auth/refresh', { method: 'POST' });
        if (refreshRes.ok) {
            const data = await refreshRes.json();
            AppState.token = data.access_token;
            options.headers['Authorization'] = `Bearer ${data.access_token}`;
            response = await fetch(url, options);
        } else {
            AppState.token = null;
            window.location.reload();
        }
    }
    return response;
}


let currentUserRole = null;
let historyChartInstance = null;
let shelfChartInstance = null;
let currentChartPeriod = 'weekly';
let html5QrcodeScanner = null;


document.addEventListener('DOMContentLoaded', async () => {
    // Sayfa yüklendiğinde refresh token ile access token almayı dene
    try {
        const refreshRes = await fetch('/api/v1/auth/refresh', { method: 'POST' });
        if (refreshRes.ok) {
            const data = await refreshRes.json();
            AppState.token = data.access_token;
        }
    } catch (e) {}

    const token = AppState.token;
    
    if (!token) {
        showLoginModal();
    } else {
        await fetchUserInfo();
    }


    // Navigation routing
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const target = btn.dataset.target;
            handleNavigation(target);
        });
    });
});

function handleNavigation(target) {
    document.querySelectorAll('.view-section').forEach(s => s.classList.remove('active'));

    const pageTitle = document.getElementById('page-title');

    if (target === 'dashboard') {
        pageTitle.innerText = "Dashboard";
        document.getElementById('dashboard').classList.add('active');
        loadDashboard();
    } else if (target === 'kirli-giris' || target === 'rfid-eslestirme') {
        setupActionView(target);
    } else if (target.startsWith('tablo-')) {
        setupTableView(target.replace('tablo-', ''));
    } else if (target === 'raf-simulasyon') {
        pageTitle.innerText = "Raf Simülasyonu";
        document.getElementById('raf-simulasyon').classList.add('active');
        selectRack('A');
    } else if (target === 'audit-logs') {
        pageTitle.innerText = "Audit Logları";
        document.getElementById('audit-logs').classList.add('active');
        loadAuditLogs();
    } else if (target === 'edge-devices') {
        pageTitle.innerText = "Edge Cihazlar";
        document.getElementById('edge-devices').classList.add('active');
        loadEdgeDevices();
    }

    // Auto-close sidebar on mobile after navigation
    if (window.innerWidth < 768) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar && !sidebar.classList.contains('-translate-x-full')) {
            toggleMobileSidebar();
        }
    }
}

function setupActionView(action) {
    const view = document.getElementById('action-view');
    view.classList.add('active');

    let cfg;
    const sicilContainer = document.getElementById('sicil_container');
    const sicilInput = document.getElementById('sicil_numarasi');
    const kisiDetayContainer = document.getElementById('kisi_detay_container');

    const rfidOkuContainer = document.getElementById('rfid-oku-container');
    const rfidOkuSonuc = document.getElementById('rfid-oku-sonuc');

    if (action === 'kirli-giris') {
        cfg = { title: 'Kirli Kıyafet Girişi', type: 'kirli', bg: 'bg-red-500' };
        sicilContainer.classList.add('hidden');
        if (kisiDetayContainer) kisiDetayContainer.classList.add('hidden');
        sicilInput.required = false;
        if (rfidOkuContainer) rfidOkuContainer.classList.remove('hidden');
        if (rfidOkuSonuc) rfidOkuSonuc.classList.add('hidden');
    } else {
        cfg = { title: 'RFID Eşleştirme', type: 'eslestirme', bg: 'bg-indigo-500' };
        sicilContainer.classList.remove('hidden');
        if (kisiDetayContainer) kisiDetayContainer.classList.remove('hidden');
        sicilInput.required = true;
        if (rfidOkuContainer) rfidOkuContainer.classList.add('hidden');
        if (rfidOkuSonuc) rfidOkuSonuc.classList.add('hidden');
    }

    document.getElementById('page-title').innerText = cfg.title;
    document.getElementById('action-title').innerText = cfg.title;
    document.getElementById('islem_tipi').value = cfg.type;
    document.getElementById('rfid_tag').value = '';
    sicilInput.value = '';
    
    if (kisiDetayContainer) {
        document.getElementById('kisi_ad').value = '';
        document.getElementById('kisi_soyad').value = '';
        document.getElementById('kisi_cinsiyet').value = '';
        document.getElementById('kisi_ad').readOnly = false;
        document.getElementById('kisi_soyad').readOnly = false;
        document.getElementById('kisi_cinsiyet').disabled = false;
        document.getElementById('kisi_ad').classList.remove('bg-gray-100');
        document.getElementById('kisi_soyad').classList.remove('bg-gray-100');
        document.getElementById('kisi_cinsiyet').classList.remove('bg-gray-100');
        const msg = document.getElementById('kisi_detay_msg');
        if (msg) {
            msg.innerText = "Personel bilgilerini giriniz:";
            msg.className = "text-xs text-gray-500 font-semibold mb-2";
        }
    }

    const header = document.getElementById('action-header');
    header.className = `p-6 text-center transition-colors duration-300 ${cfg.bg}`;

    // Focus after animation
    setTimeout(() => {
        document.getElementById('rfid_tag').focus();
    }, 100);
}

async function submitIslem(e) {
    e.preventDefault();
    const islem_tipi = document.getElementById('islem_tipi').value;
    const rfid_tag = document.getElementById('rfid_tag').value;
    const sicil_numarasi = document.getElementById('sicil_numarasi').value;

    try {
        let endpoint = '/api/v1/islem';
        let payload = { islem_tipi, rfid_tag };

        if (islem_tipi === 'eslestirme') {
            endpoint = '/api/v1/kiyafet';
            payload = { 
                rfid_tag, 
                sicil_numarasi,
                ad: document.getElementById('kisi_ad')?.value,
                soyad: document.getElementById('kisi_soyad')?.value,
                cinsiyet: document.getElementById('kisi_cinsiyet')?.value
            };
        } else {
            if (sicil_numarasi) payload.sicil_numarasi = sicil_numarasi;
        }

        const res = await fetchWithAuth(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast('İşlem başarıyla kaydedildi!');
            document.getElementById('rfid_tag').value = '';
            document.getElementById('sicil_numarasi').value = '';
            if (islem_tipi === 'eslestirme') {
                document.getElementById('kisi_ad').value = '';
                document.getElementById('kisi_soyad').value = '';
                document.getElementById('kisi_cinsiyet').value = '';
            }
            document.getElementById('rfid_tag').focus();
        } else {
            const errData = await res.json();
            showToast(errData.detail || 'Bir hata oluştu!', true);
        }
    } catch (err) {
        showToast('Sunucuya bağlanılamadı!', true);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const sicilInput = document.getElementById('sicil_numarasi');
    if (sicilInput) {
        sicilInput.addEventListener('blur', async function(e) {
            if (document.getElementById('islem_tipi').value !== 'eslestirme') return;
            const sicil = e.target.value.trim();
            if (!sicil) return;

            try {
                const res = await fetchWithAuth(`/api/v1/calisan/${sicil}`);
                const kisiAd = document.getElementById('kisi_ad');
                const kisiSoyad = document.getElementById('kisi_soyad');
                const kisiCinsiyet = document.getElementById('kisi_cinsiyet');
                const msg = document.getElementById('kisi_detay_msg');

                if (res.ok) {
                    const data = await res.json();
                    kisiAd.value = data.ad || '';
                    kisiSoyad.value = data.soyad || '';
                    kisiCinsiyet.value = data.cinsiyet || '';
                    
                    kisiAd.readOnly = true;
                    kisiSoyad.readOnly = true;
                    kisiCinsiyet.disabled = true;
                    kisiAd.classList.add('bg-gray-100');
                    kisiSoyad.classList.add('bg-gray-100');
                    kisiCinsiyet.classList.add('bg-gray-100');
                    
                    if (msg) {
                        msg.innerText = "Personel sistemde kayıtlı:";
                        msg.className = "text-xs text-green-600 font-bold mb-2";
                    }
                } else {
                    kisiAd.value = '';
                    kisiSoyad.value = '';
                    kisiCinsiyet.value = '';
                    kisiAd.readOnly = false;
                    kisiSoyad.readOnly = false;
                    kisiCinsiyet.disabled = false;
                    kisiAd.classList.remove('bg-gray-100');
                    kisiSoyad.classList.remove('bg-gray-100');
                    kisiCinsiyet.classList.remove('bg-gray-100');
                    kisiAd.required = true;
                    kisiSoyad.required = true;
                    if (msg) {
                        msg.innerText = "Yeni personel kaydı (Bilgileri giriniz):";
                        msg.className = "text-xs text-blue-600 font-bold mb-2";
                    }
                }
            } catch (err) {
                console.error("Personel bilgisi okunamadı:", err);
            }
        });
    }
});

// === QR/Barcode Scanner Functions ===
function onScanSuccess(decodedText, decodedResult) {
    // Handle the scanned code. Focus the other input field automatically.
    document.getElementById('rfid_tag').value = decodedText;
    stopScanner();
    document.getElementById('sicil_numarasi').focus();
    const audio = new Audio('https://freesound.org/data/previews/320/320181_3306938-lq.mp3'); // Optional beep sound
    audio.play().catch(e => console.log(e));
}

function startScanner() {
    document.getElementById('scanner-container').classList.remove('hidden');
    
    if (!html5QrcodeScanner) {
        html5QrcodeScanner = new Html5Qrcode("reader");
    }
    
    // First try "environment" (rear camera)
    html5QrcodeScanner.start(
        { facingMode: "environment" }, 
        {
            fps: 10,
            qrbox: { width: 250, height: 250 },
            aspectRatio: 1.0
        },
        onScanSuccess,
        (errorMessage) => {
            // parse errors are ignored usually
        }
    ).catch(err => {
        console.error("Camera start failed for environment, error:", err);
        // On mobile, accessing via HTTP (instead of HTTPS) blocks camera
        if (window.location.protocol === 'http:' && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {
            showToast("Dikkat: Telefon tarayıcıları 'http://' adreslerinde kamerayı gizlilik nedeniyle engeller! Ngrok gibi bir HTTPS aracı kullanmalısınız.", true);
        } else {
            showToast("Kamera başlatılamadı. İzinleri kontrol edin veya arka kamera desteklenmiyor.", true);
        }
        document.getElementById('scanner-container').classList.add('hidden');
    });
}

function stopScanner() {
    if (html5QrcodeScanner && html5QrcodeScanner.isScanning) {
        html5QrcodeScanner.stop().then(() => {
            html5QrcodeScanner.clear();
            document.getElementById('scanner-container').classList.add('hidden');
        }).catch(error => {
            console.error("Failed to stop scanner", error);
        });
    } else {
        document.getElementById('scanner-container').classList.add('hidden');
    }
}

async function loadDashboard() {
    try {
        const res = await fetchWithAuth('/api/v1/stats');
        const data = await res.json();
        document.getElementById('stat-kirli').innerText = data.kirli_bugun;
        document.getElementById('stat-temiz').innerText = data.temiz_bugun;
        document.getElementById('stat-teslim').innerText = data.teslim_bugun;
        
        // Grafiği de yükle
        await loadHistoryChart(currentChartPeriod);
        loadShelfChart();
    } catch (err) {
        console.error("Dashboard yüklenemedi", err);
    }
}

async function loadHistoryChart(period) {
    try {
        const res = await fetchWithAuth(`/api/v1/stats/history?period=${period}`);
        if (!res.ok) return;
        const data = await res.json();
        
        renderChart(data);
    } catch (err) {
        console.error("Grafik verisi yüklenemedi", err);
    }
}

function changeChartPeriod(period) {
    currentChartPeriod = period;
    
    // UI Buton Güncellemesi
    const btnW = document.getElementById('btn-period-weekly');
    const btnM = document.getElementById('btn-period-monthly');
    
    if (period === 'weekly') {
        btnW.className = 'px-4 py-1.5 text-sm font-medium rounded-md bg-white shadow-sm text-indigo-600 transition-colors';
        btnM.className = 'px-4 py-1.5 text-sm font-medium rounded-md text-gray-500 hover:text-gray-700 transition-colors';
    } else {
        btnM.className = 'px-4 py-1.5 text-sm font-medium rounded-md bg-white shadow-sm text-indigo-600 transition-colors';
        btnW.className = 'px-4 py-1.5 text-sm font-medium rounded-md text-gray-500 hover:text-gray-700 transition-colors';
    }
    
    loadHistoryChart(period);
}

function renderChart(data) {
    const ctx = document.getElementById('historyChart');
    if (!ctx) return;
    
    if (historyChartInstance) {
        historyChartInstance.destroy();
    }
    
    historyChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [
                {
                    label: 'Kirli Gelen',
                    data: data.kirli_data,
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderColor: 'rgb(239, 68, 68)',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Temizlenen',
                    data: data.temiz_data,
                    backgroundColor: 'rgba(59, 130, 246, 0.7)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Teslim Edilen',
                    data: data.teslim_data,
                    backgroundColor: 'rgba(34, 197, 94, 0.7)',
                    borderColor: 'rgb(34, 197, 94)',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false,
            },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { usePointStyle: true, padding: 20 }
                },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.9)',
                    titleFont: { size: 13 },
                    bodyFont: { size: 13 },
                    padding: 12,
                    cornerRadius: 8,
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0 },
                    grid: { color: 'rgba(243, 244, 246, 1)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

async function loadShelfChart() {
    try {
        const res = await fetchWithAuth('/api/v1/stats/raflar');
        if (!res.ok) return;
        const data = await res.json();
        
        renderShelfChart(data);
    } catch (err) {
        console.error("Raf verisi yüklenemedi", err);
    }
}

function renderShelfChart(data) {
    const ctx = document.getElementById('shelfChart');
    if (!ctx) return;
    
    if (shelfChartInstance) {
        shelfChartInstance.destroy();
    }
    
    const labels = [];
    const doluData = [];
    const bosData = [];
    
    const racks = Object.keys(data).sort();
    
    for (const rack of racks) {
        labels.push(rack + ' Rafı');
        let rackTotalCapacity = 0;
        let rackTotalCount = 0;
        
        const compartments = data[rack];
        for (const compId in compartments) {
            rackTotalCount += compartments[compId].count || 0;
            rackTotalCapacity += compartments[compId].capacity || 0;
        }
        
        doluData.push(rackTotalCount);
        bosData.push(Math.max(0, rackTotalCapacity - rackTotalCount));
    }
    
    shelfChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Dolu Kapasite',
                    data: doluData,
                    backgroundColor: 'rgba(59, 130, 246, 0.8)',
                    borderColor: 'rgb(59, 130, 246)',
                    borderWidth: 1,
                    borderRadius: 4
                },
                {
                    label: 'Boş Kapasite',
                    data: bosData,
                    backgroundColor: 'rgba(229, 231, 235, 0.8)',
                    borderColor: 'rgb(209, 213, 219)',
                    borderWidth: 1,
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: { stacked: true, grid: { display: false } },
                y: { stacked: true, beginAtZero: true, border: {display: false} }
            },
            plugins: {
                legend: { position: 'bottom', labels: { usePointStyle: true, padding: 20 } },
                tooltip: {
                    backgroundColor: 'rgba(17, 24, 39, 0.9)',
                    cornerRadius: 8,
                    padding: 12
                }
            }
        }
    });
}

async function setupTableView(type) {
    _currentTabloType = type;
    const view = document.getElementById('tablo-view');
    view.classList.add('active');
    resetTableSearch();

    const titles = { 
        'kirli': 'Kirli Bekleyenler (Onay)', 
        'temiz': 'Teslim Edilecekler', 
        'teslim': 'Geçmiş Teslim Edilenler',
        'kiyafet': 'RFID Eşleştirme Tablosu'
    };
    document.getElementById('page-title').textContent = titles[type];

    const islemTh = document.getElementById('islem-th');
    const idTh = document.getElementById('th-islem-id');
    const zamanTh = document.getElementById('th-zaman');
    const rafNoTh = document.getElementById('th-raf-no');
    const adSoyadTh = document.getElementById('th-ad-soyad');

    if (rafNoTh) rafNoTh.style.display = 'none';

    if (type === 'kiyafet') {
        if(idTh) idTh.style.display = 'none';
        if(zamanTh) zamanTh.style.display = 'none';
        if(adSoyadTh) adSoyadTh.style.display = 'table-cell';
        if(islemTh) islemTh.style.display = 'table-cell';
    } else {
        if(idTh) idTh.style.display = 'table-cell';
        if(zamanTh) zamanTh.style.display = 'table-cell';
        if(adSoyadTh) adSoyadTh.style.display = 'table-cell';
        if (type === 'kirli') {
            if(islemTh) islemTh.style.display = 'table-cell';
        } else if (type === 'temiz') {
            if(islemTh) islemTh.style.display = 'table-cell';
            if(rafNoTh) rafNoTh.style.display = 'table-cell';
        } else {
            if(islemTh) islemTh.style.display = 'none';
        }
    }

    const tbody = document.getElementById('tablo-body');
    tbody.textContent = ''; // clear
    const trLoading = createEl('tr');
    const tdLoading = createEl('td', 'text-center py-8');
    tdLoading.colSpan = 5;
    tdLoading.textContent = 'Yükleniyor...';
    trLoading.appendChild(tdLoading);
    tbody.appendChild(trLoading);

    try {
        if (type === 'kiyafet') {
            await loadKiyafetPage(0, '');
            return;
        }

        const res = await apiFetch(`/api/v1/tablo/${type}`);
        const data = await res.json();

        tbody.textContent = '';
        if (data.length === 0) {
            const trEmpty = createEl('tr');
            const tdEmpty = createEl('td', 'text-center py-8 text-gray-500', 'Kayıt bulunamadı.');
            tdEmpty.colSpan = 5;
            trEmpty.appendChild(tdEmpty);
            tbody.appendChild(trEmpty);
            return;
        }

        data.forEach(row => {
            const tr = createEl('tr', 'hover:bg-gray-50 transition-colors');
            
            const tdId = createEl('td', 'py-4 px-6 font-medium text-gray-900 border-b border-gray-100', `#${row.islem_id}`);
            const tdRfid = createEl('td', 'py-4 px-6 border-b border-gray-100', row.rfid_tag || '-');
            
            const tdSicil = createEl('td', 'py-4 px-6 border-b border-gray-100');
            const spanSicil = createEl('span', 'bg-indigo-100 text-indigo-800 px-2 py-1 rounded text-xs font-bold border border-indigo-200', row.sicil_numarasi || '-');
            tdSicil.appendChild(spanSicil);

            const tdAd = createEl('td', 'py-4 px-6 border-b border-gray-100 whitespace-nowrap', row.ad_soyad || '-');
            
            tr.appendChild(tdId);
            tr.appendChild(tdRfid);
            tr.appendChild(tdSicil);
            tr.appendChild(tdAd);

            if (type === 'temiz') {
                const tdRaf = createEl('td', 'py-4 px-6 border-b border-gray-100 text-center');
                const spanRaf = createEl('span', 'bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-bold border border-yellow-200', `Raf ${row.raf_id || '?'}`);
                tdRaf.appendChild(spanRaf);
                tr.appendChild(tdRaf);
            }

            const formatZaman = row.zaman_damgasi ? new Date(row.zaman_damgasi).toLocaleString('tr-TR') : '';
            const tdZaman = createEl('td', 'py-4 px-6 text-gray-500 text-xs border-b border-gray-100', formatZaman);
            tr.appendChild(tdZaman);

            const tdAction = createEl('td', 'py-4 px-6 text-right border-b border-gray-100 whitespace-nowrap');
            if (type === 'kirli') {
                const btnOnay = createEl('button', 'bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors shadow-sm', 'Temizlendi');
                btnOnay.onclick = () => onaylaIslem(row.islem_id);
                tdAction.appendChild(btnOnay);
            } else if (type === 'temiz') {
                const btnTeslim = createEl('button', 'bg-indigo-500 hover:bg-indigo-600 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors shadow-sm mr-2', 'Teslim Et');
                btnTeslim.onclick = () => teslimEt(row.islem_id);
                tdAction.appendChild(btnTeslim);

                const btnBarkod = createEl('button', 'bg-gray-800 hover:bg-gray-900 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors shadow-sm', 'Barkod');
                btnBarkod.onclick = () => yazdirBarkod(row.raf_id || '?', row.sicil_numarasi || '', row.ad_soyad || '', row.zaman_damgasi || '', row.rfid_tag || '');
                tdAction.appendChild(btnBarkod);
            } else {
                tdAction.style.display = 'none';
            }
            tr.appendChild(tdAction);
            tbody.appendChild(tr);
        });

    } catch (err) {
        tbody.textContent = '';
        const trErr = createEl('tr');
        const tdErr = createEl('td', 'text-center py-8 text-red-500', 'Veriler yüklenirken hata oluştu!');
        tdErr.colSpan = 5;
        trErr.appendChild(tdErr);
        tbody.appendChild(trErr);
    }
}

async function onaylaIslem(islem_id) {
    if (!confirm("Kıyafet temizlendi olarak işaretlensin mi?")) return;

    try {
        const res = await fetchWithAuth('/api/v1/islem/onayla', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ islem_id })
        });

        if (res.ok) {
            showToast("Kıyafet başarıyla temizlendi & teslim edildi!");
            // Tabloyu yenile
            setupTableView('kirli');
        } else {
            showToast("Hata oluştu!", true);
        }
    } catch (err) {
        showToast("Sunucu hatası!", true);
    }
}

async function teslimEt(islem_id) {
    const p = prompt("Personel Sicil Numarasını Giriniz:");
    if (!p) return;
    
    const sicil_numarasi = p.trim();
    if (!sicil_numarasi) return;

    try {
        const res = await fetchWithAuth('/api/v1/islem/teslim', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ islem_id, sicil_numarasi })
        });

        if (res.ok) {
            showToast("Kıyafet başarıyla teslim edildi!");
            setupTableView('temiz');
        } else {
            const errData = await res.json();
            showToast(errData.detail || "Hata oluştu!", true);
        }
    } catch (err) {
        showToast("Sunucu hatası!", true);
    }
}

function removeTurkish(str) {
    const map = {
        'ç': 'c', 'Ç': 'C',
        'ğ': 'g', 'Ğ': 'G',
        'ş': 's', 'Ş': 'S',
        'ü': 'u', 'Ü': 'U',
        'ı': 'i', 'İ': 'I',
        'ö': 'o', 'Ö': 'O'
    };
    return str.replace(/[çÇğĞşŞüÜıİöÖ]/g, match => map[match] || match);
}

// Aktif barkod verisi (modal için state)
let _barkodData = null;

function yazdirBarkod(rafId, sicil, adSoyad, zamanDamgasi, rfidTag) {
    if (!window.QRious) {
        showToast("QRious kütüphanesi yüklenemedi!", true);
        return;
    }

    _barkodData = { rafId, sicil, adSoyad, zamanDamgasi, rfidTag };

    // QR canvas'ını doldur
    const canvas = document.getElementById('bc-qr');
    if (rfidTag) {
        new QRious({ element: canvas, value: rfidTag, size: 110, level: 'M', background: '#ffffff', foreground: '#1e1e2d' });
    } else {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, 110, 110);
        ctx.fillStyle = '#f3f4f6';
        ctx.fillRect(0, 0, 110, 110);
        ctx.fillStyle = '#9ca3af';
        ctx.font = '11px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('RFID yok', 55, 58);
    }

    const formatZaman = zamanDamgasi ? new Date(zamanDamgasi).toLocaleString('tr-TR') : '—';
    document.getElementById('bc-baslik').textContent  = 'LaundroStar';
    document.getElementById('bc-baslik2').textContent = `Raf ${rafId || '?'}`;
    document.getElementById('bc-raf').textContent     = `Raf: ${rafId || '?'}`;
    document.getElementById('bc-isim').textContent    = adSoyad || '—';
    document.getElementById('bc-sicil').textContent   = `Sicil: ${sicil || '—'}`;
    document.getElementById('bc-tarih').textContent   = `Tarih: ${formatZaman}`;
    document.getElementById('bc-rfid').textContent    = `RFID: ${rfidTag || '—'}`;

    document.getElementById('barkod-modal').classList.remove('hidden');
}

function _barkodPdfDoc() {
    if (!window.jspdf) { showToast("jsPDF yüklenemedi!", true); return null; }
    const { rafId, sicil, adSoyad, zamanDamgasi, rfidTag } = _barkodData;
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: [100, 50] });
    const formatZaman = zamanDamgasi ? new Date(zamanDamgasi).toLocaleString('tr-TR') : '?';
    const safeAd = removeTurkish(adSoyad || 'Bilinmiyor');

    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text("LaundroStar - Islem Barkodu", 50, 7, { align: "center" });
    doc.setLineWidth(0.5);
    doc.rect(4, 10, 92, 35);
    doc.setFontSize(14);
    doc.text("RAF: " + removeTurkish(rafId || '?'), 8, 18);
    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text("Sicil: " + removeTurkish(sicil || '?'), 8, 25);
    doc.text("Kisi: " + safeAd, 8, 31);
    doc.text("Tarih: " + formatZaman, 8, 37);
    doc.setFontSize(7);
    doc.text("RFID: " + (rfidTag || 'Yok'), 8, 42);
    if (rfidTag) {
        const qrDataUrl = document.getElementById('bc-qr').toDataURL('image/png');
        doc.addImage(qrDataUrl, 'PNG', 70, 15, 24, 24);
    }
    return { doc, safeName: removeTurkish(adSoyad || 'bilinmiyor').replace(/\s+/g, '_').toLowerCase(), rafId };
}

function barkodYazdir() {
    if (!_barkodData) return;
    const result = _barkodPdfDoc();
    if (!result) return;
    const { doc } = result;
    const blob = doc.output('blob');
    const url = URL.createObjectURL(blob);
    const win = window.open(url);
    if (win) {
        win.onload = () => { win.focus(); win.print(); };
    }
}

function barkodPngIndir() {
    if (!_barkodData) return;
    const canvas = document.getElementById('bc-qr');
    const link = document.createElement('a');
    link.download = `barkod_raf_${_barkodData.rafId || 'x'}_${removeTurkish(_barkodData.adSoyad || 'bilinmiyor').replace(/\s+/g,'_').toLowerCase()}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
}

async function editKiyafet(old_rfid, old_sicil) {
    const new_rfid = prompt("Yeni RFID Tag değerini giriniz:", old_rfid);
    if (new_rfid === null) return;
    const new_sicil = prompt("Yeni Sicil Numarasını giriniz:", old_sicil);
    if (new_sicil === null) return;

    if (!new_rfid.trim() || !new_sicil.trim()) {
        showToast("Alanlar boş bırakılamaz!", true);
        return;
    }

    try {
        const res = await fetchWithAuth(`/api/v1/kiyafet/${old_rfid}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rfid_tag: new_rfid.trim(), sicil_numarasi: new_sicil.trim() })
        });

        if (res.ok) {
            showToast("Eşleştirme güncellendi!");
            setupTableView('kiyafet');
        } else {
            const errData = await res.json();
            showToast(errData.detail || "Güncelleme hatası!", true);
        }
    } catch (err) {
        showToast("Sunucu hatası!", true);
    }
}

async function deleteKiyafet(rfid) {
    if (!confirm(`'${rfid}' id'li eşleştirmeyi silmek istediğinize emin misiniz?`)) return;

    try {
        const res = await fetchWithAuth(`/api/v1/kiyafet/${rfid}`, {
            method: 'DELETE'
        });

        if (res.ok) {
            showToast("Kayıt başarıyla silindi!");
            setupTableView('kiyafet');
        } else {
             const errData = await res.json();
             showToast(errData.detail || "Silme hatası!", true);
        }
    } catch (err) {
        showToast("Sunucu hatası!", true);
    }
}

function showToast(message, isError = false) {
    const toast = document.getElementById('toast');
    const msg = document.getElementById('toast-msg');
    const icon = toast.querySelector('i');

    // Reset background and icon classes safely
    toast.className = 'absolute top-5 right-5 text-white px-6 py-3 rounded shadow-lg transform transition-all duration-300 translate-x-full opacity-0 flex items-center z-50';
    icon.className = 'fas mr-2';

    if (isError) {
        toast.classList.add('bg-red-500');
        icon.classList.add('fa-times-circle');
    } else {
        toast.classList.add('bg-green-500');
        icon.classList.add('fa-check-circle');
    }

    msg.innerText = message;

    // Show toast
    toast.classList.remove('translate-x-full', 'opacity-0');

    // Hide toast after 3 seconds
    setTimeout(() => {
        toast.classList.add('translate-x-full', 'opacity-0');
    }, 3000);
}

async function initMock() {
    try {
        const res = await fetchWithAuth('/api/init_mock_data', { method: 'POST' });
        const data = await res.json();
        showToast(data.message);
    } catch (e) {
        showToast("Mock veri eklenemedi", true);
    }
}

// === AUTH & SECURITY ===

async function fetchWithAuth(url, options = {}) {
    const token = AppState.token;
    options.headers = options.headers || {};

    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }

    // CSRF: mutating isteklerde cookie'deki csrf_token header olarak gönderilmeli
    // (Double Submit Cookie — CSRFMiddleware aksi halde 403 döner).
    const method = (options.method || 'GET').toUpperCase();
    if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
        const csrfMatch = document.cookie.match(/csrf_token=([^;]+)/);
        if (csrfMatch) {
            options.headers['x-csrf-token'] = csrfMatch[1];
        }
    }

    const response = await fetch(url, options);
    if (response.status === 401 && !url.includes('/api/v1/auth/token')) {
        logout();
        throw new Error('Unauthorized');
    }
    return response;
}

async function fetchUserInfo() {
    try {
        const res = await fetchWithAuth('/api/v1/users/me');
        if (res.ok) {
            const user = await res.json();
            currentUserRole = user.role;
            document.getElementById('header-username').innerText = user.username.toUpperCase();
            document.getElementById('login-modal').classList.add('hidden');
            
            // Adjust UI for role
            if (user.role === 'admin') {
                document.getElementById('header-role').innerText = "YÖNETİCİ";
                document.getElementById('admin-menu-header').classList.remove('hidden');
                document.getElementById('admin-menu-teslim').classList.remove('hidden');
                document.getElementById('admin-audit-header').classList.remove('hidden');
                document.getElementById('admin-menu-audit').classList.remove('hidden');
                document.getElementById('menu-rfid-eslestirme')?.classList.remove('hidden');
                document.getElementById('admin-menu-kiyafet')?.classList.remove('hidden');
                document.getElementById('admin-edge-header')?.classList.remove('hidden');
                document.getElementById('admin-menu-edge')?.classList.remove('hidden');
            } else {
                document.getElementById('header-role').innerText = "PERSONEL";
                document.getElementById('admin-menu-header').classList.add('hidden');
                document.getElementById('admin-menu-teslim').classList.add('hidden');
                document.getElementById('admin-audit-header').classList.add('hidden');
                document.getElementById('admin-menu-audit').classList.add('hidden');
                document.getElementById('menu-rfid-eslestirme')?.classList.add('hidden');
                document.getElementById('admin-menu-kiyafet')?.classList.add('hidden');
                document.getElementById('admin-edge-header')?.classList.add('hidden');
                document.getElementById('admin-menu-edge')?.classList.add('hidden');
            }
            
            // Setup Avatar if exists
            if (user.profile_photo) {
                document.getElementById('header-avatar-img').src = user.profile_photo;
                document.getElementById('header-avatar-img').classList.remove('hidden');
                document.getElementById('header-avatar-icon').classList.add('hidden');
            } else {
                document.getElementById('header-avatar-img').classList.add('hidden');
                document.getElementById('header-avatar-icon').classList.remove('hidden');
            }
            
            loadDashboard();
        } else {
            showLoginModal();
        }
    } catch (err) {
        console.error("Auth check failed", err);
        showLoginModal();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const btn = document.getElementById('login-btn');
    const errObj = document.getElementById('login-error');
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    
    btn.textContent = ''; const i=createEl('i','fas fa-spinner fa-spin mr-2'); btn.appendChild(i); btn.appendChild(document.createTextNode(' Bekleyin...'));
    btn.disabled = true;
    errObj.classList.add('hidden');
    
    try {
        const params = new URLSearchParams();
        params.append('username', username);
        params.append('password', password);

        const res = await apiFetch('/api/v1/auth/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params
        });
        
        if (res.ok) {
            const data = await res.json();
            document.getElementById('login-password').value = '';

            // MFA aktifse ikinci faktör (TOTP) iste — ADR 0007
            if (data.mfa_required) {
                const ok = await handleMfaChallenge(data.mfa_token, errObj);
                if (!ok) return;
            } else if (data.access_token) {
                AppState.token = data.access_token;
            }

            if (data.mfa_enrollment_required) {
                // Politika gereği admin MFA tanımlamalı; profil/güvenlik ekranına yönlendirme önerisi
                console.warn('MFA kaydı zorunlu: Lütfen güvenlik ayarlarından MFA etkinleştirin.');
            }

            await fetchUserInfo();
        } else {
            errObj.innerText = "Kullanıcı adı veya şifre hatalı!";
            errObj.classList.remove('hidden');
        }
    } catch (err) {
        errObj.innerText = "Sunucuya bağlanılamadı!";
        errObj.classList.remove('hidden');
    } finally {
        btn.textContent = ''; const i=createEl('i','fas fa-lock mr-2'); btn.appendChild(i); btn.appendChild(document.createTextNode(' Giriş Yap'));
        btn.disabled = false;
    }
}

// MFA ikinci faktör akışı (ADR 0007). Authenticator'dan 6 haneli kod ister,
// /auth/mfa/verify ile doğrular ve access token'ı AppState'e yazar.
async function handleMfaChallenge(mfaToken, errObj) {
    const code = window.prompt("İki faktörlü doğrulama: Authenticator uygulamanızdaki 6 haneli kodu girin");
    if (!code) {
        if (errObj) { errObj.innerText = "MFA doğrulaması iptal edildi."; errObj.classList.remove('hidden'); }
        return false;
    }
    const verifyRes = await apiFetch('/api/v1/auth/mfa/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mfa_token: mfaToken, code: code.trim() })
    });
    if (verifyRes.ok) {
        const vdata = await verifyRes.json();
        AppState.token = vdata.access_token;
        return true;
    }
    if (errObj) { errObj.innerText = "Doğrulama kodu hatalı veya süresi dolmuş."; errObj.classList.remove('hidden'); }
    return false;
}

function showLoginModal() {
    document.getElementById('login-modal').classList.remove('hidden');
}

function toggleUserMenu(e) {
    if (e) e.stopPropagation();
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
}

// Dropdown'u dışarıya veya menü öğelerine tıklayınca kapatmak için
document.addEventListener('click', function(event) {
    const dropdown = document.getElementById('user-dropdown');
    if (dropdown && !dropdown.classList.contains('hidden')) {
        dropdown.classList.add('hidden');
    }
});

function logout(e) {
    if (e) e.preventDefault();
    
    currentUserRole = null;
    document.getElementById('user-dropdown').classList.add('hidden');
    showLoginModal();
}

async function showProfile() {
    // Hide all views
    document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
    
    const view = document.getElementById('profile-view');
    view.classList.add('active');
    
    document.getElementById('page-title').innerText = "Kullanıcı Profili";
    
    // Fetch latest user data
    try {
        const res = await fetchWithAuth('/api/v1/users/me');
        if (res.ok) {
            const data = await res.json();
            document.getElementById('profile-display-name').innerText = data.username.toUpperCase();
            document.getElementById('profile-display-role').innerText = data.role.toUpperCase();
            
            document.getElementById('profile-title').value = data.title || '';
            document.getElementById('profile-company').value = data.company || '';
            document.getElementById('profile-email').value = data.email || '';
            document.getElementById('profile-phone').value = data.phone || '';
            document.getElementById('profile-password').value = ''; // Don't show password
            
            if (data.profile_photo) {
                document.getElementById('profile-photo-preview').src = data.profile_photo;
                document.getElementById('profile-photo-preview').classList.remove('hidden');
                document.getElementById('profile-photo-icon').classList.add('hidden');
            }
            
            // Admin Panel Visibility
            if (currentUserRole === 'admin') {
                document.getElementById('admin-user-management').classList.remove('hidden');
                loadAdminUsers();
            } else {
                document.getElementById('admin-user-management').classList.add('hidden');
            }
        }
    } catch (e) {
        console.error("Profil verisi alınamadı", e);
    }
}

async function handlePhotoSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    if (file.type !== "image/png") {
        showToast("Sadece PNG formatında fotoğraf yükleyebilirsiniz!", true);
        return;
    }
    
    if (file.size > 2 * 1024 * 1024) {
        showToast("Dosya boyutu 2MB'den küçük olmalıdır!", true);
        return;
    }
    
    const formData = new FormData();
    formData.append("file", file);
    
    try {
        const token = AppState.token;
        const res = await apiFetch('/api/v1/users/me/photo', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });
        
        if (res.ok) {
            const data = await res.json();
            showToast("Profil fotoğrafı başarıyla güncellendi!");
            
            if (data.profile_photo) {
                const imgUrl = data.profile_photo + "?t=" + new Date().getTime(); // Prevent caching
                document.getElementById('profile-photo-preview').src = imgUrl;
                document.getElementById('profile-photo-preview').classList.remove('hidden');
                document.getElementById('profile-photo-icon').classList.add('hidden');
                
                document.getElementById('header-avatar-img').src = imgUrl;
                document.getElementById('header-avatar-img').classList.remove('hidden');
                document.getElementById('header-avatar-icon').classList.add('hidden');
            }
        } else {
            const errorData = await res.json();
            showToast("Hata: " + errorData.detail, true);
        }
    } catch (err) {
        console.error(err);
        showToast("Fotoğraf yüklenirken bağlantı hatası oluştu", true);
    }
}

async function handleProfileUpdate(e) {
    e.preventDefault();
    
    const payload = {
        title: document.getElementById('profile-title').value,
        company: document.getElementById('profile-company').value,
        email: document.getElementById('profile-email').value,
        phone: document.getElementById('profile-phone').value,
        password: document.getElementById('profile-password').value || null
    };

    try {
        const res = await fetchWithAuth('/api/v1/users/me', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            showToast("Profil başarıyla güncellendi!");
            const data = await res.json();
            // Header'ı da yenileriz
            if (data.profile_photo) {
                 document.getElementById('header-avatar-img').src = data.profile_photo;
                 document.getElementById('header-avatar-img').classList.remove('hidden');
                 document.getElementById('header-avatar-icon').classList.add('hidden');
            }
            if(data.password) {
                 document.getElementById('profile-password').value = ''; 
            }
        } else {
             const errorData = await res.json();
             showToast("Hata: " + errorData.detail, true);
        }
    } catch (err) {
        console.error(err);
        showToast("Bağlantı hatası", true);
    }
}

// === ADMIN USER MANAGEMENT ===

async function loadAdminUsers() {
    const tbody = document.getElementById('admin-users-table-body');
    tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-gray-500"><i class="fas fa-spinner fa-spin mr-2"></i>Kullanıcılar yükleniyor...</td></tr>';
    
    try {
        const res = await fetchWithAuth('/api/v1/users');
        if (res.ok) {
            const users = await res.json();
            
            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-gray-500">Hiç kullanıcı bulunamadı.</td></tr>';
                return;
            }
            
            tbody.innerHTML = users.map(u => {
                const roleBadge = u.role === 'admin' 
                    ? '<span class="px-2 py-1 bg-red-100 text-red-800 rounded-md text-xs font-bold">Admin</span>' 
                    : '<span class="px-2 py-1 bg-blue-100 text-blue-800 rounded-md text-xs font-bold">Personel</span>';
                    
                const isCurrentUser = u.username === document.getElementById('profile-display-name').innerText.toLowerCase();
                const deleteBtn = isCurrentUser 
                    ? `<span class="text-gray-400 text-xs italic" title="Kendinizi silemezsiniz">Silinemez</span>` 
                    : `<button onclick="deleteUser(${u.id}, '${u.username}')" class="text-red-500 hover:text-red-700 transition-colors bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-md text-sm font-medium"><i class="fa-solid fa-trash-alt mr-1"></i> Sil</button>`;
                    
                return `
                <tr class="hover:bg-gray-50 transition-colors">
                    <td class="py-3 px-4 border-b border-gray-100">
                        <div class="font-bold text-gray-800">${u.username}</div>
                        ${u.email ? `<div class="text-xs text-gray-500">${u.email}</div>` : ''}
                    </td>
                    <td class="py-3 px-4 border-b border-gray-100">${roleBadge}</td>
                    <td class="py-3 px-4 border-b border-gray-100">
                        <div class="text-sm font-medium text-gray-700">${u.title || '-'}</div>
                        <div class="text-xs text-gray-500">${u.company || '-'}</div>
                    </td>
                    <td class="py-3 px-4 border-b border-gray-100 text-right">
                        ${deleteBtn}
                    </td>
                </tr>
                `;
            }).join('');
        } else {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-red-500">Kullanıcılar yüklenemedi. Yetkiniz olmayabilir.</td></tr>';
        }
    } catch (e) {
        console.error("Kullanıcılar yüklenirken hata:", e);
        tbody.innerHTML = '<tr><td colspan="4" class="text-center py-4 text-red-500">Sunucu bağlantı hatası.</td></tr>';
    }
}

async function handleCreateUser(e) {
    e.preventDefault();
    
    const btn = document.getElementById('btn-create-user');
    const originalText = btn.innerHTML;
    btn.textContent = ''; const i=createEl('i','fas fa-spinner fa-spin mr-2'); btn.appendChild(i); btn.appendChild(document.createTextNode(' Oluşturuluyor...'));
    btn.disabled = true;
    
    const payload = {
        username: document.getElementById('new-user-username').value,
        password: document.getElementById('new-user-password').value,
        role: document.getElementById('new-user-role').value,
        title: document.getElementById('new-user-title').value || null,
        company: document.getElementById('new-user-company').value || null
    };
    
    try {
        const res = await fetchWithAuth('/api/v1/users', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (res.ok) {
            showToast("Kullanıcı başarıyla oluşturuldu!");
            document.getElementById('admin-add-user-form').reset();
            loadAdminUsers();
        } else {
            const errorData = await res.json();
            showToast("Hata: " + errorData.detail, true);
        }
    } catch (err) {
        console.error(err);
        showToast("Bağlantı hatası", true);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function deleteUser(userId, username) {
    if (!confirm(`'${username}' adlı kullanıcıyı silmek istediğinize emin misiniz? Bu işlem geri alınamaz.`)) {
        return;
    }
    
    try {
        const res = await fetchWithAuth(`/api/v1/users/${userId}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            showToast("Kullanıcı başarıyla silindi!");
            loadAdminUsers();
        } else {
            const errorData = await res.json();
            showToast("Hata: " + errorData.detail, true);
        }
    } catch (err) {
        console.error(err);
        showToast("Bağlantı hatası", true);
    }
}

// === AUDIT LOGS ===

const ACTION_LABELS = {
    LOGIN_SUCCESS:  { label: 'Başarılı Giriş',        badge: 'bg-green-100 text-green-800' },
    LOGIN_FAIL:     { label: 'Başarısız Giriş',        badge: 'bg-red-100 text-red-800' },
    KIRLI_GIRIS:    { label: 'Kirli Giriş',           badge: 'bg-orange-100 text-orange-800' },
    TEMIZ_GIRIS:    { label: 'Temiz Giriş',           badge: 'bg-blue-100 text-blue-800' },
    TESLIM_GIRIS:   { label: 'Teslim Giriş',          badge: 'bg-purple-100 text-purple-800' },
    ISLEM_ONAYLA:   { label: 'İşlem Onayı',            badge: 'bg-teal-100 text-teal-800' },
    USER_CREATE:    { label: 'Kullanıcı Oluşturma',   badge: 'bg-indigo-100 text-indigo-800' },
    USER_DELETE:    { label: 'Kullanıcı Silme',       badge: 'bg-red-100 text-red-900' },
    USER_UPDATE:    { label: 'Kullanıcı Güncelleme', badge: 'bg-yellow-100 text-yellow-800' },
    PROFILE_UPDATE: { label: 'Profil Güncelleme',    badge: 'bg-gray-100 text-gray-800' },
};

async function loadAuditLogs() {
    const tbody = document.getElementById('audit-log-body');
    if (!tbody) return;

    tbody.textContent = '';
    const trLoading = createEl('tr');
    const tdLoading = createEl('td', 'text-center py-6', 'Yükleniyor...');
    tdLoading.colSpan = 6;
    trLoading.appendChild(tdLoading);
    tbody.appendChild(trLoading);

    try {
        const res = await apiFetch('/api/v1/audit-logs?limit=200');
        if (!res.ok) {
            tbody.textContent = '';
            const trErr = createEl('tr');
            const tdErr = createEl('td', 'text-center py-6 text-red-500', 'Loglar yüklenemedi.');
            tdErr.colSpan = 6;
            trErr.appendChild(tdErr);
            tbody.appendChild(trErr);
            return;
        }

        const logs = await res.json();
        tbody.textContent = '';
        if (logs.length === 0) {
            const trEmpty = createEl('tr');
            const tdEmpty = createEl('td', 'text-center py-6 text-gray-400', 'Kayıt bulunamadı.');
            tdEmpty.colSpan = 6;
            trEmpty.appendChild(tdEmpty);
            tbody.appendChild(trEmpty);
            return;
        }

        logs.forEach(log => {
            const tr = createEl('tr', 'border-b border-gray-100 hover:bg-gray-50 transition-colors');
            tr.appendChild(createEl('td', 'py-3 px-4 text-sm text-gray-500', new Date(log.timestamp).toLocaleString('tr-TR')));
            tr.appendChild(createEl('td', 'py-3 px-4 font-medium text-gray-900', log.username || '-'));
            
            const actionTd = createEl('td', 'py-3 px-4 text-sm');
            const actionSpan = createEl('span', 'bg-gray-100 text-gray-700 px-2 py-1 rounded border border-gray-200 font-mono text-xs', log.action);
            actionTd.appendChild(actionSpan);
            tr.appendChild(actionTd);
            
            tr.appendChild(createEl('td', 'py-3 px-4 text-sm text-gray-600', log.detail || '-'));
            tr.appendChild(createEl('td', 'py-3 px-4 text-xs text-gray-400 font-mono', log.ip_address || '-'));
            
            const statusTd = createEl('td', 'py-3 px-4 text-right');
            const isSuccess = log.status === 'success';
            const sClass = isSuccess ? 'bg-green-100 text-green-700 border-green-200' : 'bg-red-100 text-red-700 border-red-200';
            const statusSpan = createEl('span', `${sClass} px-2 py-1 rounded text-xs font-bold border`, log.status);
            statusTd.appendChild(statusSpan);
            tr.appendChild(statusTd);
            
            tbody.appendChild(tr);
        });

    } catch (err) {
        tbody.textContent = '';
        const trErr = createEl('tr');
        const tdErr = createEl('td', 'text-center py-6 text-red-500', 'Sunucu bağlantı hatası.');
        tdErr.colSpan = 6;
        trErr.appendChild(tdErr);
        tbody.appendChild(trErr);
    }
}

function clearAuditFilters() {
    document.getElementById('audit-filter-user').value = '';
    document.getElementById('audit-filter-action').value = '';
    loadAuditLogs();
}

// ---------------------------------------------------------------------------
// Edge Cihazlar (Gateway Network — onay/iptal)
// ---------------------------------------------------------------------------
const EDGE_STATUS_BADGE = {
    pending: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    approved: 'bg-green-100 text-green-700 border-green-200',
    revoked: 'bg-red-100 text-red-700 border-red-200',
};
const EDGE_STATUS_LABEL = { pending: 'BEKLEMEDE', approved: 'ONAYLI', revoked: 'İPTAL' };

async function loadEdgeDevices() {
    const tbody = document.getElementById('edge-devices-body');
    if (!tbody) return;
    tbody.textContent = '';
    const trLoading = createEl('tr');
    const tdLoading = createEl('td', 'text-center py-6', 'Yükleniyor...');
    tdLoading.colSpan = 7;
    trLoading.appendChild(tdLoading);
    tbody.appendChild(trLoading);

    try {
        const res = await apiFetch('/api/v1/edge/devices');
        if (!res.ok) {
            tbody.textContent = '';
            const tr = createEl('tr');
            const td = createEl('td', 'text-center py-6 text-red-500', 'Cihazlar yüklenemedi.');
            td.colSpan = 7; tr.appendChild(td); tbody.appendChild(tr);
            return;
        }
        const body = await res.json();
        const devices = body.data || [];
        tbody.textContent = '';
        if (devices.length === 0) {
            const tr = createEl('tr');
            const td = createEl('td', 'text-center py-6 text-gray-400', 'Henüz kayıtlı edge cihaz yok.');
            td.colSpan = 7; tr.appendChild(td); tbody.appendChild(tr);
            return;
        }

        devices.forEach(d => {
            const tr = createEl('tr', 'border-b border-gray-100 hover:bg-gray-50 transition-colors');

            const statusTd = createEl('td', 'py-3 px-4');
            const sClass = EDGE_STATUS_BADGE[d.status] || 'bg-gray-100 text-gray-700 border-gray-200';
            statusTd.appendChild(createEl('span', `${sClass} px-2 py-1 rounded text-xs font-bold border`, EDGE_STATUS_LABEL[d.status] || d.status));
            tr.appendChild(statusTd);

            tr.appendChild(createEl('td', 'py-3 px-4 font-medium text-gray-900', d.name || '-'));
            tr.appendChild(createEl('td', 'py-3 px-4 text-sm text-gray-600', d.location || '-'));

            const hw = Array.isArray(d.hardware)
                ? d.hardware.map(h => `${h.model || h.type || '?'}`).join(', ')
                : '-';
            tr.appendChild(createEl('td', 'py-3 px-4 text-sm text-gray-600', hw || '-'));
            tr.appendChild(createEl('td', 'py-3 px-4 text-xs text-gray-400 font-mono', d.device_uid));
            tr.appendChild(createEl('td', 'py-3 px-4 text-xs text-gray-400', d.last_seen_at ? new Date(d.last_seen_at).toLocaleString('tr-TR') : '-'));

            const actionTd = createEl('td', 'py-3 px-4 text-right');
            if (d.status !== 'approved') {
                const approveBtn = createEl('button', 'bg-green-600 hover:bg-green-700 text-white text-xs font-bold py-1.5 px-3 rounded transition-colors mr-2', 'Onayla');
                approveBtn.onclick = () => approveEdgeDevice(d.id, d.name);
                actionTd.appendChild(approveBtn);
            }
            if (d.status !== 'revoked') {
                const revokeBtn = createEl('button', 'bg-gray-100 hover:bg-red-100 text-red-700 text-xs font-bold py-1.5 px-3 rounded border border-red-200 transition-colors', 'İptal');
                revokeBtn.onclick = () => revokeEdgeDevice(d.id, d.name);
                actionTd.appendChild(revokeBtn);
            }
            tr.appendChild(actionTd);
            tbody.appendChild(tr);
        });
    } catch (err) {
        tbody.textContent = '';
        const tr = createEl('tr');
        const td = createEl('td', 'text-center py-6 text-red-500', 'Sunucu bağlantı hatası.');
        td.colSpan = 7; tr.appendChild(td); tbody.appendChild(tr);
    }
}

async function approveEdgeDevice(id, name) {
    try {
        const res = await apiFetch(`/api/v1/edge/devices/${id}/approve`, { method: 'POST' });
        if (res.ok) {
            showToast(`Cihaz onaylandı: ${name || id}`);
            loadEdgeDevices();
        } else {
            showToast('Onaylama başarısız.', 'error');
        }
    } catch (err) {
        showToast('Sunucu bağlantı hatası.', 'error');
    }
}

async function revokeEdgeDevice(id, name) {
    try {
        const res = await apiFetch(`/api/v1/edge/devices/${id}/revoke`, { method: 'POST' });
        if (res.ok) {
            showToast(`Cihaz iptal edildi: ${name || id}`);
            loadEdgeDevices();
        } else {
            showToast('İptal başarısız.', 'error');
        }
    } catch (err) {
        showToast('Sunucu bağlantı hatası.', 'error');
    }
}

// ---------------------------------------------------------------------------
// Raf Simülasyonu
// ---------------------------------------------------------------------------

let currentRack = 'A';
let rackStatsCache = null;
let rackDetailCache = {};

async function selectRack(letter) {
    currentRack = letter;

    // Tab UI güncelle
    document.querySelectorAll('.rack-tab').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.rack === letter);
    });

    // Veriyi çek ve grid'i oluştur
    try {
        const [statsRes, detailRes] = await Promise.all([
            fetchWithAuth('/api/v1/stats/raflar'),
            fetchWithAuth(`/api/v1/stats/raf-detay/${letter}`)
        ]);

        if (statsRes.ok) rackStatsCache = await statsRes.json();
        if (detailRes.ok) rackDetailCache[letter] = await detailRes.json();

        renderRackGrid(letter);
    } catch (err) {
        console.error('Raf verisi yüklenemedi:', err);
    }
}

function renderRackGrid(letter) {
    const grid = document.getElementById('rack-grid');
    const rackData = rackStatsCache?.[letter] || {};
    const detailData = rackDetailCache[letter] || {};

    let totalItems = 0;
    let totalCapacity = 0;

    let html = '';
    for (let floor = 1; floor <= 7; floor++) {
        html += '<div class="grid grid-cols-5 gap-2">';
        // Bölmeler sağdan sola: 5, 4, 3, 2, 1
        for (let comp = 5; comp >= 1; comp--) {
            const rafId = `${letter}${floor}${comp}`;
            const info = rackData[rafId] || { count: 0, capacity: floor === 7 ? 1 : 3 };
            const count = info.count;
            const capacity = info.capacity;

            totalItems += count;
            totalCapacity += capacity;

            let cellClass = 'empty';
            if (count > 0 && count < capacity) cellClass = 'partial';
            if (count >= capacity) cellClass = 'full';

            html += `
                <div class="rack-cell ${cellClass}"
                     data-raf-id="${rafId}"
                     onmouseenter="showRackPopup(event, '${rafId}', ${count}, ${capacity})"
                     onmousemove="moveRackPopup(event)"
                     onmouseleave="hideRackPopup()">
                    <span class="text-xs font-bold text-gray-700">${rafId}</span>
                    <span class="text-[11px] font-semibold ${count >= capacity ? 'text-red-600' : count > 0 ? 'text-amber-600' : 'text-emerald-600'}">${count}/${capacity}</span>
                </div>
            `;
        }
        html += '</div>';
    }

    grid.innerHTML = html;

    // Özet
    const summaryEl = document.getElementById('rack-summary-text');
    if (summaryEl) {
        const pct = totalCapacity > 0 ? ((totalItems / totalCapacity) * 100).toFixed(0) : 0;
        summaryEl.textContent = `${letter} Rafı: ${totalItems} / ${totalCapacity} (%${pct} dolu)`;
    }
}

function showRackPopup(event, rafId, count, capacity) {
    const popup = document.getElementById('rack-popup');
    const detailData = rackDetailCache[currentRack] || {};
    const items = detailData[rafId] || [];

    let statusColor = 'emerald';
    let statusText = 'Boş';
    if (count > 0 && count < capacity) { statusColor = 'amber'; statusText = 'Kısmen Dolu'; }
    if (count >= capacity) { statusColor = 'red'; statusText = 'Dolu'; }

    let html = `
        <div class="px-3 py-2.5 bg-gray-50 border-b border-gray-200 rounded-t-xl flex items-center justify-between gap-3">
            <div>
                <span class="font-bold text-gray-800 text-sm">${rafId}</span>
                <span class="text-[11px] text-gray-400 ml-1.5">${count}/${capacity} kapasite</span>
            </div>
            <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-${statusColor}-100 text-${statusColor}-700 shrink-0">${statusText}</span>
        </div>
    `;

    if (items.length > 0) {
        html += '<div class="p-2.5 space-y-1.5">';
        items.forEach((item, idx) => {
            const tarih = item.zaman_damgasi
                ? new Date(item.zaman_damgasi).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' })
                : '-';
            html += `
                <div class="bg-white rounded-lg px-2.5 py-2 border border-gray-100 text-xs">
                    <div class="flex justify-between items-center">
                        <span class="font-bold text-gray-800">${item.ad_soyad}</span>
                        <span class="text-[10px] text-gray-300 ml-2 shrink-0">#${idx + 1}</span>
                    </div>
                    <div class="flex items-center gap-3 text-gray-400 mt-0.5">
                        <span><i class="fas fa-id-badge mr-1 text-indigo-300"></i>${item.sicil_numarasi}</span>
                        <span><i class="fas fa-tag mr-1 text-indigo-300"></i>${item.rfid_tag}</span>
                        <span class="ml-auto"><i class="fas fa-clock mr-1"></i>${tarih}</span>
                    </div>
                </div>
            `;
        });
        html += '</div>';
    } else {
        html += '<div class="px-3 py-3 text-center text-xs text-gray-400"><i class="fas fa-inbox mr-1 text-gray-300"></i>Bu bölmede kıyafet yok</div>';
    }

    popup.innerHTML = html;
    popup.classList.remove('hidden');
    moveRackPopup(event);
}

function moveRackPopup(event) {
    const popup = document.getElementById('rack-popup');
    const offset = 16;
    let x = event.clientX + offset;
    let y = event.clientY + offset;

    // Ekran dışına taşma kontrolü
    const rect = popup.getBoundingClientRect();
    if (x + rect.width > window.innerWidth) x = event.clientX - rect.width - offset;
    if (y + rect.height > window.innerHeight) y = event.clientY - rect.height - offset;

    popup.style.left = x + 'px';
    popup.style.top = y + 'px';
}

function hideRackPopup() {
    document.getElementById('rack-popup').classList.add('hidden');
}

// ---------------------------------------------------------------------------
// Tablo Arama
// ---------------------------------------------------------------------------

let _currentTabloType = null;
let _tabloSearchTimer = null;
const KIYAFET_PAGE_SIZE = 50;

function filterTable(query) {
    if (_currentTabloType !== 'kiyafet') {
        // Diğer tablolar için eski DOM filtresi yeterli (max 50 kayıt)
        const q = query.trim().toLowerCase();
        const tbody = document.getElementById('tablo-body');
        const countEl = document.getElementById('tablo-search-count');
        const rows = tbody.querySelectorAll('tr');
        if (!rows.length) return;
        let visible = 0;
        rows.forEach(row => {
            const text = row.innerText.toLowerCase();
            const match = !q || text.includes(q);
            row.style.display = match ? '' : 'none';
            if (match) visible++;
        });
        if (q) { countEl.textContent = `${visible} sonuç`; countEl.classList.remove('hidden'); }
        else { countEl.classList.add('hidden'); }
        return;
    }
    // kiyafet tablosu: debounce + API
    clearTimeout(_tabloSearchTimer);
    _tabloSearchTimer = setTimeout(() => loadKiyafetPage(0, query.trim()), 300);
}

async function loadKiyafetPage(offset, q) {
    const tbody = document.getElementById('tablo-body');
    const countEl = document.getElementById('tablo-search-count');
    const params = new URLSearchParams({ limit: KIYAFET_PAGE_SIZE, offset });
    if (q) params.set('q', q);

    tbody.innerHTML = '<tr><td colspan="4" class="text-center py-6"><i class="fas fa-spinner fa-spin text-indigo-500 text-xl"></i></td></tr>';

    const res = await fetchWithAuth(`/api/v1/tablo/kiyafet?${params}`);
    const json = await res.json();
    const { total, data } = json;

    if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center py-8 text-gray-500">Kayıt bulunamadı.</td></tr>';
        countEl.classList.add('hidden');
        return;
    }

    tbody.innerHTML = data.map(row => `
        <tr class="hover:bg-gray-50 transition-colors">
            <td class="py-4 px-6 border-b border-gray-100 font-medium whitespace-nowrap">${row.rfid_tag || '-'}</td>
            <td class="py-4 px-6 border-b border-gray-100"><span class="bg-indigo-100 text-indigo-800 px-2 py-1 rounded text-xs font-bold border border-indigo-200">${row.sicil_numarasi || '-'}</span></td>
            <td class="py-4 px-6 border-b border-gray-100 whitespace-nowrap">${row.ad_soyad || '-'}</td>
            <td class="py-4 px-6 text-right border-b border-gray-100 whitespace-nowrap">
                <button onclick="editKiyafet('${row.rfid_tag}', '${row.sicil_numarasi}')" class="text-blue-500 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-md text-sm font-medium mr-2 transition-colors"><i class="fas fa-edit"></i></button>
                <button onclick="deleteKiyafet('${row.rfid_tag}')" class="text-red-500 hover:text-red-700 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-md text-sm font-medium transition-colors"><i class="fas fa-trash-alt"></i></button>
            </td>
        </tr>
    `).join('');

    // Sayfalama bilgisi
    const showing = Math.min(offset + KIYAFET_PAGE_SIZE, total);
    countEl.textContent = `${offset + 1}–${showing} / ${total} kayıt`;
    countEl.classList.remove('hidden');

    // Sayfalama kontrolleri
    let pagerEl = document.getElementById('kiyafet-pager');
    if (!pagerEl) {
        pagerEl = document.createElement('div');
        pagerEl.id = 'kiyafet-pager';
        pagerEl.className = 'flex justify-between items-center px-6 py-3 border-t border-gray-100 text-sm';
        document.getElementById('tablo-body').closest('table').parentElement.appendChild(pagerEl);
    }
    const prevDisabled = offset === 0 ? 'opacity-40 cursor-not-allowed' : 'hover:bg-gray-100 cursor-pointer';
    const nextDisabled = showing >= total ? 'opacity-40 cursor-not-allowed' : 'hover:bg-gray-100 cursor-pointer';
    const currentQ = document.getElementById('tablo-search')?.value.trim() || '';
    pagerEl.innerHTML = `
        <button class="px-3 py-1.5 rounded border border-gray-200 ${prevDisabled}"
            ${offset === 0 ? 'disabled' : `onclick="loadKiyafetPage(${offset - KIYAFET_PAGE_SIZE}, '${currentQ.replace(/'/g,"\\'")}')"`}>
            ← Önceki
        </button>
        <span class="text-gray-400">${Math.floor(offset/KIYAFET_PAGE_SIZE)+1} / ${Math.ceil(total/KIYAFET_PAGE_SIZE)} sayfa</span>
        <button class="px-3 py-1.5 rounded border border-gray-200 ${nextDisabled}"
            ${showing >= total ? 'disabled' : `onclick="loadKiyafetPage(${offset + KIYAFET_PAGE_SIZE}, '${currentQ.replace(/'/g,"\\'")}')"`}>
            Sonraki →
        </button>
    `;
}

// Tablo yüklendiğinde arama kutusunu sıfırla
function resetTableSearch() {
    const input = document.getElementById('tablo-search');
    const countEl = document.getElementById('tablo-search-count');
    if (input) input.value = '';
    if (countEl) countEl.classList.add('hidden');
    const pager = document.getElementById('kiyafet-pager');
    if (pager) pager.remove();
}

// ---------------------------------------------------------------------------
// Raf Simülasyonu — Kişi/Sicil Arama
// ---------------------------------------------------------------------------

async function rafSearch(query) {
    const q = query.trim().toLowerCase();
    const resultEl = document.getElementById('raf-search-result');

    if (!q) {
        resultEl.classList.add('hidden');
        resultEl.innerHTML = '';
        // Highlight temizle
        document.querySelectorAll('.rack-cell.search-highlight').forEach(el => {
            el.classList.remove('search-highlight');
        });
        return;
    }

    // Tüm raf detaylarını tara — önce yüklenmemiş rafları çek
    const LETTERS = ['A','B','C','D','E','F','G','H'];
    const missing = LETTERS.filter(l => !rackDetailCache[l]);
    if (missing.length) {
        await Promise.all(missing.map(async l => {
            const res = await fetchWithAuth(`/api/v1/stats/raf-detay/${l}`);
            if (res.ok) rackDetailCache[l] = await res.json();
        }));
    }

    // Ara
    const bulunanlar = [];
    for (const letter of LETTERS) {
        const rafData = rackDetailCache[letter] || {};
        for (const [rafId, items] of Object.entries(rafData)) {
            for (const item of items) {
                const adSoyad = (item.ad_soyad || '').toLowerCase();
                const sicil = (item.sicil_numarasi || '').toLowerCase();
                const rfid = (item.rfid_tag || '').toLowerCase();
                if (adSoyad.includes(q) || sicil.includes(q) || rfid.includes(q)) {
                    bulunanlar.push({ ...item, rafId, rack: letter });
                }
            }
        }
    }

    resultEl.classList.remove('hidden');

    if (!bulunanlar.length) {
        resultEl.innerHTML = `
            <div class="flex items-center gap-2 text-sm text-gray-400">
                <i class="fas fa-search-minus text-gray-300"></i>
                <span>"<strong>${query}</strong>" ile eşleşen kayıt bulunamadı.</span>
            </div>`;
        return;
    }

    resultEl.innerHTML = `
        <p class="text-xs font-semibold text-gray-500 mb-2">
            <i class="fas fa-map-marker-alt text-indigo-400 mr-1"></i>${bulunanlar.length} kıyafet bulundu
        </p>
        <div class="space-y-2">
            ${bulunanlar.map(item => {
                const tarih = item.zaman_damgasi
                    ? new Date(item.zaman_damgasi).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' })
                    : '-';
                const rackColor = item.rack === 'E' ? 'pink' : 'indigo';
                return `
                <div class="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3 border border-gray-100 cursor-pointer hover:border-indigo-300 hover:bg-indigo-50 transition-all"
                     onclick="rafSearchGoTo('${item.rack}', '${item.rafId}')">
                    <div>
                        <div class="font-bold text-gray-800 text-sm">${item.ad_soyad}</div>
                        <div class="flex items-center gap-3 text-xs text-gray-400 mt-0.5">
                            <span><i class="fas fa-id-badge mr-1 text-indigo-300"></i>${item.sicil_numarasi}</span>
                            <span><i class="fas fa-tag mr-1 text-indigo-300"></i>${item.rfid_tag}</span>
                            <span><i class="fas fa-clock mr-1"></i>${tarih}</span>
                        </div>
                    </div>
                    <div class="text-right ml-4 shrink-0">
                        <span class="inline-flex items-center gap-1.5 bg-${rackColor}-100 text-${rackColor}-700 font-black text-sm px-3 py-1.5 rounded-lg border border-${rackColor}-200">
                            <i class="fas fa-warehouse text-xs"></i>${item.rafId}
                        </span>
                        <div class="text-[10px] text-gray-400 mt-1">tıkla → rafa git</div>
                    </div>
                </div>`;
            }).join('')}
        </div>`;
}

async function rafSearchGoTo(rack, rafId) {
    // Rafa geç ve ilgili bölmeyi vurgula
    await selectRack(rack);

    // Highlight
    document.querySelectorAll('.rack-cell').forEach(el => el.classList.remove('search-highlight'));
    const target = document.querySelector(`[data-raf-id="${rafId}"]`);
    if (target) {
        target.classList.add('search-highlight');
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function rafSearchClear() {
    const input = document.getElementById('raf-search-input');
    if (input) { input.value = ''; rafSearch(''); }
}

// ---------------------------------------------------------------------------
// RFID Oku — Kirli Sepeti Simülasyonu
// ---------------------------------------------------------------------------

async function rfidOku() {
    const btn = document.querySelector('#rfid-oku-container button');
    const sonucEl = document.getElementById('rfid-oku-sonuc');
    const uyariEl = document.getElementById('rfid-oku-uyari');
    const listeEl = document.getElementById('rfid-oku-liste');
    const itemsEl = document.getElementById('rfid-oku-items');
    const sayiEl  = document.getElementById('rfid-oku-sayi');
    const kalanEl = document.getElementById('rfid-oku-kalan');

    // Buton loading
    btn.disabled = true;
    btn.textContent = ''; const i=createEl('i','fas fa-spinner fa-spin text-xl'); btn.appendChild(i); btn.appendChild(document.createTextNode(' Okunuyor...'));

    try {
        const res = await fetchWithAuth('/api/v1/islem/rfid-oku', { method: 'POST' });
        const data = await res.json();

        sonucEl.classList.remove('hidden');
        uyariEl.classList.add('hidden');
        listeEl.classList.add('hidden');

        if (data.durum === 'bos') {
            uyariEl.classList.remove('hidden');
        } else {
            listeEl.classList.remove('hidden');
            sayiEl.textContent = data.eklenenler.length;
            kalanEl.textContent = data.kalan_aday > 0
                ? `${data.kalan_aday} kişi daha eklenebilir`
                : 'Tüm kıyafetler tarandı';

            const cinsiyetBadge = c => c === 'K'
                ? '<span class="text-[10px] bg-pink-100 text-pink-600 px-1.5 py-0.5 rounded font-bold">K</span>'
                : '<span class="text-[10px] bg-blue-100 text-blue-600 px-1.5 py-0.5 rounded font-bold">E</span>';

            itemsEl.innerHTML = data.eklenenler.map(item => {
                const tarih = new Date(item.zaman_damgasi).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' });
                return `
                <div class="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2 border border-gray-100 text-xs">
                    <div class="flex items-center gap-2">
                        ${cinsiyetBadge(item.cinsiyet)}
                        <span class="font-semibold text-gray-800">${item.ad_soyad}</span>
                        <span class="text-gray-400 font-mono">${item.sicil_numarasi}</span>
                    </div>
                    <div class="flex items-center gap-2 text-gray-400">
                        <span class="font-mono">${item.rfid_tag}</span>
                        <span>${tarih}</span>
                    </div>
                </div>`;
            }).join('');
        }
    } catch (err) {
        showToast('RFID okuma hatası!', true);
    } finally {
        btn.disabled = false;
        btn.textContent = ''; const i=createEl('i','fas fa-wifi text-xl'); btn.appendChild(i); btn.appendChild(document.createTextNode(' RFID Oku'));
    }
}
