let currentUserRole = null;
let historyChartInstance = null;
let currentChartPeriod = 'weekly';

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
    } else if (target === 'kirli-giris') {
        setupActionView('kirli-giris');
    } else if (target.startsWith('tablo-')) {
        setupTableView(target.replace('tablo-', ''));
    }
}

function setupActionView(action) {
    const view = document.getElementById('action-view');
    view.classList.add('active');

    // Yalnızca Kirli Girişi kaldı
    const cfg = { title: 'Kirli Kıyafet Girişi', type: 'kirli', bg: 'bg-red-500' };

    document.getElementById('page-title').innerText = cfg.title;
    document.getElementById('action-title').innerText = cfg.title;
    document.getElementById('islem_tipi').value = cfg.type;
    document.getElementById('rfid_tag').value = '';
    document.getElementById('sicil_numarasi').value = '';

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
        const res = await fetchWithAuth('/api/islem', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ islem_tipi, rfid_tag, sicil_numarasi })
        });

        if (res.ok) {
            showToast('İşlem başarıyla kaydedildi!');
            document.getElementById('rfid_tag').value = '';
            document.getElementById('sicil_numarasi').value = '';
            document.getElementById('rfid_tag').focus();
        } else {
            showToast('Bir hata oluştu!', true);
        }
    } catch (err) {
        showToast('Sunucuya bağlanılamadı!', true);
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

async function setupTableView(type) {
    const view = document.getElementById('tablo-view');
    view.classList.add('active');

    const titles = { 'kirli': 'Kirli Bekleyenler (Onay)', 'teslim': 'Geçmiş Teslim Edilenler' };
    document.getElementById('page-title').innerText = titles[type];

    const islemTh = document.getElementById('islem-th');
    if (type === 'kirli') {
        islemTh.style.display = 'table-cell';
    } else {
        islemTh.style.display = 'none';
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
            let actionBtn = '';
            if (type === 'kirli') {
                actionBtn = `<td class="py-4 px-6 text-right border-b border-gray-100 whitespace-nowrap">
                    <button onclick="onaylaIslem(${row.islem_id})" class="bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg text-xs font-bold transition-colors shadow-sm">
                        <i class="fas fa-check mr-1"></i> Temizlendi
                    </button>
                </td>`;
            } else {
                actionBtn = `<td style="display:none;" class="border-b border-gray-100"></td>`;
            }

            return `
            <tr class="hover:bg-gray-50 transition-colors">
                <td class="py-4 px-6 font-medium text-gray-900 border-b border-gray-100">#${row.islem_id}</td>
                <td class="py-4 px-6 border-b border-gray-100">${row.rfid_tag || '-'}</td>
                <td class="py-4 px-6 border-b border-gray-100"><span class="bg-indigo-100 text-indigo-800 px-2 py-1 rounded text-xs font-bold border border-indigo-200">${row.sicil_numarasi || '-'}</span></td>
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
    if (!confirm("Kıyafet temizlendi ve kullanıcıya teslime hazır olarak işaretlensin mi?")) return;

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
                document.getElementById('admin-menu-header').classList.remove('hidden');
                document.getElementById('admin-menu-teslim').classList.remove('hidden');
            } else {
                document.getElementById('admin-menu-header').classList.add('hidden');
                document.getElementById('admin-menu-teslim').classList.add('hidden');
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

function toggleUserMenu() {
    const dropdown = document.getElementById('user-dropdown');
    dropdown.classList.toggle('hidden');
}

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
