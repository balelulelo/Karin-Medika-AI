document.addEventListener('DOMContentLoaded', () => {
    // --- REFERENSI ELEMEN ---
    const viewStart = document.getElementById('view-start');
    const viewMedication = document.getElementById('view-medication');
    const appContainer = document.getElementById('app-container');
    const loadingScreen = document.getElementById('loading-screen');
    
    // Elemen Kartu untuk Animasi
    const loginCard = document.querySelector('.login-card');
    const medsCard = document.querySelector('.meds-card');

    // Input & Tombol
    const nameInput = document.getElementById('name-input');
    const btnToMeds = document.getElementById('btn-to-meds');
    
    const drugContainer = document.getElementById('drug-input-container');
    const addDrugBtn = document.getElementById('add-drug-btn');
    const btnStartAnalysis = document.getElementById('btn-start-analysis');
    const greetingText = document.getElementById('greeting-text');

    // Chat Elements
    const chatLog = document.getElementById('chat-log');
    const userInput = document.getElementById('user-input');
    const sendBtn = document.getElementById('send-btn');
    const karinImage = document.getElementById('karin-image');
    const langEnBtn = document.getElementById('lang-en');
    const langIdBtn = document.getElementById('lang-id');

    // --- STATE VARIABLES ---
    let userName = '';
    let currentLanguage = 'en';
    let drugList = [];
    let chatHistory = [];
    const backendUrl = 'http://127.0.0.1:8000/chat';

    // --- INISIALISASI AWAL ---
    // Beri animasi pop-out pada kartu login saat pertama buka
    if(loginCard) loginCard.classList.add('pop-out-enter');

    // --- 1. NAVIGASI: START -> MEDICATION LIST ---
    btnToMeds.addEventListener('click', () => {
        const name = nameInput.value.trim();
        if (!name) {
            alert("Please enter your name first!");
            return;
        }

        userName = name;
        
        // Update teks sapaan
        const text = currentLanguage === 'id' 
            ? `Halo ${userName}, Sebutkan obat apa saja yang akan kamu minum`
            : `Hello ${userName}, Please tell us the medications you're about to take`;
        if(greetingText) greetingText.textContent = text;

        // Transisi Halaman
        viewStart.classList.add('hidden');
        viewMedication.classList.remove('hidden');

        // Tambahkan animasi pop-out ke kartu obat
        if(medsCard) {
            medsCard.classList.remove('pop-out-enter'); // Reset dulu biar bisa trigger ulang
            void medsCard.offsetWidth; // Trigger reflow (trik CSS)
            medsCard.classList.add('pop-out-enter');
        }

        // Generate input obat default jika kosong
        if (drugContainer.children.length === 0) {
            addDrugInput();
            addDrugInput();
        }
    });

    // --- 2. LOGIKA TAMBAH OBAT (FIXED) ---
    function addDrugInput() {
        const currentCount = document.querySelectorAll('.drug-input').length;
        if (currentCount >= 6) {
            alert("You can add up to 6 medications only.");
            return;
        }

        // Buat Wrapper
        const wrapper = document.createElement('div');
        wrapper.classList.add('drug-input-wrapper');

        // Buat Input Field
        const input = document.createElement('input');
        input.type = 'text';
        input.classList.add('drug-input'); // Class penting untuk selector nanti
        input.placeholder = `Medication ${currentCount + 1}...`;
        input.style.flex = "1"; // Agar input memenuhi ruang
        input.style.marginBottom = "0"; // Reset margin bawaan styles.css jika ada

        // Tombol Hapus (X)
        const removeBtn = document.createElement('button');
        removeBtn.classList.add('remove-drug-btn');
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.onclick = () => wrapper.remove();

        // Gabungkan
        wrapper.appendChild(input);
        // Hanya tampilkan tombol hapus jika bukan input pertama/kedua (opsional)
        // Atau tampilkan selalu agar user bebas menghapus
        wrapper.appendChild(removeBtn);

        drugContainer.appendChild(wrapper);
        
        // Fokus ke input baru
        input.focus();
    }

    // Pasang Event Listener ke Tombol Add More
    if(addDrugBtn) {
        addDrugBtn.addEventListener('click', (e) => {
            e.preventDefault(); // Mencegah form submit jika ada tag <form>
            addDrugInput();
        });
    }

    // --- 3. NAVIGASI: MEDICATION -> CHAT (ANALYSIS) ---
    if(btnStartAnalysis) {
        btnStartAnalysis.addEventListener('click', async () => {
            // Ambil semua value dari input yang punya class .drug-input
            const inputs = document.querySelectorAll('.drug-input');
            drugList = [];
            
            inputs.forEach(input => {
                const val = input.value.trim();
                if (val) drugList.push(val);
            });

            if (drugList.length === 0) {
                alert("Please enter at least one medication.");
                return;
            }

            // Transisi ke Loading
            viewMedication.classList.add('hidden');
            loadingScreen.classList.remove('hidden');

            // Mulai sesi chat di background
            await startChatSession();
        });
    }

    // --- 4. LOGIKA CHAT & BACKEND ---
    async function startChatSession() {
        // Siapkan pesan intro tersembunyi
        const introMsg = currentLanguage === 'id' 
            ? `Halo Karin. Nama saya ${userName}. Saya mengonsumsi obat-obatan ini: ${drugList.join(', ')}. Tolong analisis interaksi dan efek sampingnya.`
            : `Hi Karin. My name is ${userName}. I am taking these medications: ${drugList.join(', ')}. Please analyze the interactions and side effects.`;

        // Masukkan ke history backend (tapi tidak ditampilkan di UI user)
        chatHistory.push({ "role": "user", "parts": [introMsg] });

        try {
            const response = await fetch(backendUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: introMsg, 
                    history: [],
                    language: currentLanguage,
                    userName: userName
                }),
            });

            if (!response.ok) throw new Error("Network Error");
            const data = await response.json();

            // Selesai Loading -> Tampilkan Chat
            loadingScreen.classList.add('hidden');
            appContainer.classList.remove('hidden');
            
            // Tambahkan animasi pop-out ke panel chat
            const profileCard = document.querySelector('.profile-card');
            const chatInterface = document.querySelector('.chat-interface');
            if(profileCard) profileCard.classList.add('pop-out-enter');
            if(chatInterface) chatInterface.classList.add('pop-out-enter');

            // Tampilkan Balasan Karin
            for (const msg of data.messages) {
                appendMessage('karin', msg);
                chatHistory.push({ "role": "model", "parts": [msg] });
            }
            updateKarinImage(data.emotion);

        } catch (error) {
            console.error(error);
            loadingScreen.classList.add('hidden');
            appContainer.classList.remove('hidden');
            appendMessage('karin', "Maaf, koneksi ke server gagal. Pastikan backend Python berjalan.");
        }
    }

    async function sendMessage() {
        const messageText = userInput.value.trim();
        if (!messageText) return;

        appendMessage('user', messageText);
        userInput.value = '';
        userInput.disabled = true;
        sendBtn.disabled = true;

        chatHistory.push({ "role": "user", "parts": [messageText] });

        try {
            const response = await fetch(backendUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: messageText,
                    history: chatHistory.slice(0, -1),
                    language: currentLanguage,
                    userName: userName
                }),
            });

            const data = await response.json();
            for (const msg of data.messages) {
                appendMessage('karin', msg);
                chatHistory.push({ "role": "model", "parts": [msg] });
            }
            updateKarinImage(data.emotion);

        } catch (error) {
            appendMessage('karin', "Error connecting to server.");
        } finally {
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
        }
    }

    // --- 5. BAHASA & UI UPDATE ---
    function updateUIForLanguage() {
        // Update tampilan tombol aktif
        if(langEnBtn && langIdBtn) {
            if (currentLanguage === 'en') {
                langEnBtn.style.fontWeight = 'bold';
                langEnBtn.style.textDecoration = 'underline';
                langIdBtn.style.fontWeight = 'normal';
                langIdBtn.style.textDecoration = 'none';
                if(userInput) userInput.placeholder = "Type a message to Karin...";
            } else {
                langIdBtn.style.fontWeight = 'bold';
                langIdBtn.style.textDecoration = 'underline';
                langEnBtn.style.fontWeight = 'normal';
                langEnBtn.style.textDecoration = 'none';
                if(userInput) userInput.placeholder = "Ketik pesan untuk Karin...";
            }
        }
    }

    // Event Listener untuk Tombol Bahasa
    if(langEnBtn) {
        langEnBtn.addEventListener('click', () => { 
            currentLanguage = 'en'; 
            updateUIForLanguage();
        });
    }

    if(langIdBtn) {
        langIdBtn.addEventListener('click', () => { 
            currentLanguage = 'id'; 
            updateUIForLanguage();
        });
    }

    // Panggil sekali saat start untuk set default
    updateUIForLanguage();

    // --- HELPER FUNCTIONS ---
    function appendMessage(sender, text) {
        const div = document.createElement('div');
        div.classList.add('message', sender === 'user' ? 'user-message' : 'karin-message');
        div.innerHTML = text;
        chatLog.appendChild(div);
        chatLog.scrollTop = chatLog.scrollHeight;
    }

    function updateKarinImage(emotion) {
        const valid = ['neutral', 'happy', 'blushing', 'concerned', 'curious'];
        const imgName = valid.includes(emotion) ? emotion : 'neutral';
        if(karinImage) karinImage.src = `images/${imgName}.png`;
    }

    // --- EVENT LISTENERS TAMBAHAN ---
    if(sendBtn) sendBtn.addEventListener('click', sendMessage);
    if(userInput) userInput.addEventListener('keypress', (e) => { if(e.key === 'Enter') sendMessage(); });
    
    // Switcher Bahasa
    if(langEnBtn) langEnBtn.addEventListener('click', () => { 
        currentLanguage = 'en'; 
        langEnBtn.style.fontWeight = 'bold'; langIdBtn.style.fontWeight = 'normal';
    });
    if(langIdBtn) langIdBtn.addEventListener('click', () => { 
        currentLanguage = 'id'; 
        langIdBtn.style.fontWeight = 'bold'; langEnBtn.style.fontWeight = 'normal';
    });
});