let currentUserRole = null;
let historyChartInstance = null;
let shelfChartInstance = null;
let currentChartPeriod = 'weekly';
let html5QrcodeScanner = null;

document.addEventListener('DOMContentLoaded', async () => {
    const token = localStorage.getItem('token');
    
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

    if (action === 'kirli-giris') {
        cfg = { title: 'Kirli Kıyafet Girişi', type: 'kirli', bg: 'bg-red-500' };
        sicilContainer.classList.add('hidden');
        if (kisiDetayContainer) kisiDetayContainer.classList.add('hidden');
        sicilInput.required = false;
    } else {
        cfg = { title: 'RFID Eşleştirme', type: 'eslestirme', bg: 'bg-indigo-500' };
        sicilContainer.classList.remove('hidden');
        if (kisiDetayContainer) kisiDetayContainer.classList.remove('hidden');
        sicilInput.required = true;
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
        let endpoint = '/api/islem';
        let payload = { islem_tipi, rfid_tag };

        if (islem_tipi === 'eslestirme') {
            endpoint = '/api/kiyafet';
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
                const res = await fetchWithAuth(`/api/calisan/${sicil}`);
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
        const res = await fetchWithAuth('/api/stats');
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
        const res = await fetchWithAuth(`/api/stats/history?period=${period}`);
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
        const res = await fetchWithAuth('/api/stats/raflar');
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
    const view = document.getElementById('tablo-view');
    view.classList.add('active');

    const titles = { 
        'kirli': 'Kirli Bekleyenler (Onay)', 
        'temiz': 'Teslim Edilecekler', 
        'teslim': 'Geçmiş Teslim Edilenler',
        'kiyafet': 'RFID Eşleştirme Tablosu'
    };
    document.getElementById('page-title').innerText = titles[type];

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
    tbody.innerHTML = '<tr><td colspan="5" class="text-center py-8"><i class="fas fa-spinner fa-spin text-2xl text-indigo-500"></i></td></tr>';

    try {
        const res = await fetchWithAuth(`/api/tablo/${type}`);
        const data = await res.json();

        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-8 text-gray-500">Kayıt bulunamadı.</td></tr>';
            return;
        }

        tbody.innerHTML = data.map(row => {
            if (type === 'kiyafet') {
                return `
                <tr class="hover:bg-gray-50 transition-colors">
                    <td class="py-4 px-6 border-b border-gray-100 font-medium whitespace-nowrap">${row.rfid_tag || '-'}</td>
                    <td class="py-4 px-6 border-b border-gray-100"><span class="bg-indigo-100 text-indigo-800 px-2 py-1 rounded text-xs font-bold border border-indigo-200">${row.sicil_numarasi || '-'}</span></td>
                    <td class="py-4 px-6 border-b border-gray-100 whitespace-nowrap">${row.ad_soyad || '-'}</td>
                    <td class="py-4 px-6 text-right border-b border-gray-100 whitespace-nowrap">
                        <button onclick="editKiyafet('${row.rfid_tag}', '${row.sicil_numarasi}')" class="text-blue-500 hover:text-blue-700 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-md text-sm font-medium mr-2 transition-colors">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button onclick="deleteKiyafet('${row.rfid_tag}')" class="text-red-500 hover:text-red-700 bg-red-50 hover:bg-red-100 px-3 py-1.5 rounded-md text-sm font-medium transition-colors">
                            <i class="fas fa-trash-alt"></i>
                        </button>
                    </td>
                </tr>
                `;
            }

            let actionBtn = '';
            let rafBadge = '';
            
            if (type === 'kirli') {
                actionBtn = `<td class="py-4 px-6 text-right border-b border-gray-100 whitespace-nowrap">
                    <button onclick="onaylaIslem(${row.islem_id})" class="bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors shadow-sm">
                        <i class="fas fa-check mr-1"></i> Temizlendi
                    </button>
                </td>`;
            } else if (type === 'temiz') {
                actionBtn = `<td class="py-4 px-6 text-right border-b border-gray-100 whitespace-nowrap">
                    <button onclick="teslimEt(${row.islem_id})" class="bg-indigo-500 hover:bg-indigo-600 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors shadow-sm mr-2">
                        <i class="fas fa-box-open mr-1"></i> Teslim Et
                    </button>
                    <button onclick="yazdirBarkod('${row.raf_id || '?'}', '${row.sicil_numarasi || ''}', '${(row.ad_soyad || '').replace(/'/g, "\\'")}', '${row.zaman_damgasi}', '${row.rfid_tag || ''}')" class="bg-gray-800 hover:bg-gray-900 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors shadow-sm">
                        <i class="fas fa-barcode mr-1"></i> Barkod
                    </button>
                </td>`;
                rafBadge = `<td class="py-4 px-6 border-b border-gray-100 text-center"><span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-bold border border-yellow-200">Raf ${row.raf_id || '?'}</span></td>`;
            } else {
                actionBtn = `<td style="display:none;" class="border-b border-gray-100"></td>`;
            }

            return `
            <tr class="hover:bg-gray-50 transition-colors">
                <td class="py-4 px-6 font-medium text-gray-900 border-b border-gray-100">#${row.islem_id}</td>
                <td class="py-4 px-6 border-b border-gray-100">${row.rfid_tag || '-'}</td>
                <td class="py-4 px-6 border-b border-gray-100"><span class="bg-indigo-100 text-indigo-800 px-2 py-1 rounded text-xs font-bold border border-indigo-200">${row.sicil_numarasi || '-'}</span></td>
                <td class="py-4 px-6 border-b border-gray-100 whitespace-nowrap">${row.ad_soyad || '-'}</td>
                ${type === 'temiz' ? rafBadge : ''}
                <td class="py-4 px-6 text-gray-500 text-xs border-b border-gray-100">${new Date(row.zaman_damgasi).toLocaleString('tr-TR')}</td>
                ${actionBtn}
            </tr>
            `;
        }).join('');

    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center py-8 text-red-500">Veriler yüklenirken hata oluştu!</td></tr>';
    }
}

async function onaylaIslem(islem_id) {
    if (!confirm("Kıyafet temizlendi olarak işaretlensin mi?")) return;

    try {
        const res = await fetchWithAuth('/api/islem/onayla', {
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
        const res = await fetchWithAuth('/api/islem/teslim', {
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

function yazdirBarkod(rafId, sicil, adSoyad, zamanDamgasi, rfidTag) {
    if (!window.jspdf || !window.QRious) {
        showToast("Gerekli kütüphaneler yüklenemedi!", true);
        return;
    }
    
    const { jsPDF } = window.jspdf;
    
    const doc = new jsPDF({
        orientation: 'landscape',
        unit: 'mm',
        format: [100, 50]
    });

    const formatZaman = new Date(zamanDamgasi).toLocaleString('tr-TR');
    const safeAdSoyad = removeTurkish(adSoyad || 'Bilinmiyor');

    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.text("LaundroStar - islem Barkodu", 50, 7, { align: "center" });

    doc.setLineWidth(0.5);
    doc.rect(4, 10, 92, 35);

    doc.setFontSize(14);
    doc.text("RAF: " + removeTurkish(rafId), 8, 18);

    doc.setFontSize(9);
    doc.setFont("helvetica", "normal");
    doc.text("Sicil: " + removeTurkish(sicil || 'Bilinmiyor'), 8, 25);
    doc.text("Kisi: " + safeAdSoyad, 8, 31);
    doc.text("Tarih: " + formatZaman, 8, 37);
    
    doc.setFontSize(7);
    doc.text("RFID: " + (rfidTag || 'Yok'), 8, 42);

    if (rfidTag) {
        try {
            const qr = new QRious({
                value: rfidTag,
                size: 250,
                level: 'M'
            });
            const qrDataUrl = qr.toDataURL();
            
            doc.addImage(qrDataUrl, 'PNG', 70, 15, 24, 24);
        } catch (e) {
            console.error("QR kod olusturulurken hata:", e);
        }
    }

    const safeName = removeTurkish(adSoyad || 'bilinmiyor').replace(/\s+/g, '_').toLowerCase();
    doc.save(`barkod_raf_${rafId}_${safeName}.pdf`);
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
        const res = await fetchWithAuth(`/api/kiyafet/${old_rfid}`, {
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
        const res = await fetchWithAuth(`/api/kiyafet/${rfid}`, {
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
    const token = localStorage.getItem('token');
    options.headers = options.headers || {};
    
    if (token) {
        options.headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, options);
    if (response.status === 401 && !url.includes('/api/token')) {
        logout();
        throw new Error('Unauthorized');
    }
    return response;
}

async function fetchUserInfo() {
    try {
        const res = await fetchWithAuth('/api/users/me');
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
            } else {
                document.getElementById('header-role').innerText = "PERSONEL";
                document.getElementById('admin-menu-header').classList.add('hidden');
                document.getElementById('admin-menu-teslim').classList.add('hidden');
                document.getElementById('admin-audit-header').classList.add('hidden');
                document.getElementById('admin-menu-audit').classList.add('hidden');
                document.getElementById('menu-rfid-eslestirme')?.classList.add('hidden');
                document.getElementById('admin-menu-kiyafet')?.classList.add('hidden');
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
    
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Bekleyin...';
    btn.disabled = true;
    errObj.classList.add('hidden');
    
    try {
        const params = new URLSearchParams();
        params.append('username', username);
        params.append('password', password);

        const res = await fetch('/api/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: params
        });
        
        if (res.ok) {
            const data = await res.json();
            localStorage.setItem('token', data.access_token);
            document.getElementById('login-password').value = '';
            await fetchUserInfo();
        } else {
            errObj.innerText = "Kullanıcı adı veya şifre hatalı!";
            errObj.classList.remove('hidden');
        }
    } catch (err) {
        errObj.innerText = "Sunucuya bağlanılamadı!";
        errObj.classList.remove('hidden');
    } finally {
        btn.innerHTML = '<i class="fas fa-lock mr-2"></i> Giriş Yap';
        btn.disabled = false;
    }
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
    localStorage.removeItem('token');
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
        const res = await fetchWithAuth('/api/users/me');
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
        const token = localStorage.getItem('token');
        const res = await fetch('/api/users/me/photo', {
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
        const res = await fetchWithAuth('/api/users/me', {
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
        const res = await fetchWithAuth('/api/users');
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
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Oluşturuluyor...';
    btn.disabled = true;
    
    const payload = {
        username: document.getElementById('new-user-username').value,
        password: document.getElementById('new-user-password').value,
        role: document.getElementById('new-user-role').value,
        title: document.getElementById('new-user-title').value || null,
        company: document.getElementById('new-user-company').value || null
    };
    
    try {
        const res = await fetchWithAuth('/api/users', {
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
        const res = await fetchWithAuth(`/api/users/${userId}`, {
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
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-6"><i class="fas fa-spinner fa-spin text-2xl text-indigo-400"></i></td></tr>';
    
    const userFilter   = document.getElementById('audit-filter-user')?.value.trim() || '';
    const actionFilter = document.getElementById('audit-filter-action')?.value || '';
    
    let url = '/api/audit-logs?limit=200';
    if (userFilter)   url += `&username=${encodeURIComponent(userFilter)}`;
    if (actionFilter) url += `&action=${encodeURIComponent(actionFilter)}`;
    
    try {
        const res = await fetchWithAuth(url);
        if (!res.ok) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-6 text-red-500">Loglar yüklenemedi.</td></tr>';
            return;
        }
        const logs = await res.json();
        
        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center py-6 text-gray-400">Kayıt bulunamadı.</td></tr>';
            return;
        }
        
        tbody.innerHTML = logs.map(log => {
            const actionInfo = ACTION_LABELS[log.action] || { label: log.action, badge: 'bg-gray-100 text-gray-700' };
            const statusBadge = log.status === 'success'
                ? '<span class="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-bold">Başarılı</span>'
                : '<span class="px-2 py-1 bg-red-100 text-red-800 rounded-full text-xs font-bold">Başarısız</span>';
            const ts = new Date(log.timestamp).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'medium' });
            
            return `
            <tr class="hover:bg-gray-50 transition-colors">
                <td class="py-3 px-4 text-xs text-gray-500 whitespace-nowrap">${ts}</td>
                <td class="py-3 px-4 font-semibold text-gray-800">${log.username || '-'}</td>
                <td class="py-3 px-4">
                    <span class="px-2 py-1 rounded-full text-xs font-bold ${actionInfo.badge}">${actionInfo.label}</span>
                </td>
                <td class="py-3 px-4 text-xs text-gray-600 max-w-xs truncate" title="${log.detail || ''}">${log.detail || '-'}</td>
                <td class="py-3 px-4 text-xs font-mono text-gray-500">${log.ip_address || '-'}</td>
                <td class="py-3 px-4">${statusBadge}</td>
            </tr>`;
        }).join('');
    } catch (err) {
        console.error('Audit log yükleme hatası:', err);
        tbody.innerHTML = '<tr><td colspan="6" class="text-center py-6 text-red-500">Sunucu bağlantı hatası.</td></tr>';
    }
}

function clearAuditFilters() {
    document.getElementById('audit-filter-user').value = '';
    document.getElementById('audit-filter-action').value = '';
    loadAuditLogs();
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
            fetchWithAuth('/api/stats/raflar'),
            fetchWithAuth(`/api/stats/raf-detay/${letter}`)
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
        <div class="px-4 py-3 bg-gray-50 border-b border-gray-200 rounded-t-xl">
            <div class="flex items-center justify-between">
                <span class="font-bold text-gray-800 text-sm">${rafId}</span>
                <span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-${statusColor}-100 text-${statusColor}-700">${statusText}</span>
            </div>
            <div class="text-[11px] text-gray-500 mt-0.5">${count} / ${capacity} kapasite</div>
        </div>
    `;

    if (items.length > 0) {
        html += '<div class="p-3 space-y-2 max-h-60 overflow-y-auto">';
        items.forEach((item, idx) => {
            const tarih = item.zaman_damgasi
                ? new Date(item.zaman_damgasi).toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' })
                : '-';
            html += `
                <div class="bg-gray-50 rounded-lg p-2.5 border border-gray-100 text-xs">
                    <div class="flex justify-between items-center mb-1">
                        <span class="font-bold text-gray-800">${item.ad_soyad}</span>
                        <span class="text-[10px] text-gray-400">#${idx + 1}</span>
                    </div>
                    <div class="grid grid-cols-2 gap-1 text-gray-500">
                        <span><i class="fas fa-id-badge mr-1 text-indigo-400"></i>${item.sicil_numarasi}</span>
                        <span><i class="fas fa-tag mr-1 text-indigo-400"></i>${item.rfid_tag}</span>
                    </div>
                    <div class="text-gray-400 mt-1"><i class="fas fa-clock mr-1"></i>${tarih}</div>
                </div>
            `;
        });
        html += '</div>';
    } else {
        html += '<div class="p-4 text-center text-xs text-gray-400"><i class="fas fa-inbox text-2xl mb-2 block text-gray-300"></i>Bu bölmede kıyafet yok</div>';
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
